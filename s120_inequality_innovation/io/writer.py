from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


@dataclass
class ArtifactWriter:
    base_dir: Path
    series_path: Path
    meta_path: Path
    timeline_path: Path

    @classmethod
    def create(cls, base_dir: Path, meta: Dict) -> "ArtifactWriter":
        ensure_dir(base_dir)
        series = base_dir / "series.csv"
        timeline = base_dir / "timeline.csv"
        meta_p = base_dir / "meta.json"
        with open(meta_p, "w", encoding="utf-8") as f:
            json.dump(meta, f, sort_keys=True, indent=2)
        with open(series, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t", "GDP", "CONS", "INV", "INFL", "UNEMP"])
        with open(timeline, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t", "step", "label", "ts"])
        return cls(base_dir, series, meta_p, timeline)

    def append_series(self, t: int, gdp: float, cons: float, inv: float, infl: float, unemp: float):
        with open(self.series_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([t, gdp, cons, inv, infl, unemp])

    def append_timeline_row(self, row: Iterable):
        with open(self.timeline_path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(list(row))


def summarize_runs(run_dirs: List[Path], out_csv: Path):
    import pandas as pd

    records = []
    for rd in run_dirs:
        s = pd.read_csv(rd / "series.csv")
        if not s.empty:
            last = s.iloc[-1]
            records.append({
                "run": rd.name,
                "GDP_end": last["GDP"],
                "CONS_end": last["CONS"],
                "INV_end": last["INV"],
                "INFL_end": last["INFL"],
                "UNEMP_end": last["UNEMP"],
            })
    df = pd.DataFrame.from_records(records)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

