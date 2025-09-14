from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import numpy as np
import yaml


@dataclass
class RNGStreams:
    rng_model: np.random.Generator
    rng_match: np.random.Generator
    rng_fn1: np.random.Generator
    rng_fn2: np.random.Generator
    rng_fn3: np.random.Generator
    rng_rnd: np.random.Generator


def load_seeds(path: str | Path | None = None) -> Dict[str, int]:
    if path is None:
        path = Path(__file__).resolve().parents[1] / "config" / "seeds.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {k: int(v) for k, v in data["streams"].items()}


def build_streams(seeds: Dict[str, int]) -> RNGStreams:
    return RNGStreams(
        rng_model=np.random.default_rng(seeds["rng_model"]),
        rng_match=np.random.default_rng(seeds["rng_match"]),
        rng_fn1=np.random.default_rng(seeds["rng_fn1"]),
        rng_fn2=np.random.default_rng(seeds["rng_fn2"]),
        rng_fn3=np.random.default_rng(seeds["rng_fn3"]),
        rng_rnd=np.random.default_rng(seeds["rng_rnd"]),
    )

