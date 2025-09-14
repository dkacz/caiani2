from __future__ import annotations

import time
from pathlib import Path
from typing import List

import numpy as np

from s120_inequality_innovation.core.registry import ParameterRegistry
from s120_inequality_innovation.core.rng import load_seeds, build_streams
from s120_inequality_innovation.io.writer import ArtifactWriter, summarize_runs
from s120_inequality_innovation.core.scheduler import STEP_LABELS


def run_baseline_smoke(artifacts_root: Path = Path("artifacts") / "baseline", overrides: dict | None = None) -> List[Path]:
    params = ParameterRegistry.from_files(overrides=overrides)
    seeds = load_seeds()
    runs = []
    mc = int(params.get("meta.mc_runs"))
    horizon = int(params.get("meta.horizon"))
    for run_id in range(1, mc + 1):
        # Vary seeds deterministically per run_id
        seeds_run = {k: v + run_id for k, v in seeds.items()}
        rngs = build_streams(seeds_run)
        run_dir = artifacts_root / f"run_{run_id:03d}"
        meta = {
            "run_id": run_id,
            "seeds": seeds_run,
            "config_hash": params.config_hash(),
            "horizon": horizon,
        }
        aw = ArtifactWriter.create(run_dir, meta)
        # Generate placeholder series using RNGs
        gdp = 100.0
        cons = 60.0
        inv = 20.0
        infl = 0.02
        unemp = 0.07
        for t in range(1, horizon + 1):
            # simple AR(1)-like evolutions to create plausible series
            shock_g = rngs.rng_model.normal(0, 0.2)
            shock_c = rngs.rng_model.normal(0, 0.1)
            shock_i = rngs.rng_model.normal(0, 0.08)
            shock_pi = rngs.rng_model.normal(0, 0.001)
            shock_u = rngs.rng_model.normal(0, 0.002)
            gdp = max(1.0, gdp * (1 + shock_g * 0.001))
            cons = max(0.1, cons * (1 + shock_c * 0.001))
            inv = max(0.1, inv * (1 + shock_i * 0.001))
            infl = max(-0.05, infl * 0.99 + shock_pi)
            unemp = min(0.5, max(0.01, unemp * 0.995 + shock_u))
            aw.append_series(t, gdp, cons, inv, infl, unemp)
            # Also append a minimal timeline row (step 19 only to keep file small)
            aw.append_timeline_row([t, 19, STEP_LABELS[-1], time.time_ns()])
        runs.append(run_dir)
    summarize_runs(runs, artifacts_root / "summary_mc.csv")
    return runs


if __name__ == "__main__":
    run_baseline_smoke()
