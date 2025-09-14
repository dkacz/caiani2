from pathlib import Path

from s120_inequality_innovation.core.registry import ParameterRegistry


def test_params_load_and_validate():
    reg = ParameterRegistry.from_files()
    d = reg.as_dict()
    # Spot-check required keys
    assert d["matching"]["epsilon_consumption"] > 0
    assert d["inventories"]["nu_target"] == 0.10
    assert d["wage_rigidity"]["tu"] in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}
    assert d["taxes"]["theta_progressive"] >= 0.0
    # config hash stable for same file
    assert len(reg.config_hash()) == 12

