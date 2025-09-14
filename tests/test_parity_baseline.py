import os
from pathlib import Path

import pytest

from s120_inequality_innovation.io.golden_compare import compare_baseline, write_baseline_report


def test_parity_baseline_if_golden_present():
    java_csv = Path("artifacts/golden_java/baseline/series.csv")
    py_csv = Path("artifacts/baseline/run_001/series.csv")
    if not (java_csv.exists() and py_csv.exists()):
        pytest.skip("Golden or Python baseline CSV missing; skipping parity test")
    # Skip if baseline golden was produced via fallback (not a real oracle run)
    meta = Path("artifacts/golden_java/baseline/meta.json")
    if meta.exists():
        import json
        m = json.loads(meta.read_text())
        if any(isinstance(x, str) and x.startswith("FALLBACK:") for x in m.get("raw_sources", [])):
            pytest.skip("Baseline golden uses FALLBACK; skip parity until real oracle data is present")
    res = compare_baseline(py_csv, java_csv)
    # Write a short report as an artifact
    write_baseline_report(res, Path("reports/baseline_parity.md"))
    # Guard: errors must be <=10% but not all exactly 0.0 (prevents placeholder goldens)
    assert any(v != 0.0 for v in res.rel_errors.values()), "All relative errors are 0.0 — likely placeholder goldens"
    for k, v in res.rel_errors.items():
        assert v <= 0.10
