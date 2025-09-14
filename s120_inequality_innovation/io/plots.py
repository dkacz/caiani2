from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_smoke(baseline_dir: Path = Path("artifacts") / "smoke"):
    # Read latest baseline summary if present, else generate from baseline artifacts
    series_files = list((Path("artifacts") / "baseline").glob("run_*/series.csv"))
    outdir = baseline_dir / "plots"
    outdir.mkdir(parents=True, exist_ok=True)
    if not series_files:
        return []
    # Use the first run for simple plots
    df = pd.read_csv(series_files[0])
    figs = []
    for col, fname in [
        ("GDP", "gdp.png"),
        ("CONS", "cons.png"),
        ("INV", "inv.png"),
        ("INFL", "infl.png"),
        ("UNEMP", "unemp.png"),
    ]:
        ax = df.plot(x="t", y=col, legend=False, title=col)
        ax.set_xlabel("t")
        ax.set_ylabel(col)
        fig = ax.get_figure()
        out = outdir / fname
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        figs.append(out)
    return figs


def plot_lorenz(inequality_csv: Path, outdir: Path = Path("artifacts") / "figures"):
    from .metrics import lorenz_curve
    outdir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(inequality_csv)
    # Expect columns income_i... or precomputed curves; here just plot Gini time series if present
    if "Gini_income" in df.columns:
        ax = df["Gini_income"].plot(title="Gini Income")
        fig = ax.get_figure(); fig.savefig(outdir / "gini_income.png", dpi=120, bbox_inches="tight"); plt.close(fig)
    if "Gini_wealth" in df.columns:
        ax = df["Gini_wealth"].plot(title="Gini Wealth")
        fig = ax.get_figure(); fig.savefig(outdir / "gini_wealth.png", dpi=120, bbox_inches="tight"); plt.close(fig)
    return [outdir / "gini_income.png", outdir / "gini_wealth.png"]

if __name__ == "__main__":
    plot_smoke()
