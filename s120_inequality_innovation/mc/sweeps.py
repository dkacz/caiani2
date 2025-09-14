from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yaml

from .runner import run_baseline_smoke
from s120_inequality_innovation.core.registry import ParameterRegistry


WINDOW = (501, 1000)
METRICS = ["GDP", "CONS", "INV", "INFL", "UNEMP", "PROD_C"]


def _window_mean(csv_path: Path, t0: int, t1: int) -> Dict[str, float]:
    df = pd.read_csv(csv_path)
    dfw = df[(df["t"] >= t0) & (df["t"] <= t1)]
    out = {}
    for m in METRICS:
        if m in dfw.columns:
            out[m] = float(dfw[m].mean())
    return out


def _summary_row(scenario: str, means: Dict[str, float], baseline: Dict[str, float]) -> List[Dict[str, object]]:
    rows = []
    for m in METRICS:
        if m in means and m in baseline:
            rows.append({
                "scenario": scenario,
                "metric": m,
                "mean_window": means[m],
                "delta_vs_baseline": means[m] - baseline[m],
            })
    return rows


def _load_yaml(path: Path) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_tax_sweep(out_root: Path = Path("artifacts") / "experiments" / "tax_sweep") -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    scenarios = _load_yaml(Path("s120_inequality_innovation/config/scenarios/tax_progressive_theta_sweep.yaml"))
    grid = scenarios["grid"]["taxes.theta_progressive"]
    # Baseline
    base_dir = Path("artifacts") / "experiments" / "tax_sweep" / "baseline"
    runs = run_baseline_smoke(base_dir, overrides=None)
    base_means = _window_mean(base_dir / "run_001" / "series.csv", *WINDOW)
    rows: List[Dict[str, object]] = []
    for theta in grid:
        overrides = {"taxes": {"theta_progressive": float(theta)}}
        scen_dir = out_root / f"theta_{theta}"
        run_baseline_smoke(scen_dir, overrides=overrides)
        means = _window_mean(scen_dir / "run_001" / "series.csv", *WINDOW)
        rows.extend(_summary_row(f"theta_{theta}", means, base_means))
    df = pd.DataFrame(rows)
    out = out_root / "summary.csv"
    df.to_csv(out, index=False)
    return out


def run_wage_sweep(out_root: Path = Path("artifacts") / "experiments" / "wage_sweep") -> Path:
    out_root.mkdir(parents=True, exist_ok=True)
    scenarios = _load_yaml(Path("s120_inequality_innovation/config/scenarios/wage_rigidity_tu_sweep.yaml"))
    grid = scenarios["grid"]["wage_rigidity.tu"]
    base_dir = out_root / "baseline"
    run_baseline_smoke(base_dir, overrides=None)
    base_means = _window_mean(base_dir / "run_001" / "series.csv", *WINDOW)
    rows: List[Dict[str, object]] = []
    for tu in grid:
        overrides = {"wage_rigidity": {"tu": int(tu)}}
        scen_dir = out_root / f"tu_{tu}"
        run_baseline_smoke(scen_dir, overrides=overrides)
        means = _window_mean(scen_dir / "run_001" / "series.csv", *WINDOW)
        rows.extend(_summary_row(f"tu_{tu}", means, base_means))
    out = out_root / "summary.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    return out


if __name__ == "__main__":
    run_tax_sweep()
    run_wage_sweep()

