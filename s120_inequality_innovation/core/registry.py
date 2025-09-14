from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import yaml


@dataclass
class ParameterRegistry:
    data: Dict[str, Any]

    @classmethod
    def from_files(
        cls,
        default_yaml: str | Path = Path(__file__).resolve().parents[1]
        / "config" / "params_default.yaml",
        overrides: Dict[str, Any] | None = None,
    ) -> "ParameterRegistry":
        with open(default_yaml, "r", encoding="utf-8") as f:
            base = yaml.safe_load(f)
        if overrides:
            base = deep_merge(base, overrides)
        _validate_params(base)
        return cls(base)

    def get(self, dotted_key: str, default: Any | None = None) -> Any:
        node = self.data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def as_dict(self) -> Dict[str, Any]:
        return self.data

    def config_hash(self) -> str:
        """Stable hash of the parameters for artifact tagging."""
        payload = json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def _assert_between(name: str, val: float, lo: float, hi: float):
    if not (lo <= float(val) <= hi):
        raise ValueError(f"Parameter {name}={val} out of range [{lo},{hi}]")


def _validate_params(cfg: Dict[str, Any]):
    # Minimal type/range checks for this round.
    # Matching epsilons and chis
    for key in [
        "matching.chi_consumption",
        "matching.chi_capital",
        "matching.chi_labor",
        "matching.chi_credit",
        "matching.chi_deposit",
    ]:
        v = _dget(cfg, key)
        if not isinstance(v, (int, float)):
            raise TypeError(f"{key} must be numeric")
        _assert_between(key, v, 1, 100)

    for key in [
        "matching.epsilon_deposit",
        "matching.epsilon_credit",
        "matching.epsilon_consumption",
        "matching.epsilon_capital",
    ]:
        v = _dget(cfg, key)
        if not isinstance(v, (int, float)):
            raise TypeError(f"{key} must be numeric")
        _assert_between(key, v, 0.0, 100.0)

    # Inventories
    _assert_between("inventories.nu_target", _dget(cfg, "inventories.nu_target"), 0.0, 10.0)

    # Markups
    _assert_between("markups.mu_c0", _dget(cfg, "markups.mu_c0"), 0.0, 2.0)
    _assert_between("markups.mu_k0", _dget(cfg, "markups.mu_k0"), 0.0, 2.0)

    # Wage rigidity
    tu = _dget(cfg, "wage_rigidity.tu")
    if not isinstance(tu, (int, float)):
        raise TypeError("wage_rigidity.tu must be numeric")
    _assert_between("wage_rigidity.tu", tu, 0, 12)

    # Taxes progressive
    theta = _dget(cfg, "taxes.theta_progressive")
    _assert_between("taxes.theta_progressive", theta, 0.0, 2.0)

    # Rates sanity
    _assert_between("rates.i_l0", _dget(cfg, "rates.i_l0"), 0.0, 1.0)
    _assert_between("rates.i_d0", _dget(cfg, "rates.i_d0"), 0.0, 1.0)

    # CB bonds
    _assert_between("cb_bonds.i_a_cb", _dget(cfg, "cb_bonds.i_a_cb"), 0.0, 1.0)
    _assert_between("cb_bonds.i_bonds", _dget(cfg, "cb_bonds.i_bonds"), 0.0, 1.0)
    assert abs(float(_dget(cfg, "cb_bonds.p_bonds")) - 1.0) < 1e-9


def _dget(d: Dict[str, Any], dotted: str) -> Any:
    node: Any = d
    for p in dotted.split("."):
        if not isinstance(node, dict):
            raise KeyError(dotted)
        node = node[p]
    return node

