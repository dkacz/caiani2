from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd


@dataclass
class ParityResult:
    rel_errors: Dict[str, float]
    window: Tuple[int, int]


def _window_mean(df: pd.DataFrame, cols: List[str], t0: int, t1: int) -> pd.Series:
    w = df[(df["t"] >= t0) & (df["t"] <= t1)]
    present = [c for c in cols if c in w.columns]
    return w[present].mean()


def compare_baseline(python_csv: Path, java_csv: Path, t0: int = 501, t1: int = 1000) -> ParityResult:
    p = pd.read_csv(python_csv)
    j = pd.read_csv(java_csv)
    j = canonicalize_java_headers(j)
    cols = ["GDP", "CONS", "INV", "INFL", "UNEMP", "PROD_C"]
    pm = _window_mean(p, cols, t0, t1)
    jm = _window_mean(j, cols, t0, t1)
    rel: Dict[str, float] = {}
    for c in cols:
        if c not in pm.index or c not in jm.index:
            continue
        denom = abs(jm[c]) if abs(jm[c]) > 1e-12 else 1.0
        rel[c] = float(abs(pm[c] - jm[c]) / denom)
    return ParityResult(rel_errors=rel, window=(t0, t1))


def write_baseline_report(res: ParityResult, out_md: Path):
    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("# Baseline Parity Report")
    lines.append("")
    lines.append(f"Window: t={res.window[0]}–{res.window[1]}")
    lines.append("")
    lines.append("Metric | Relative Error")
    lines.append("---|---")
    for k, v in res.rel_errors.items():
        lines.append(f"{k} | {v:.4%}")
    out_md.write_text("\n".join(lines), encoding="utf-8")


def canonicalize_java_headers(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        # GDP
        "RealGDP": "GDP",
        "GDP_nominal": "GDP",
        "GDP": "GDP",
        # Consumption
        "RealC": "CONS",
        "Consumption": "CONS",
        "CONS": "CONS",
        # Investment
        "RealI": "INV",
        "Investment": "INV",
        "INV": "INV",
        # Inflation
        "Inflation": "INFL",
        "CPI_infl": "INFL",
        "INFL": "INFL",
        # Unemployment
        "Unemployment": "UNEMP",
        "u": "UNEMP",
        "UNEMP": "UNEMP",
        # Productivity (C-sector)
        "ProdC": "PROD_C",
        "LaborProductivityC": "PROD_C",
        "PROD_C": "PROD_C",
        # Inequality & debt
        "GiniIncome": "Gini_income",
        "GiniWealth": "Gini_wealth",
        "DebtGDP": "Debt_GDP",
    }
    cols = {c: mapping.get(c, c) for c in df.columns}
    return df.rename(columns=cols)
