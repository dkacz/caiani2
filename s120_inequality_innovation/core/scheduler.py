from __future__ import annotations

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List

from .flowmatrix_glue import FlowMatrix, FMContext, fm_start_period, fm_log, fm_assert_ok
from .registry import ParameterRegistry


STEP_LABELS: List[str] = [
    "01_production_planning",
    "02_labor_demand",
    "03_prices_interest_reservation_wage_revision",
    "04_desired_capacity_growth",
    "05_capital_market_vintage_choice",
    "06_credit_demand",
    "07_credit_supply",
    "08_labor_markets_w_o_r_m",
    "09_production",
    "10_research_and_development",
    "11_capital_purchase_delivery_next",
    "12_consumption_market",
    "13_interest_and_principal_payments",
    "14_wages_and_dole",
    "15_taxes",
    "16_dividends",
    "17_deposit_market",
    "18_bond_purchases",
    "19_cb_advances",
]


@dataclass
class SchedulerResult:
    timeline_csv: Path
    fm_residuals_csv: Path | None = None


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def run_simulation(
    params: ParameterRegistry,
    horizon: int,
    artifacts_dir: Path,
) -> SchedulerResult:
    _ensure_dir(artifacts_dir)
    fm = FlowMatrix()
    ctx = FMContext(fm=fm)
    timeline_path = artifacts_dir / "timeline.csv"
    fmres_path = artifacts_dir / "fm_residuals.csv"
    with open(fmres_path, "w", newline="", encoding="utf-8") as fr:
        wres = csv.writer(fr)
        wres.writerow(["t", "step", "max_row_abs", "max_col_abs"])  # placeholders
    with open(timeline_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t", "step", "label", "ts"])
        for t in range(1, horizon + 1):
            fm_start_period(ctx, t)
            for i, label in enumerate(STEP_LABELS, start=1):
                # Minimal neutral flows to let SFC checks run without business logic
                fm_log(ctx, source=f"SYS:{label}", sink="SYS:buffer", amount=0.0, label=label)
                if i in {3, 7, 12, 16, 19}:
                    fm_assert_ok(ctx)
                    # Placeholder residuals (0.0, 0.0) while only zero-flows exist
                    r, c = (ctx.last_residuals or (0.0, 0.0))
                    with open(fmres_path, "a", newline="", encoding="utf-8") as fr:
                        wres = csv.writer(fr)
                        wres.writerow([t, i, f"{abs(r):.12e}", f"{abs(c):.12e}"])
                w.writerow([t, i, label, time.time_ns()])
    return SchedulerResult(timeline_csv=timeline_path, fm_residuals_csv=fmres_path)
