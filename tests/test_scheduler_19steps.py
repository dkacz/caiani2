from pathlib import Path

from s120_inequality_innovation.core.scheduler import run_simulation, STEP_LABELS
from s120_inequality_innovation.core.registry import ParameterRegistry


def test_scheduler_labels_and_timeline(tmp_path: Path):
    reg = ParameterRegistry.from_files()
    res = run_simulation(reg, horizon=2, artifacts_dir=tmp_path)
    assert res.timeline_csv.exists()
    lines = res.timeline_csv.read_text(encoding="utf-8").strip().splitlines()
    # header + 2 periods * 19 steps = 39 lines
    assert len(lines) == 1 + 2 * len(STEP_LABELS)
    # ensure a known label appears
    assert any(STEP_LABELS[0] in ln for ln in lines)

