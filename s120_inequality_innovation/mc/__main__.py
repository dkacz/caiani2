from __future__ import annotations

import argparse
from pathlib import Path

from .runner import run_baseline_smoke


def main():
    p = argparse.ArgumentParser(description="MC runners for s120_inequality_innovation")
    p.add_argument("cmd", choices=["baseline"], help="What to run")
    p.add_argument("--out", default="artifacts/baseline", help="Artifacts root")
    a = p.parse_args()
    if a.cmd == "baseline":
        run_baseline_smoke(Path(a.out))


if __name__ == "__main__":
    raise SystemExit(main())

