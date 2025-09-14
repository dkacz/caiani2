from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from sfctools import FlowMatrix  # type: ignore
from sfctools.core.flow_matrix import Accounts  # type: ignore
import numpy as np


@dataclass
class FMContext:
    fm: FlowMatrix
    period: int = -1
    # Track simple residuals (placeholder: zeros if not available)
    last_residuals: Tuple[float, float] | None = None


def fm_start_period(ctx: FMContext, t: int):
    ctx.period = t
    # The real FlowMatrix is global and period-agnostic; we reset per period.
    ctx.fm.reset()


def fm_log(ctx: FMContext, source: str, sink: str, amount: float, label: Optional[str] = None):
    kind = (Accounts.CA, Accounts.CA)
    subject = label or "flow"
    ctx.fm.log_flow(kind, float(amount), source, sink, subject)


def fm_assert_ok(ctx: FMContext):
    # Compute residual diagnostics then assert consistency (raises on failure)
    try:
        df = ctx.fm.to_dataframe(group=True)
        if df.empty:
            ctx.last_residuals = (0.0, 0.0)
        else:
            null_sym = "   .-   "
            df2 = df.replace(null_sym, 0.0).astype(float)
            om_max = int(np.ceil(np.log10(df2.to_numpy().max())))
            om_min = int(np.ceil(np.log10(abs(df2.to_numpy().min()))))
            order_magnitude = max(om_max, om_min)
            df2 = df2.round(-order_magnitude + 4)
            # Row totals are in column "Total", column totals in row "Total" after transpose
            max_row_abs = float(np.abs(np.array(df2["Total"]).astype(float)).max())
            df3 = df2.T
            max_col_abs = float(np.abs(np.array(df3["Total"]).astype(float)).max())
            ctx.last_residuals = (max_row_abs, max_col_abs)
    except Exception:
        # If anything happens during diagnostic, fallback
        ctx.last_residuals = (0.0, 0.0)
    # Finally, enforce consistency (raises RuntimeError if inconsistent)
    ctx.fm.check_consistency()
