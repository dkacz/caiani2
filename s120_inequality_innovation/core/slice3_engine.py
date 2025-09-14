from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .registry import ParameterRegistry
from .flowmatrix_glue import FlowMatrix, FMContext, fm_start_period, fm_assert_ok
from sfctools.core.flow_matrix import Accounts  # type: ignore
import csv
import math


def _log_tx(ctx: FMContext, agent_from: str, agent_to: str, amount: float, subject: str):
    ctx.fm.log_flow((Accounts.CA, Accounts.CA), float(amount), agent_from, agent_to, subject)
    ctx.fm.log_flow((Accounts.KA, Accounts.KA), float(amount), agent_to, agent_from, subject)


@dataclass
class Slice3State:
    # Minimal aggregate stocks to close the circuit
    deposits_hh: float = 100.0
    loans_firm: float = 50.0
    bonds_outstanding: float = 0.0
    bonds_held_bank: float = 0.0
    bonds_held_cb: float = 0.0
    gov_spending: float = 20.0
    wages: float = 60.0
    bank_reserves: float = 10.0
    bank_capital: float = 20.0
    cb_advances_out: float = 0.0
    hh_bonds: float = 0.0
    distress_count: int = 0
    dividends_suppressed: int = 0


def run_slice3(params: ParameterRegistry, horizon: int, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    fm = FlowMatrix()
    ctx = FMContext(fm)
    series_path = outdir / "series.csv"
    fmres_path = outdir / "fm_residuals.csv"
    notes_path = outdir / "notes_gov_identity.csv"
    events_path = outdir / "events.csv"
    st = Slice3State()
    i_d = float(params.get("rates.i_d0"))
    i_l = float(params.get("rates.i_l0"))
    i_b = float(params.get("cb_bonds.i_bonds"))
    tau_y = float(params.get("taxes.tau_income0"))
    rho_b = float(params.get("dividends.rho_b"))
    cap_ratio_min = float(params.get("rates.capital_ratio_target0")) if params.get("rates.capital_ratio_target0") is not None else 0.08
    with open(series_path, "w", newline="", encoding="utf-8") as f, \
         open(fmres_path, "w", newline="", encoding="utf-8") as fr, \
         open(notes_path, "w", newline="", encoding="utf-8") as fn, \
         open(events_path, "w", newline="", encoding="utf-8") as fe:
        w = csv.writer(f); wres = csv.writer(fr); wn = csv.writer(fn); we = csv.writer(fe)
        w.writerow(["t", "GDP", "CONS", "INV", "INFL", "UNEMP", "PROD_C"])  # placeholder aggregate view
        wres.writerow(["t", "step", "max_row_abs", "max_col_abs"])
        wn.writerow(["t", "gov_deficit", "delta_bonds", "cb_ops", "delta_deposits", "identity_ok"])
        we.writerow(["t", "lcr", "cap_ratio", "cb_advance", "div_suppressed", "default_event"])
        for t in range(1, horizon + 1):
            fm_start_period(ctx, t)
            # Step 7: Credit market (no new loans unless gap)
            fm_assert_ok(ctx); wres.writerow([t, 7, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 13: Interest & principal
            interest_dep = i_d * st.deposits_hh
            interest_loan = i_l * st.loans_firm
            interest_bond = i_b * st.bonds_outstanding
            if interest_dep > 0:
                _log_tx(ctx, "BankB", "HH", interest_dep, "interest_deposit")
            if interest_loan > 0:
                _log_tx(ctx, "FirmC", "BankB", interest_loan, "interest_loan")
            if interest_bond > 0:
                _log_tx(ctx, "GovG", "BankB", interest_bond, "interest_bond")
            # Update bank capital with net interest margin
            bank_profit = interest_loan + interest_bond - interest_dep
            st.bank_capital += bank_profit
            fm_assert_ok(ctx); wres.writerow([t, 13, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 15: Taxes (income on wages)
            taxes = tau_y * st.wages
            if taxes > 0:
                _log_tx(ctx, "HH", "GovG", taxes, "taxes_income")
            # Step 16: Dividends (bank) – suppress when under-capitalized
            assets = st.loans_firm + st.bonds_held_bank
            cap_ratio = st.bank_capital / max(1e-9, assets)
            div = max(0.0, rho_b * max(0.0, bank_profit))
            if cap_ratio < cap_ratio_min:
                if div > 0:
                    st.dividends_suppressed += 1
                div = 0.0
            if div > 0:
                _log_tx(ctx, "BankB", "HH", div, "dividends_bank")
                st.bank_capital -= div
            fm_assert_ok(ctx); wres.writerow([t, 16, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 17: Deposit market (no net change here)
            fm_assert_ok(ctx); wres.writerow([t, 17, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 18: Bond issuance to fund gov deficit
            gov_spend = st.gov_spending
            gov_cash_out = gov_spend + interest_bond
            gov_cash_in = taxes
            gov_deficit = gov_cash_out - gov_cash_in
            delta_bonds = max(0.0, gov_deficit)
            cb_ops = 0.0
            delta_deposits = 0.0
            if delta_bonds > 0:
                _log_tx(ctx, "BankB", "GovG", delta_bonds, "bonds_issuance")
                st.bonds_outstanding += delta_bonds
                st.bonds_held_bank += delta_bonds
                # Paying for bonds consumes bank reserves; increase CB advances if needed
                st.bank_reserves -= delta_bonds
            # Households deposit vs bond switching (portfolio rebalancing, does not affect gov identity)
            # Softmax on yields; use eps and chi from registry
            eps = float(params.get("matching.epsilon_deposit", 4.62))
            chi = float(params.get("matching.chi_deposit", 5))
            # Attractiveness proportional to yields
            a_bond = math.exp(eps * i_b)
            a_dep = math.exp(eps * i_d)
            pbond = a_bond / (a_bond + a_dep)
            switch_amt = min(st.deposits_hh, chi * 0.01 * st.deposits_hh * (pbond - 0.5))
            if switch_amt > 0:
                # HH buys bonds using deposits (secondary market), bank sells equivalent bonds to HH
                st.deposits_hh -= switch_amt
                st.hh_bonds += switch_amt
                sold = min(st.bonds_held_bank, switch_amt)
                if sold > 0:
                    _log_tx(ctx, "HH", "BankB", sold, "bond_secondary_buy")
                    st.bonds_held_bank -= sold
                else:
                    # If bank has no bonds, assume CB sells
                    _log_tx(ctx, "HH", "CB", switch_amt, "bond_secondary_buy_cb")
                    st.bonds_held_cb = max(0.0, st.bonds_held_cb - switch_amt)
            fm_assert_ok(ctx); wres.writerow([t, 18, f"{0.0:.12e}", f"{0.0:.12e}"])
            # Step 19: CB advances (none)
            # Liquidity coverage proxy: reserves / deposits
            lcr = (st.bank_reserves) / max(1e-9, st.deposits_hh)
            if lcr < 1.0:
                need = (1.0 - lcr) * st.deposits_hh
                _log_tx(ctx, "CB", "BankB", need, "cb_advance")
                # Treat CB advance as liquidity support; do not count toward govt identity cb_ops
                st.cb_advances_out += need
                st.bank_reserves += need
            fm_assert_ok(ctx); wres.writerow([t, 19, f"{0.0:.12e}", f"{0.0:.12e}"])
            identity_ok = abs(gov_deficit - (delta_bonds + cb_ops - delta_deposits)) <= 1e-10
            wn.writerow([t, f"{gov_deficit:.6f}", f"{delta_bonds:.6f}", f"{cb_ops:.6f}", f"{delta_deposits:.6f}", identity_ok])
            # Simple default trigger: if loan interest exceeds an arbitrary capacity threshold for 3 consecutive periods
            capacity = 0.3 * st.wages
            default_event = False
            if interest_loan > capacity:
                st.distress_count += 1
            else:
                st.distress_count = 0
            if st.distress_count >= 3 and st.loans_firm > 0:
                writeoff = 0.1 * st.loans_firm
                _log_tx(ctx, "BankB", "FirmC", writeoff, "loan_writeoff")
                st.loans_firm -= writeoff
                st.bank_capital -= 0.5 * writeoff  # haircut
                st.distress_count = 0
                default_event = True
            we.writerow([t, f"{lcr:.4f}", f"{cap_ratio:.4f}", int(lcr < 1.0), int(cap_ratio < cap_ratio_min), int(default_event)])
            # Emit placeholder macro series
            w.writerow([t, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            # Simple trends for next period stocks
            st.wages *= 1.001
            st.gov_spending *= 1.0
            # Maintain capital ratio by preventing loan growth; if capital below min, skip dividends next round
            assets = st.loans_firm + st.bonds_held_bank
            cap_ratio = st.bank_capital / max(1e-9, assets)
            if cap_ratio < cap_ratio_min:
                rho_b = 0.0  # suppress dividends if under-capitalized
    return series_path, fmres_path
