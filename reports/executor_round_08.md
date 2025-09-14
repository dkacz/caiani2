1. WHAT I CHANGED
- Oracle tools: extended `oracle/extract_params.py` to support `--map` and `--report`, generating a Markdown mapping diff (`reports/params_mapping.md`) against `config/param_map.yaml` while still writing `params_extracted.json`.
- Accounting + finance: kept Slice‑3 finance core in `core/slice3_engine.py` and extended liquidity handling (CB advances backstop), simple bank capital tracking, dividend suppression when under‑capitalized, and government funding identity logging (`notes_gov_identity.csv`). SFC assertions remain at 7/13/16/17/18/19.
- Inequality metrics: added `io/metrics.py` (Gini, Lorenz, top shares) and hooks in `io/plots.py` to render basic Gini plots when an `inequality.csv` exists.
- CI parity gate (conditional): updated `.github/workflows/ci.yml` to conditionally run the baseline parity step when golden baseline CSV is present, and upload `reports/` as CI artifact.
- Ergonomics: added new Make targets `param-map` and `parity-report` for quick mapping and parity report generation.

2. COMMANDS I RAN
- Slice‑3 smoke (100 periods) and identity tail check:
  - `python -m s120_inequality_innovation.mc.slice3_runner`
  - Tail `notes_gov_identity.csv` (t=98–100):
    - `98,18.814330,18.814330,0.000000,0.000000,True`
    - `99,18.856077,18.856077,0.000000,0.000000,True`
    - `100,18.897923,18.897923,0.000000,0.000000,True`
- Tests: `pytest -q` → `3 passed, 1 skipped` (parity test skipped without goldens).

3. DIFFS (FULL DIFFS FOR MOST IMPORTANT CHANGES)

File: s120_inequality_innovation/oracle/extract_params.py
```
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple
import xml.etree.ElementTree as ET
import yaml


def _flatten_xml(elem: ET.Element, prefix: str = "") -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    tag = elem.tag.split("}")[-1]
    key_base = f"{prefix}/{tag}" if prefix else tag
    text = (elem.text or "").strip()
    if text:
        data[key_base] = text
    for k, v in elem.attrib.items():
        data[f"{key_base}@{k}"] = v
    for child in list(elem):
        data.update(_flatten_xml(child, key_base))
    return data


def extract_params(xml_path: Path) -> Dict[str, Any]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    return _flatten_xml(root)


def load_mapping(map_yaml: Path) -> Dict[str, str]:
    with open(map_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def mapping_report(extracted: Dict[str, Any], mapping: Dict[str, str]) -> Tuple[str, int, int]:
    lines = ["# Params Mapping Report", "", "XML Key | YAML Key | XML Value", "---|---|---"]
    mapped = 0
    for xk, yk in mapping.items():
        if xk in extracted:
            lines.append(f"{xk} | {yk} | {extracted[xk]}")
            mapped += 1
        else:
            lines.append(f"{xk} | {yk} | MISSING")
    unmapped = [k for k in extracted.keys() if k not in mapping]
    lines.append("")
    lines.append(f"Unmapped XML keys: {len(unmapped)}")
    for k in sorted(unmapped)[:50]:
        lines.append(f"- {k}")
    return "\n".join(lines), mapped, len(unmapped)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Extract JMAB XML params to JSON; optional mapping report")
    p.add_argument("--xml", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("artifacts/golden_java/params_extracted.json"))
    p.add_argument("--map", type=Path, help="YAML mapping file (XML key -> YAML dotted key)")
    p.add_argument("--report", action="store_true", help="Also generate mapping report markdown next to --out or in reports/")
    args = p.parse_args()
    data = extract_params(args.xml)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"Wrote {args.out}")
    if args.report and args.map:
        mapping = load_mapping(args.map)
        md, mapped, unmapped = mapping_report(data, mapping)
        report_path = Path("reports/params_mapping.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(md, encoding="utf-8")
        print(f"Report written to {report_path} (mapped={mapped}, unmapped={unmapped})")


if __name__ == "__main__":
    main()
```

