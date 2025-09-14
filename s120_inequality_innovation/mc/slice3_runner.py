from __future__ import annotations

from pathlib import Path

from s120_inequality_innovation.core.registry import ParameterRegistry
from s120_inequality_innovation.core.slice3_engine import run_slice3
import pandas as pd


def run_baseline_slice3(out_root: Path = Path("artifacts") / "python" / "baseline_slice3", horizon: int = 100):
    params = ParameterRegistry.from_files()
    rundir = out_root / "run_001"
    series, fmres = run_slice3(params, horizon=horizon, outdir=rundir)
    # Produce a small notes report summarizing binding constraints and defaults if events.csv exists
    evp = rundir / "events.csv"
    if evp.exists():
        df = pd.read_csv(evp)
        notes = [
            f"CB advances periods: {int(df['cb_advance'].sum())}",
            f"Dividends suppressed periods: {int(df['div_suppressed'].sum())}",
            f"Default events: {int(df['default_event'].sum())}",
        ]
        (out_root.parent / "slice3_notes.md").write_text("\n".join(notes), encoding="utf-8")
    return rundir


if __name__ == "__main__":
    run_baseline_slice3()
