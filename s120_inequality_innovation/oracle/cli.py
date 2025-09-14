from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List, Tuple

from .jpype_harness import run_java_oracle
from ..core.registry import ParameterRegistry
from ..io.golden_compare import canonicalize_java_headers

import pandas as pd
import xml.etree.ElementTree as ET


@dataclass
class OracleRunSpec:
    name: str
    overrides: Dict


def _resolve_classpath() -> Optional[str]:
    # Prefer explicit env, else guess common paths under $HOME/work
    cp = os.environ.get("S120_ORACLE_CLASSPATH")
    if cp:
        return cp
    candidates = []
    home = Path.home()
    classes = home / "work" / "build" / "java_classes"
    if classes.exists():
        candidates.append(str(classes))
    for d in [home / "work" / "InequalityInnovation" / "lib", home / "work" / "jmab" / "lib"]:
        if d.exists():
            candidates.append(str(d) + "/*")
    if candidates:
        return ":".join(candidates)
    return None


def _resolve_xml(scenario: str) -> Optional[Path]:
    # Expect env var or default under model repo
    xml = os.environ.get("S120_ORACLE_XML")
    if xml:
        return Path(xml)
    # Fallback guess (adjust as needed)
    home = Path.home()
    candidate = home / "work" / "InequalityInnovation" / "resources" / "InequalityInnovation.xml"
    return candidate if candidate.exists() else None


def run_oracle_scenario(spec: OracleRunSpec, outdir: Path, classpath: Optional[str] = None, xml: Optional[Path] = None,
                        jvm: Optional[str] = None, seed: Optional[int] = None) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    params = ParameterRegistry.from_files(overrides=spec.overrides)
    meta = {
        "scenario": spec.name,
        "overrides": spec.overrides,
        "config_hash": params.config_hash(),
    }
    meta_path = outdir / "meta.json"
    (outdir / "series.csv").write_text("", encoding="utf-8")  # will be overwritten by Java side
    if classpath is None:
        classpath = _resolve_classpath()
    if xml is None:
        xml = _resolve_xml(spec.name)
    # create scenario-specific XML with patched fileNamePrefix pointing under outdir/data
    scenario_xml = _ensure_scenario_xml(xml, spec.name, outdir) if xml else None
    meta.update({"classpath": classpath, "xml": str(scenario_xml) if scenario_xml else None})
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    if classpath and scenario_xml:
        try:
            run_java_oracle(scenario_xml, classpath, jvm_path=jvm, seed=seed)
        except Exception as e:  # pragma: no cover
            # Do not hard-fail here; allow collection to proceed so callers can inspect meta/logs
            print(f"Warning: Java oracle run failed: {e}")
    else:
        print("Warning: Missing classpath or xml; wrote meta.json only.")
    # Attempt to collect canonical series and finalize meta
    _collect_and_write_canonical(spec, outdir, params, scenario_xml)
    return outdir / "series.csv"


def _ensure_scenario_xml(xml_path: Path, scenario: str, outdir: Path) -> Path:
    """Copy the provided XML and patch fileNamePrefix -> <outdir>/data for the scenario."""
    headless_dir = Path("artifacts/golden_java/headless")
    headless_dir.mkdir(parents=True, exist_ok=True)
    scenario_xml = headless_dir / f"main_headless_{scenario}.xml"
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        def local(tag: str) -> str:
            return tag.split('}', 1)[-1]
        for bean in root.iter():
            if local(bean.tag) == 'bean' and bean.attrib.get('id') == 'fileNamePrefix':
                for child in list(bean):
                    if local(child.tag) == 'constructor-arg':
                        child.attrib['value'] = str(outdir / 'data')
        scenario_xml.write_text(ET.tostring(root, encoding='unicode'), encoding='utf-8')
    except Exception as e:  # pragma: no cover
        print(f"Warning: could not patch scenario XML: {e}; using original.")
        scenario_xml = xml_path
    return scenario_xml


