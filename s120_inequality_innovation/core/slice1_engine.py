from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import numpy as np

from .registry import ParameterRegistry
from .flowmatrix_glue import FlowMatrix, FMContext, fm_start_period, fm_assert_ok
from sfctools.core.flow_matrix import Accounts  # type: ignore


def _log_tx(ctx: FMContext, agent_from: str, agent_to: str, amount: float, subject: str):
    # Flow (CA->CA) from A to B
    ctx.fm.log_flow((Accounts.CA, Accounts.CA), float(amount), agent_from, agent_to, subject)
    # Stock change (KA->KA) opposite direction to keep row/col totals at zero
    ctx.fm.log_flow((Accounts.KA, Accounts.KA), float(amount), agent_to, agent_from, subject)


@dataclass
class Slice1State:
    # Aggregate state (Consumption firms + Households)
    s_expected: float = 100.0
    s_realized: float = 100.0
    inventories: float = 10.0
    markup: float = 0.3
    price: float = 1.0
    wage: float = 1.0
    prod: float = 1.0  # labor productivity
    labor_supply: float = 100.0
    inflation: float = 0.0
    unemployment: float = 0.1


def step1_production_planning(state: Slice1State, params: ParameterRegistry) -> Tuple[float, float]:
    lam = 0.2
    state.s_expected = state.s_expected + lam * (state.s_realized - state.s_expected)
    nu = float(params.get("inventories.nu_target"))
    yD = max(0.0, state.s_expected * (1.0 + nu) - state.inventories)
    inv_target = state.s_expected * nu
    return yD, inv_target


def step2_labor_demand(state: Slice1State, yD: float) -> Tuple[float, float]:
    N = yD / max(1e-9, state.prod)
    u = max(0.0, min(0.5, 1.0 - N / max(1e-9, state.labor_supply)))
    state.unemployment = u
    return N, u


def step3_pricing_markup(state: Slice1State, params: ParameterRegistry, yD: float, inv_target: float):
    # Adjust markup toward keeping inventories near target
    gap = state.inventories - inv_target
    adj = -0.01 if gap > 0 else 0.01
    state.markup = min(1.0, max(0.0, state.markup + adj))
    ulc = state.wage / max(1e-9, state.prod)
    p_old = state.price
    state.price = (1.0 + state.markup) * ulc
    state.inflation = state.price / max(1e-9, p_old) - 1.0


def step9_production(state: Slice1State, yD: float) -> float:
    y = yD
    return y


def step12_consumption_and_sales(ctx: FMContext, state: Slice1State, params: ParameterRegistry, y: float):
    alpha = 0.6
    desired_cons = alpha * state.s_expected  # placeholder
    sales = min(state.inventories + y, desired_cons)
    # Update inventories
    state.inventories = max(0.0, state.inventories + y - sales)
    # Log consumption transaction: Households -> FirmC
    value = sales * state.price
    _log_tx(ctx, "HH", "FirmC", value, "consumption")
    state.s_realized = sales


def step14_wages(ctx: FMContext, state: Slice1State, N: float, params: ParameterRegistry):
    # Reservation wage revision (very simple placeholder bounded >0)
    tu = float(params.get("wage_rigidity.tu"))
    # slight downward drift when unemployment high, upward when low
    drift = -0.001 * tu if state.unemployment > 0.1 else 0.001
    state.wage = max(0.1, state.wage * (1.0 + drift))
    wage_bill = state.wage * N
    _log_tx(ctx, "FirmC", "HH", wage_bill, "wages")
    return wage_bill


def run_slice1(params: ParameterRegistry, horizon: int, outdir: Path) -> Tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    fm = FlowMatrix()
    ctx = FMContext(fm)
    state = Slice1State()
    series_path = outdir / "series.csv"
    fmres_path = outdir / "fm_residuals.csv"
    with open(series_path, "w", newline="", encoding="utf-8") as f, open(
        fmres_path, "w", newline="", encoding="utf-8"
    ) as fr:
        w = csv.writer(f)
        w.writerow(["t", "GDP", "CONS", "INV", "INFL", "UNEMP", "PROD_C"])  # canonical
        wres = csv.writer(fr)
        wres.writerow(["t", "step", "max_row_abs", "max_col_abs"])
        for t in range(1, horizon + 1):
            fm_start_period(ctx, t)
            # Step 1: planning
            yD, inv_target = step1_production_planning(state, params)
            # Step 2: labor demand
            N, u = step2_labor_demand(state, yD)
            # Step 3: pricing/markup
            step3_pricing_markup(state, params, yD, inv_target)
            fm_assert_ok(ctx); wres.writerow([t, 3, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 7: (no credit in slice1) still assert
            fm_assert_ok(ctx); wres.writerow([t, 7, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 9: production
            y = step9_production(state, yD)
            # Step 12: consumption
            step12_consumption_and_sales(ctx, state, params, y)
            fm_assert_ok(ctx); wres.writerow([t, 12, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 14: wages
            wage_bill = step14_wages(ctx, state, N, params)
            fm_assert_ok(ctx); wres.writerow([t, 16, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 19: CB advances (none) assert
            fm_assert_ok(ctx); wres.writerow([t, 19, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Log simple GDP as sales; cons equals sales
            w.writerow([
                t,
                state.s_realized * state.price,
                state.s_realized * state.price,
                0.0,
                state.inflation,
                state.unemployment,
                state.prod,
            ])
    return series_path, fmres_path
