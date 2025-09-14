from __future__ import annotations

from typing import Iterable, Tuple
import numpy as np
import pandas as pd


def gini(array: Iterable[float]) -> float:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return float("nan")
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    n = x.size
    if n == 0 or x.sum() == 0:
        return 0.0
    cumx = np.cumsum(x)
    g = (n + 1 - 2 * (cumx.sum() / cumx[-1])) / n
    return float(g)


def lorenz_curve(array: Iterable[float]) -> Tuple[np.ndarray, np.ndarray]:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return np.array([0.0]), np.array([0.0])
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    cumx = np.cumsum(x)
    cumx = np.insert(cumx, 0, 0.0)
    cumx = cumx / cumx[-1] if cumx[-1] != 0 else cumx
    p = np.linspace(0.0, 1.0, cumx.size)
    return p, cumx


def top_share(array: Iterable[float], top_fraction: float = 0.1) -> float:
    x = np.array(list(array), dtype=float)
    if x.size == 0:
        return float("nan")
    if np.any(x < 0):
        x = x - x.min()
    x = np.sort(x)
    n_top = max(1, int(np.ceil(top_fraction * x.size)))
    return float(np.sum(x[-n_top:]) / (np.sum(x) + 1e-12))


def compute_inequality_df(income: Iterable[float], wealth: Iterable[float]) -> pd.DataFrame:
    gi = gini(income)
    gw = gini(wealth)
    return pd.DataFrame({"Gini_income": [gi], "Gini_wealth": [gw]})

