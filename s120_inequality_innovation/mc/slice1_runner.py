from __future__ import annotations

from pathlib import Path

from s120_inequality_innovation.core.registry import ParameterRegistry
from s120_inequality_innovation.core.slice1_engine import run_slice1


def run_baseline_slice1(out_root: Path = Path("artifacts") / "python" / "baseline_slice1", horizon: int = 100):
    params = ParameterRegistry.from_files()
    rundir = out_root / "run_001"
    series, fmres = run_slice1(params, horizon=horizon, outdir=rundir)
    return rundir


if __name__ == "__main__":
    run_baseline_slice1()