File: s120_inequality_innovation/io/metrics.py
```
from __future__ import annotations

from typing import Iterable, Tuple
import numpy as np
import pandas as pd


def gini(array: Iterable[float]) -> float:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return float("nan")
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    n = x.size
    if n == 0 or x.sum() == 0:
        return 0.0
    cumx = np.cumsum(x)
    g = (n + 1 - 2 * (cumx.sum() / cumx[-1])) / n
    return float(g)


def lorenz_curve(array: Iterable[float]) -> Tuple[np.ndarray, np.ndarray]:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return np.array([0.0]), np.array([0.0])
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    cumx = np.cumsum(x)
    cumx = np.insert(cumx, 0, 0.0)
    cumx = cumx / cumx[-1] if cumx[-1] != 0 else cumx
    p = np.linspace(0.0, 1.0, cumx.size)
    return p, cumx


def top_share(array: Iterable[float], top_fraction: float = 0.1) -> float:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return float("nan")
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    n_top = max(1, int(np.ceil(top_fraction * x.size)))
    return float(np.sum(x[-n_top:]) / (np.sum(x) + 1e-12))


def compute_inequality_df(income: Iterable[float], wealth: Iterable[float]) -> pd.DataFrame:
    gi = gini(income)
    gw = gini(wealth)
    return pd.DataFrame({"Gini_income": [gi], "Gini_wealth": [gw]})
```

Condensed diffs for other changes
- `s120_inequality_innovation/io/plots.py`: added `plot_lorenz()` to render Gini plots from a CSV; kept existing smoke plots unchanged.
- `.github/workflows/ci.yml`: added a conditional parity step executed only when `artifacts/golden_java/baseline/series.csv` exists; uploads the `reports/` directory as CI artifact.
- `Makefile`: added `param-map` (extracts XML params and writes mapping report) and `parity-report` (runs comparator and writes `reports/baseline_parity.md`).
- `s120_inequality_innovation/core/slice3_engine.py`: extended liquidity support (CB advances), capital tracking, dividend suppression, and continued logging of SFC residuals and government identity (see repo for full context).

4. ARTIFACTS PRODUCED/UPDATED
- `artifacts/python/baseline_slice3/run_001/series.csv`
- `artifacts/python/baseline_slice3/run_001/fm_residuals.csv` (cut‑points 7/13/16/17/18/19; zeros)
- `artifacts/python/baseline_slice3/run_001/notes_gov_identity.csv` (identity_ok=True in smoke)
- `reports/params_mapping.md` (generated once XML provided via env)
- `reports/baseline_parity.md` (generated by CI or Make target once goldens exist)

5. RESULTS / CHECKS
- Tests: `3 passed, 1 skipped` (parity baseline skipped without goldens)
- Slice‑3 government identity (last three lines):
  - `98,18.814330,18.814330,0.000000,0.000000,True`
  - `99,18.856077,18.856077,0.000000,0.000000,True`
  - `100,18.897923,18.897923,0.000000,0.000000,True`
- Slice‑3 SFC residuals: zeros at 13/16/17/18/19 for t=100 (see fm_residuals tail)

6. ISSUES & BLOCKERS
- Java oracle (baseline + frontiers) not executed in this environment due to missing JDK/WSL; the harness and docs are ready. Please run `make oracle-baseline` and `make oracle-frontiers` on WSL to deposit goldens; CI parity will pick them up automatically.
- Parameter mapping report requires the baseline XML path; once available, run `make param-map` to generate and review `reports/params_mapping.md`.

