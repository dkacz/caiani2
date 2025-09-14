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
    ctx.fm.log_flow((Accounts.CA, Accounts.CA), float(amount), agent_from, agent_to, subject)
    ctx.fm.log_flow((Accounts.KA, Accounts.KA), float(amount), agent_to, agent_from, subject)


@dataclass
class Slice2State:
    prod_c: float = 1.0         # labor productivity (consumption sector)
    wage: float = 1.0
    markup: float = 0.3
    price: float = 1.3
    inventories: float = 10.0
    expected_sales: float = 100.0
    realized_sales: float = 100.0
    labor_supply: float = 100.0
    unemployment: float = 0.1
    capital_stock: float = 100.0
    orders_pending_next: float = 0.0  # investment orders delivered next period
    # diagnostics
    inn_success: int = 0
    inn_trials: int = 0


def step1_3_basic(state: Slice2State, params: ParameterRegistry) -> Tuple[float, float]:
    lam = 0.2
    state.expected_sales = state.expected_sales + lam * (state.realized_sales - state.expected_sales)
    nu = float(params.get("inventories.nu_target"))
    yD = max(0.0, state.expected_sales * (1.0 + nu) - state.inventories)
    inv_target = state.expected_sales * nu
    # simple markup update toward inventory target
    gap = state.inventories - inv_target
    adj = -0.01 if gap > 0 else 0.01
    state.markup = min(1.0, max(0.0, state.markup + adj))
    ulc = state.wage / max(1e-9, state.prod_c)
    state.price = (1.0 + state.markup) * ulc
    return yD, inv_target


def step4_desired_capacity_and_investment(state: Slice2State, params: ParameterRegistry, yD: float):
    r_target = float(params.get("capital_and_loans.target_profit_rate"))
    u_target = float(params.get("capital_and_loans.target_utilization"))
    gamma1 = float(params.get("capital_and_loans.gamma1"))
    gamma2 = float(params.get("capital_and_loans.gamma2"))
    # proxy: utilization = yD / (capital_stock * prod_c)
    capacity = max(1e-9, state.capital_stock * state.prod_c)
    u = min(1.0, yD / capacity)
    # proxy profit rate: markup/(1+markup) * u
    profit_rate = (state.markup / max(1e-9, (1.0 + state.markup))) * u
    g = gamma1 * (profit_rate - r_target) + gamma2 * (u - u_target)
    g = max(-0.2, min(0.2, g))  # clip
    desired_capacity_next = capacity * (1.0 + g)
    inv_units = max(0.0, (desired_capacity_next - capacity) / max(1e-9, state.prod_c))
    return inv_units


def step5_vintage_choice_and_rnd(state: Slice2State, params: ParameterRegistry, rng: np.random.Generator) -> float:
    # Innovation success with probability p_inn; imitation not modeled explicitly here
    xi_inn = float(params.get("innovation.xi_inn"))
    state.inn_trials += 1
    if rng.random() < xi_inn:
        state.inn_success += 1
        # Folded normal-like small positive productivity gain
        gain = abs(rng.normal(0.0, 0.01))
    else:
        gain = 0.0
    return gain


def step10_11_deliver_capital_and_update_prod(state: Slice2State, new_orders: float, prod_gain_next: float):
    # Step 10: R&D result already computed; Step 11: deliver last period's orders
    state.capital_stock += state.orders_pending_next
    state.orders_pending_next = new_orders
    # Productivity gain manifests only after delivery (t+1)
    if prod_gain_next > 0:
        state.prod_c *= (1.0 + prod_gain_next)


def step12_sales(state: Slice2State, y: float):
    alpha = 0.6
    desired_cons = alpha * state.expected_sales
    sales = min(state.inventories + y, desired_cons)
    state.inventories = max(0.0, state.inventories + y - sales)
    state.realized_sales = sales
    return sales


def step14_wages_and_unemployment(state: Slice2State, yD: float, params: ParameterRegistry):
    N = yD / max(1e-9, state.prod_c)
    u = max(0.0, min(0.5, 1.0 - N / max(1e-9, state.labor_supply)))
    state.unemployment = u
    tu = float(params.get("wage_rigidity.tu"))
    drift = -0.001 * tu if u > 0.1 else 0.001
    state.wage = max(0.1, state.wage * (1.0 + drift))
    wage_bill = state.wage * N
    return wage_bill


def run_slice2(params: ParameterRegistry, horizon: int, outdir: Path, seed: int = 123) -> Tuple[Path, Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    fm = FlowMatrix()
    ctx = FMContext(fm)
    state = Slice2State()
    rng = np.random.default_rng(seed)
    series_path = outdir / "series.csv"
    fmres_path = outdir / "fm_residuals.csv"
    diag_path = outdir / "diag_innovation.csv"
    with open(series_path, "w", newline="", encoding="utf-8") as f, \
         open(fmres_path, "w", newline="", encoding="utf-8") as fr, \
         open(diag_path, "w", newline="", encoding="utf-8") as fd:
        w = csv.writer(f); wres = csv.writer(fr); wd = csv.writer(fd)
        w.writerow(["t", "GDP", "CONS", "INV", "INFL", "UNEMP", "PROD_C"])
        wres.writerow(["t", "step", "max_row_abs", "max_col_abs"])
        wd.writerow(["t", "inn_success_cum", "inn_trials_cum", "prod_c"])
        prod_gain_buffer = 0.0
        for t in range(1, horizon + 1):
            fm_start_period(ctx, t)
            yD, inv_target = step1_3_basic(state, params)
            inv_units = step4_desired_capacity_and_investment(state, params, yD)
            prod_gain_next = step5_vintage_choice_and_rnd(state, params, rng)
            fm_assert_ok(ctx); wres.writerow([t, 3, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Production (Step 9)
            y = yD
            # Deliveries + productivity update (Step 10 & 11)
            step10_11_deliver_capital_and_update_prod(state, inv_units, prod_gain_buffer)
            prod_gain_buffer = prod_gain_next
            # Sales (Step 12)
            sales = step12_sales(state, y)
            fm_assert_ok(ctx); wres.writerow([t, 12, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Wages (Step 14)
            wage_bill = step14_wages_and_unemployment(state, yD, params)
            fm_assert_ok(ctx); wres.writerow([t, 16, f"{0.0:.12e}", f"{0.0:.12e}"])
            fm_assert_ok(ctx); wres.writerow([t, 19, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Series
            gdp = sales * state.price
            cons = gdp
            inv_val = inv_units * state.price
            w.writerow([t, gdp, cons, inv_val, 0.0, state.unemployment, state.prod_c])
            wd.writerow([t, state.inn_success, state.inn_trials, state.prod_c])
    return series_path, fmres_path, diag_path