def _parse_file_name_prefix(xml_path: Optional[Path]) -> Optional[str]:
    if not xml_path or not xml_path.exists():
        return None
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        def local(tag: str) -> str:
            return tag.split('}', 1)[-1]
        for bean in root.iter():
            if local(bean.tag) == 'bean' and bean.attrib.get('id') == 'fileNamePrefix':
                for child in list(bean):
                    if local(child.tag) == 'constructor-arg':
                        val = child.attrib.get('value')
                        if val:
                            return val
        return None
    except Exception as e:  # pragma: no cover
        print(f"Warning: failed to parse fileNamePrefix from XML {xml_path}: {e}")
        return None


def _find_raw_data_dir(outdir: Path, xml: Optional[Path]) -> Path:
    d = outdir / "data"
    if d.exists():
        return d
    prefix = _parse_file_name_prefix(xml)
    if prefix:
        return Path(prefix)
    return d


CANONICAL_HEADERS = [
    "t",
    "GDP",
    "CONS",
    "INV",
    "INFL",
    "UNEMP",
    "PROD_C",
    "Gini_income",
    "Gini_wealth",
    "Debt_GDP",
]


def _read_first_series(csv_path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(csv_path)
        tcol = None
        for c in df.columns:
            lc = c.lower()
            if lc in {"t", "time", "period"}:
                tcol = c
                break
        if tcol is None:
            # Try no-header, two-column format: t,val
            try:
                df = pd.read_csv(csv_path, header=None, names=["t", "val"])
                tcol = "t"
            except Exception:
                return None
        vals = [c for c in df.columns if c != tcol]
        if not vals:
            return None
        return pd.DataFrame({"t": df[tcol].astype(int), "val": df[vals[0]]})
    except Exception:
        return None


def _collect_from_raw_dir(raw_dir: Path) -> Tuple[pd.DataFrame, List[str]]:
    used: List[str] = []
    series: Dict[str, pd.Series] = {}
    # GDP
    for name in ["nominalGDP", "gdp", "GDP"]:
        for p in raw_dir.glob(f"*{name}*.csv"):
            df = _read_first_series(p)
            if df is not None:
                series["GDP"] = df.set_index("t")["val"]
                used.append(p.name)
                break
        if "GDP" in series:
            break
    # Investment
    for name in ["nominalInvestment", "investment", "INV", "NominalInvestment"]:
        for p in raw_dir.glob(f"*{name}*.csv"):
            df = _read_first_series(p)
            if df is not None:
                series["INV"] = df.set_index("t")["val"]
                used.append(p.name)
                break
        if "INV" in series:
            break
    # Unemployment
    for name in ["unemployment", "Unemployment", "u"]:
        for p in raw_dir.glob(f"*{name}*.csv"):
            df = _read_first_series(p)
            if df is not None:
                series["UNEMP"] = df.set_index("t")["val"]
                used.append(p.name)
                break
        if "UNEMP" in series:
            break
    # Consumption: sum households nominal consumption
    cons_parts: List[pd.Series] = []
    for who in ["workers", "managers", "topManagers", "researchers"]:
        for p in raw_dir.glob(f"*{who}*NominalConsumption*.csv"):
            df = _read_first_series(p)
            if df is not None:
                cons_parts.append(df.set_index("t")["val"])  # type: ignore
                used.append(p.name)
    if cons_parts:
        s = cons_parts[0].copy()
        for part in cons_parts[1:]:
            s = s.add(part, fill_value=0.0)
        series["CONS"] = s
    # Inflation: from cAvPrice
    for p in raw_dir.glob("*cAvPrice*.csv"):
        df = _read_first_series(p)
        if df is not None:
            s = df.set_index("t")["val"].astype(float)
            infl = (s - s.shift(1)) / s.shift(1)
            series["INFL"] = infl
            used.append(p.name)
            break
    # Productivity C
    for p in raw_dir.glob("*cProductivity*.csv"):
        try:
            df = pd.read_csv(p)
            tcol = next(c for c in df.columns if c.lower() in {"t", "time", "period"})
            val_cols = [c for c in df.columns if c != tcol]
            if val_cols:
                avg = df[val_cols].mean(axis=1)
                series["PROD_C"] = pd.Series(avg.values, index=df[tcol].astype(int).values)
                used.append(p.name)
                break
        except Exception:
            continue
    # Debt/GDP
    debt_s: Optional[pd.Series] = None
    for suffix in ["cFirmsAggregateDebt", "kFirmsAggregateDebt"]:
        for p in raw_dir.glob(f"*{suffix}*.csv"):
            df = _read_first_series(p)
            if df is not None:
                if debt_s is None:
                    debt_s = df.set_index("t")["val"].astype(float)
                else:
                    debt_s = debt_s.add(df.set_index("t")["val"].astype(float), fill_value=0.0)  # type: ignore
                used.append(p.name)
    # Build DataFrame
    if series:
        all_idx = None
        for s in series.values():
            all_idx = s.index if all_idx is None else all_idx.union(s.index)
        df = pd.DataFrame(index=sorted(all_idx))
        for k, s in series.items():
            df[k] = s
        if debt_s is not None and "GDP" in df.columns:
            dd = debt_s.reindex(df.index)
            g = df["GDP"].astype(float)
            with pd.option_context('mode.use_inf_as_na', True):
                df["Debt_GDP"] = (dd / g)
        df.insert(0, "t", df.index.astype(int))
        return canonicalize_java_headers(df), used
    else:
        return pd.DataFrame(columns=CANONICAL_HEADERS), used


def _collect_and_write_canonical(spec: OracleRunSpec, outdir: Path, params: ParameterRegistry, xml: Optional[Path]):
    raw_dir = _find_raw_data_dir(outdir, xml)
    horizon = int(params.get("meta.horizon", 1000))
    seed = os.environ.get("S120_ORACLE_SEED") or os.environ.get("JABM_SEED")
    used_files: List[str] = []
    # try primary raw_dir; if empty, try outdir itself (prefix often used in filenames)
    if raw_dir.exists() and any(raw_dir.glob("*.csv")):
        df, used_files = _collect_from_raw_dir(raw_dir)
    elif outdir.exists() and any(outdir.glob("data*.csv")):
        df, used_files = _collect_from_raw_dir(outdir)
    else:
        # Fallback is disabled by default; enable only if S120_ALLOW_FALLBACK is truthy
        allow_fb = os.environ.get("S120_ALLOW_FALLBACK", "0").lower() not in ("0", "false", "")
        if allow_fb:
            py_baseline = Path("artifacts/baseline/run_001/series.csv")
            if py_baseline.exists():
                try:
                    df = pd.read_csv(py_baseline)
                    df = canonicalize_java_headers(df)
                    used_files = [f"FALLBACK:{py_baseline}"]
                except Exception:
                    df = pd.DataFrame(columns=CANONICAL_HEADERS)
            else:
                df = pd.DataFrame(columns=CANONICAL_HEADERS)
        else:
            df = pd.DataFrame(columns=CANONICAL_HEADERS)
    if "t" not in df.columns:
        df["t"] = []
    try:
        if len(df.index) == 0:
            full = pd.DataFrame({"t": list(range(1, horizon + 1))})
        else:
            tmin = int(df["t"].min()) if not df["t"].isna().all() else 1
            tmax = int(df["t"].max()) if not df["t"].isna().all() else horizon
            full = pd.DataFrame({"t": list(range(tmin, max(tmax, horizon) + 1))})
        out = full.merge(df, on="t", how="left")
    except Exception:
        out = df
    for col in CANONICAL_HEADERS:
        if col not in out.columns:
            out[col] = pd.NA
    out = out[CANONICAL_HEADERS]
    outdir.mkdir(parents=True, exist_ok=True)
    out.to_csv(outdir / "series.csv", index=False)
    meta_path = outdir / "meta.json"
    meta = {}
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            try:
                meta = json.load(f)
            except Exception:
                meta = {}
    meta.update({
        "seed": int(seed) if seed is not None and str(seed).isdigit() else seed,
        "horizon": horizon,
        "fileNamePrefix": _parse_file_name_prefix(xml),
        "theta": params.get("taxes.theta_progressive"),
        "tu": params.get("wage_rigidity.tu"),
        "raw_sources": used_files,
    })
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, sort_keys=True)


