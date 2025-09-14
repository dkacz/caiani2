from __future__ import annotations

from pathlib import Path

from s120_inequality_innovation.core.registry import ParameterRegistry
from s120_inequality_innovation.core.slice2_engine import run_slice2


def run_baseline_slice2(out_root: Path = Path("artifacts") / "python" / "baseline_slice2", horizon: int = 300):
    params = ParameterRegistry.from_files()
    rundir = out_root / "run_001"
    run_slice2(params, horizon=horizon, outdir=rundir, seed=123)
    return rundir


if __name__ == "__main__":
    run_baseline_slice2()

