from pathlib import Path

from s120_inequality_innovation.core.registry import ParameterRegistry
from s120_inequality_innovation.core.scheduler import run_simulation


def test_flowmatrix_consistency(tmp_path: Path):
    reg = ParameterRegistry.from_files()
    res = run_simulation(reg, horizon=5, artifacts_dir=tmp_path)
    assert res.fm_residuals_csv and res.fm_residuals_csv.exists()
    lines = res.fm_residuals_csv.read_text(encoding="utf-8").strip().splitlines()
    # header + (5 periods * 5 cut-points) lines expected
    assert len(lines) == 1 + 5 * 5
    # verify residuals are within tolerance (placeholders are zeros)
    for ln in lines[1:]:
        _, _, r, c = ln.split(",")
        assert float(r) <= 1e-10
        assert float(c) <= 1e-10