def _build_cli():
    import argparse
    p = argparse.ArgumentParser(description="S120 Java oracle runner")
    sub = p.add_subparsers(dest="cmd", required=True)
    # common opts
    p.add_argument("--classpath", help="Classpath to JMAB+model", required=False)
    p.add_argument("--xml", help="Spring XML config", required=False)
    p.add_argument("--jvm", help="Path to libjvm.so", required=False)
    p.add_argument("--outroot", help="Artifacts root", default="artifacts/golden_java")
    p.add_argument("--seed", type=int, required=False, help="Deterministic seed for JABM")

    sb = sub.add_parser("baseline", help="Run baseline")
    st = sub.add_parser("tax", help="Run tax theta scenario")
    st.add_argument("--theta", type=float, required=True)
    sw = sub.add_parser("wage", help="Run wage tu scenario")
    sw.add_argument("--tu", type=int, required=True)
    sc = sub.add_parser("collect", help="Collect canonical series from an existing run dir")
    sc.add_argument("--scenario", required=True, help="Scenario folder under outroot (e.g., baseline)")
    sr = sub.add_parser("repro", help="Run two short baselines with same seed and compare first 10 GDPs")
    sr.add_argument("--seed", type=int, required=True)
    return p


def main():
    p = _build_cli()
    a = p.parse_args()
    outroot = Path(a.outroot)
    if a.cmd == "baseline":
        spec = OracleRunSpec("baseline", overrides={})
        outdir = outroot / "baseline"
    elif a.cmd == "tax":
        spec = OracleRunSpec(f"tax_theta{a.theta}", overrides={"taxes": {"theta_progressive": float(a.theta)}})
        outdir = outroot / f"tax_theta{a.theta}"
    elif a.cmd == "wage":
        spec = OracleRunSpec(f"wage_tu{a.tu}", overrides={"wage_rigidity": {"tu": int(a.tu)}})
        outdir = outroot / f"wage_tu{a.tu}"
    elif a.cmd == "repro":
        # run two baseline runs with same seed and compare
        out_a = outroot / "repro_a"
        out_b = outroot / "repro_b"
        spec = OracleRunSpec("baseline", overrides={})
        run_oracle_scenario(spec, out_a, classpath=a.classpath, xml=Path(a.xml) if a.xml else None, jvm=a.jvm, seed=a.seed)
        run_oracle_scenario(spec, out_b, classpath=a.classpath, xml=Path(a.xml) if a.xml else None, jvm=a.jvm, seed=a.seed)
        # compare first 10 GDPs
        import pandas as pd  # local import to keep module scope clean
        ok = False
        try:
            sa = pd.read_csv(out_a / "series.csv")
            sb = pd.read_csv(out_b / "series.csv")
            ma = sa.set_index("t")["GDP"].iloc[:10].tolist()
            mb = sb.set_index("t")["GDP"].iloc[:10].tolist()
            ok = ma == mb and len(ma) == 10
        except Exception:
            ok = False
        logp = outroot / "repro_check.txt"
        logp.parent.mkdir(parents=True, exist_ok=True)
        logp.write_text(f"Reproducibility check with seed={a.seed}: {'PASSED' if ok else 'FAILED'}\n", encoding='utf-8')
        return 0
    else:
        outdir = outroot / a.scenario
        params = ParameterRegistry.from_files(overrides=None)
        _collect_and_write_canonical(OracleRunSpec(a.scenario, overrides={}), outdir, params, Path(a.xml) if a.xml else None)
        return 0
    run_oracle_scenario(spec, outdir, classpath=a.classpath, xml=Path(a.xml) if a.xml else None, jvm=a.jvm, seed=a.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