7. UPDATED BACKLOG (full YAML INLINE)
```yaml
- id: M1
  title: Milestone – Engine ready (sfctools skeleton, scheduler, MC, CI)
  rationale: Deterministic SFC engine with the 19-step loop, artifacting, diagnostics, and CI.
  paper_refs:
    - {section: "Sequencing & accounting discipline", page: null, eq_or_fig_or_tab: "19-step; FlowMatrix"}
  deps: []
  instructions: FlowMatrix glue; 19-step scheduler; seeds & MC runner; smoke plots; CI.
  acceptance_criteria: "FlowMatrix checks pass at steps 3/7/12/16/19; smoke MC creates non-empty CSVs; CI green."
  artifacts_expected: ["artifacts/smoke/*.csv", "artifacts/smoke/plots/*.png", ".github/workflows/ci.yml"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: M2
  title: Milestone – Baseline parity vs Java
  rationale: Match baseline macro & inequality dynamics to oracle within tolerances.
  paper_refs:
    - {section: "Baseline & validation window", page: null, eq_or_fig_or_tab: "t=501–1000; macro panels"}
  deps: ["M1", "T-ORACLE-RUN-FRONTIERS", "T-GOLDEN-BASELINE", "T-BL-SLICE1", "T-BL-SLICE2", "T-BL-SLICE3-EXT"]
  instructions: Implement baseline behaviors and compare to Java golden CSVs (baseline).
  acceptance_criteria: "MC means (t=501–1000) for GDP, C, I, inflation, unemployment, C-sector productivity within ±10% of oracle; co-movements preserved; inequality paths qualitatively consistent."
  artifacts_expected: ["artifacts/golden_java/baseline/*.csv", "artifacts/python/baseline/*.csv", "reports/baseline_parity.md"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: M3
  title: Milestone – Experiments parity (θ & tu sweeps)
  rationale: Replicate direction and relative magnitudes for policy grids.
  paper_refs:
    - {section: "Policy experiments", page: null, eq_or_fig_or_tab: "Progressive tax θ; wage rigidity tu"}
  deps: ["M2", "T-GOLDEN-EXPTS"]
  instructions: Implement θ- and tu-sweeps; compute MC averages (t=501–1000); compare Δ vs baseline.
  acceptance_criteria: "Signs & ordering match; |Δ| errors ≤10% vs oracle; Lorenz/Gini patterns qualitatively consistent."
  artifacts_expected: ["artifacts/experiments/tax_sweep/*", "artifacts/experiments/wage_sweep/*", "reports/experiments_parity.md"]
  repo_paths_hint: ["s120_inequality_innovation/*"]
  estimate: L

- id: T-SKEL
  title: Project skeleton on sfctools + param registry
  rationale: Parameterization mirrors Appendix A table to avoid drift.
  paper_refs:
    - {section: "Appendix A", page: null, eq_or_fig_or_tab: "Table 1 – Parameters"}
  deps: ["M1"]
  instructions: Registry loads/validates defaults; include χ, ε, ν, μ₀, θ, tu, rates, thresholds per Table 1.
  acceptance_criteria: "params_default.yaml keys/values match Table 1; tests pass."
  artifacts_expected: ["s120_inequality_innovation/config/params_default.yaml", "tests/test_params.py"]
  repo_paths_hint: ["s120_inequality_innovation/config", "s120_inequality_innovation/core/registry.py"]
  estimate: M

- id: T-SCHED
  title: 19-step scheduler scaffold + FlowMatrix checks
  rationale: Enforce exact order of events and accounting cut-points.
  paper_refs:
    - {section: "Sec. 2.1", page: null, eq_or_fig_or_tab: "19-step sequence"}
  deps: ["T-SKEL"]
  instructions: Scheduler invokes step stubs; SFC checks after steps 3/7/12/16/19.
  acceptance_criteria: "Unit test enumerates 19 labels; SFC check passes in smoke."
  artifacts_expected: ["tests/test_scheduler_19steps.py", "artifacts/smoke/timeline.csv"]
  repo_paths_hint: ["s120_inequality_innovation/core/scheduler.py", "s120_inequality_innovation/core/flowmatrix_glue.py"]
  estimate: M

- id: T-MC
  title: Monte Carlo runner + seed management + artifact foldering
  rationale: Reproducibility for baseline/experiments; fixed streams.
  paper_refs:
    - {section: "Simulation setup", page: null, eq_or_fig_or_tab: "1000 periods; 25 reps"}
  deps: ["T-SCHED"]
  instructions: Named RNG streams; per-run artifacts; aggregated stats.
  acceptance_criteria: "25-run baseline executes; seeds logged; summary exists."
  artifacts_expected: ["artifacts/baseline/run_*/series.csv", "artifacts/baseline/summary_mc.csv"]
  repo_paths_hint: ["s120_inequality_innovation/mc/runner.py", "s120_inequality_innovation/io/writer.py"]
  estimate: M

- id: T-SFCTOOLS-INTEGRATE
  title: Integrate real sfctools; residual checks & diagnostics
  rationale: Use tested SFC engine; fail fast on accounting errors.
  paper_refs:
    - {section: "Stock–flow consistency", page: null, eq_or_fig_or_tab: "FlowMatrix guidance"}
  deps: ["T-SCHED"]
  instructions: Use PyPI sfctools; add fm_residuals.csv (max row/col abs) at cut-points; strict mode toggle.
  acceptance_criteria: "5-period smoke: residuals ≤1e-10 at all cut-points; tests pass."
  artifacts_expected: ["artifacts/smoke/fm_residuals.csv", "tests/test_flowmatrix_consistency.py"]
  repo_paths_hint: ["requirements.txt", "s120_inequality_innovation/core/flowmatrix_glue.py"]
  estimate: S

- id: T-ORACLE-HARNESS
  title: JPype primary harness; Py4J fallback
  rationale: Programmatic launches of JMAB+S120 model as oracle.
  paper_refs:
    - {section: "JMAB entry point & config", page: null, eq_or_fig_or_tab: "DesktopSimulationManager; jabm.config"}
  deps: ["T-MC"]
  instructions: `startJVM(classpath=[...]); System.setProperty("jabm.config", xml); DesktopSimulationManager.main([])`.
  acceptance_criteria: "CLI help works; dry-run prints resolved cp/xml; baseline run produces CSVs."
  artifacts_expected: ["s120_inequality_innovation/oracle/*.py", "oracle/README.md"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/*"]
  estimate: M

- id: T-ORACLE-CSV-EXPORT
  title: Standardize Java→CSV output schema
  rationale: Ensure reproducible, parsable outputs (canonical headers).
  paper_refs:
    - {section: "Variables & metrics", page: null, eq_or_fig_or_tab: "Figures/Tables variable set"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Configure observers to write per-period: GDP, CONS, INV, INFL, UNEMP, PROD_C, Gini_income, Gini_wealth, Debt_GDP; plus t; canonicalize headers.
  acceptance_criteria: "CSV has horizon rows; standardized headers; meta.json includes params & seed."
  artifacts_expected: ["artifacts/golden_java/*/series.csv", "artifacts/golden_java/*/meta.json"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/*", "artifacts/golden_java/*"]
  estimate: M

- id: T-ORACLE-WSL-SETUP
  title: WSL Java setup & classpath wiring (JMAB + S120)
  rationale: Enable headless CLI/JPype launches in WSL.
  paper_refs:
    - {section: "JMAB overview", page: null, eq_or_fig_or_tab: "Main class & system property"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Install OpenJDK; clone jmab and InequalityInnovation; compile; construct CLASSPATH and XML path.
  acceptance_criteria: "`java -version` ≥ 17; DesktopSimulationManager runs with -Djabm.config=<xml> in a smoke run; classpath file recorded."
  artifacts_expected: ["docs/java_wsl_setup.md", "s120_inequality_innovation/oracle/classpath.txt"]
  repo_paths_hint: ["docs/*", "s120_inequality_innovation/oracle/*"]
  estimate: S

- id: T-ORACLE-RUN-FRONTIERS
  title: Oracle runs – Baseline + frontier scenarios
  rationale: Golden CSVs for acceptance tests.
  paper_refs:
    - {section: "Policy levers", page: null, eq_or_fig_or_tab: "θ (progressive tax), tu (wage rigidity)"}
  deps: ["T-ORACLE-CSV-EXPORT", "T-ORACLE-WSL-SETUP"]
  instructions: Run baseline; θ∈{0.0,1.5}; tu∈{1,4}; fixed seed/horizon; deposit CSV+meta under artifacts/golden_java.
  acceptance_criteria: "5 CSVs present; horizon rows; canonical headers; meta.json includes seed & effective θ/tu."
  artifacts_expected: ["artifacts/golden_java/baseline/series.csv", "artifacts/golden_java/tax_theta*/series.csv", "artifacts/golden_java/wage_tu*/series.csv"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/cli.py", "artifacts/golden_java/*"]
  estimate: M

- id: T-PARAM-HARMONIZE
  title: Harmonize YAML with Java XML (one-to-one map)
  rationale: Prevent calibration drift in Python vs Java.
  paper_refs:
    - {section: "Appendix A Table 1", page: null, eq_or_fig_or_tab: "Param registry"}
  deps: ["T-ORACLE-HARNESS"]
  instructions: Extract XML params; map to YAML via param_map.yaml; produce diff & doc.
  acceptance_criteria: "`params_extracted.json` exists; `reports/params_mapping.md` diff empty or justified."
  artifacts_expected: ["artifacts/golden_java/params_extracted.json", "reports/params_mapping.md"]
  repo_paths_hint: ["s120_inequality_innovation/oracle/extract_params.py", "s120_inequality_innovation/config/param_map.yaml"]
  estimate: M

- id: T-GOLDEN-BASELINE
  title: Python↔Java baseline acceptance test
  rationale: Automate parity checks on steady window.
  paper_refs:
    - {section: "Validation window", page: null, eq_or_fig_or_tab: "t=501–1000"}
  deps: ["T-ORACLE-RUN-FRONTIERS", "T-SFCTOOLS-INTEGRATE"]
  instructions: Align series; compute window means; assert relative error ≤10% for GDP, C, I, inflation, unemployment, productivity.
  acceptance_criteria: "tests/test_parity_baseline.py passes; `reports/baseline_parity.md` written."
  artifacts_expected: ["reports/baseline_parity.md", "tests/test_parity_baseline.py"]
  repo_paths_hint: ["s120_inequality_innovation/io/golden_compare.py", "tests/*"]
  estimate: M

- id: T-GOLDEN-EXPTS
  title: Acceptance tests for θ- and tu-sweeps
  rationale: Lock experiment outcomes & guard regressions.
  paper_refs:
    - {section: "Policy experiments", page: null, eq_or_fig_or_tab: "Deltas vs baseline"}
  deps: ["T-GOLDEN-BASELINE"]
  instructions: Compute (MC window mean) deltas vs baseline; assert sign & ordering; |Δ| error ≤10%.
  acceptance_criteria: "tests/test_parity_experiments.py passes; `reports/experiments_parity.md`"
  artifacts_expected: ["reports/experiments_parity.md", "tests/test_parity_experiments.py"]
  repo_paths_hint: ["s120_inequality_innovation/mc/runner.py", "s120_inequality_innovation/io/golden_compare.py"]
  estimate: M

- id: T-BL-SLICE1
  title: Baseline behaviour slice 1 (Eqs. 3.1–3.10, 3.22)
  rationale: Expectations, output/inventories, labor demand, pricing/markup, wage revision.
  paper_refs:
    - {section: "Model core", page: null, eq_or_fig_or_tab: "Eqs. 3.1–3.2, 3.3–3.6, 3.9–3.10, 3.22"}
  deps: ["T-SFCTOOLS-INTEGRATE"]
  instructions: Implement and wire steps 1–3, 9, 12, 14 with FlowMatrix entries.
  acceptance_criteria: "100-period run closes SFC; inventory ratio near ν±0.05 by t≥50; wages>0; μ∈[0,1]."
  artifacts_expected: ["artifacts/python/baseline_slice1/run_*/series.csv", "artifacts/python/baseline_slice1/fm_residuals.csv"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice1_engine.py", "s120_inequality_innovation/mc/slice1_runner.py"]
  estimate: M

- id: T-BL-SLICE2
  title: Baseline behaviour slice 2 – Investment, capital vintages, innovation/imitation (Eqs. 3.11–3.16; Steps 4–5–10–11)
  rationale: Add capital accumulation & Schumpeterian dynamics driving productivity/growth.
  paper_refs:
    - {section: "Investment & innovation", page: null, eq_or_fig_or_tab: "Eqs. 3.11–3.16"}
  deps: ["T-BL-SLICE1"]
  instructions: Desired capacity growth; investment demand; vintage comparison (ε intensity); R&D success & imitation probabilities; t+1 delivery.
  acceptance_criteria: "300‑period run: PROD_C trend >0; Step‑11 lag respected; SFC residuals ≤1e‑10; innovation success rates within ±10% of target over t=100–300."
  artifacts_expected: ["artifacts/python/baseline_slice2/run_001/{series.csv,fm_residuals.csv,diag_innovation.csv}", "reports/slice2_notes.md"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice2_engine.py", "s120_inequality_innovation/mc/slice2_runner.py"]
  estimate: L

- id: T-BL-SLICE3-EXT
  title: Baseline behaviour slice 3 – extend credit/deposits/taxes/CB/bonds to constraints & defaults
  rationale: Close financial circuit under constraints and prepare policy levers for experiments.
  paper_refs:
    - {section: "Finance & policy blocks", page: null, eq_or_fig_or_tab: "Steps 6–7–13–15–16–17–18–19; Eqs. 3.24–3.28"}
  deps: ["T-BL-SLICE2"]
  instructions: Implement bank capital & liquidity ratio constraints; deposit switching (ε, χ); CB advances & bond ops; default & recap hooks; ensure government funding identity each period.
  acceptance_criteria: "End-of-period stocks reconcile; gov deficit = Δbonds + CB ops − Δdeposits; bank constraints satisfied; SFC residuals ≤1e‑10; defaults logged."
  artifacts_expected: ["artifacts/python/baseline_slice3/run_001/{series.csv,fm_residuals.csv,notes_gov_identity.csv}", "reports/slice3_notes.md"]
  repo_paths_hint: ["s120_inequality_innovation/core/slice3_engine.py", "s120_inequality_innovation/mc/slice3_runner.py"]
  estimate: L

- id: T-INEQ-METRICS
  title: Inequality metrics & figures
  rationale: Required for validation targets and experiment analysis.
  paper_refs:
    - {section: "Distributional outcomes", page: null, eq_or_fig_or_tab: "Lorenz & Gini (income/wealth)"}
  deps: ["T-BL-SLICE3-EXT"]
  instructions: Compute Lorenz curves & Gini for income and wealth per period; save MC window means; plotting scripts.
  acceptance_criteria: "CSV with per-period Gini_income & Gini_wealth; figures regenerate deterministically; comparator picks metrics when present."
  artifacts_expected: ["artifacts/python/baseline/*/inequality.csv", "artifacts/figures/inequality_*.png"]
  repo_paths_hint: ["s120_inequality_innovation/io/plots.py", "notebooks/figures.ipynb"]
  estimate: M
```

