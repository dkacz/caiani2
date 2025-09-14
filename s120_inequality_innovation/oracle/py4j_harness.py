from __future__ import annotations

"""
Py4J-based harness placeholder. Optionally, a small Java wrapper exposing a
GatewayServer entry point can be used to start the simulation and write CSV.
Implementation deferred to the oracle milestone.
"""

from pathlib import Path

def run_via_py4j(config_xml: Path, classpath: str):
    raise NotImplementedError("Py4J harness deferred to next milestone.")

