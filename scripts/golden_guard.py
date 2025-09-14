#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd


BASE_META = Path("artifacts/golden_java/baseline/meta.json")
BASE_SER = Path("artifacts/golden_java/baseline/series.csv")
FRONTIER_SER = Path("artifacts/golden_java/tax_theta1.5/series.csv")


def guard_no_fallback(meta_path: Path) -> None:
    if not meta_path.exists():
        print("skipped: golden baseline meta not found")
        return
    try:
        m = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit(f"error: failed to read meta.json: {e}")
    raw = m.get("raw_sources", [])
    if any(isinstance(x, str) and x.startswith("FALLBACK:") for x in raw):
        raise SystemExit("guard failed: FALLBACK found in baseline raw_sources")
    print("ok: baseline raw_sources contains no FALLBACK markers")


def guard_gdp_diff(base_csv: Path, frontier_csv: Path) -> None:
    if not (base_csv.exists() and frontier_csv.exists()):
        print("skipped: baseline or frontier series not found")
        return
    b = pd.read_csv(base_csv)
    f = pd.read_csv(frontier_csv)
    wb = b[(b["t"] >= 501) & (b["t"] <= 1000)]["GDP"].mean()
    wf = f[(f["t"] >= 501) & (f["t"] <= 1000)]["GDP"].mean()
    if pd.isna(wb) or pd.isna(wf):
        raise SystemExit("guard failed: empty window means for GDP")
    if abs(float(wb) - float(wf)) <= 1e-12:
        raise SystemExit("guard failed: frontier equals baseline GDP mean — placeholder suspected")
    print("ok: GDP means differ between baseline and tax_theta1.5")


def main() -> int:
    guard_no_fallback(BASE_META)
    guard_gdp_diff(BASE_SER, FRONTIER_SER)
    return 0


if __name__ == "__main__":
    sys.exit(main())