8. SNAPSHOT
- Accounting spine (sfctools FlowMatrix) active with cut‑point assertions and residual logs.
- Oracle harness hardened; param extraction/reporting added; CI parity gate conditional on goldens.
- Slice‑3 finance core extended with CB liquidity backstop and bank capital handling; government identity holds in smoke.

9. GIT COMMITS MADE
- Applied via patches in this environment (no VCS commits). Suggested commit grouping:
  - feat(oracle): extractor report + mapping; CI parity gate
  - feat(finance): extend slice‑3 (CB advances, capital, identity log)
  - feat(metrics): add Gini/Lorenz utilities and plots hook
  - chore(make): add `param-map` and `parity-report`

10. NEXT SUGGESTED STEPS
- On WSL: run oracle baseline and frontiers via `make oracle-baseline` and `make oracle-frontiers`; commit `artifacts/golden_java/**` plus `meta.json` (include seed/horizon/config hash in commit message).
- Run `make parity-report` (or let CI generate) to produce `reports/baseline_parity.md` over t=501–1000; iterate Slice‑3 constraints and Slice‑2 calibration to reduce errors.
- Extend Slice‑3 to include deposit switching (ε, χ), CB bond ops, and default/recap hooks; implement inequality metrics pipeline on real income/wealth series.

