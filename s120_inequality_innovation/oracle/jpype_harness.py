from __future__ import annotations

"""
JPype-based harness to launch the Java JMAB oracle (InequalityInnovation).

Usage (outline):
  - Ensure OpenJDK 17 is installed and `java -version` works in WSL.
  - Clone https://github.com/S120/InequalityInnovation (and build if needed).
  - Identify the Spring XML config path, e.g., resources/InequalityInnovation.xml.
  - Use `run_java_oracle(config_xml, classpath)` to run and export CSVs.

This module provides a skeleton; implementation details (classpath detection,
CSV export hooks) are filled in next milestone once the oracle repo is present.
"""

from pathlib import Path
from typing import Optional, List

try:
    import jpype
    import jpype.imports  # noqa: F401
except Exception:  # pragma: no cover
    jpype = None  # type: ignore


def run_java_oracle(config_xml: Path, classpath: str, jvm_path: Optional[str] = None, seed: Optional[int] = None):
    if jpype is None:
        raise RuntimeError("JPype not available. Please install jpype1.")
    if not jpype.isJVMStarted():
        # Support colon/semicolon separated classpath AND lists
        if isinstance(classpath, str):
            if ";" in classpath:
                cp_list: List[str] = classpath.split(";")
            else:
                cp_list = classpath.split(":")
        else:
            cp_list = [str(classpath)]
        # JPype guidance recommends convertStrings=False to avoid implicit conversions
        jpype.startJVM(jvm_path, classpath=cp_list, convertStrings=False)
    # Set the system property for jabm config
    java_lang_System = jpype.JClass("java.lang.System")
    java_lang_System.setProperty("jabm.config", str(config_xml))
    # Try to seed JABM deterministically; set several common keys
    if seed is not None:
        try:
            java_lang_System.setProperty("jabm.seed", str(int(seed)))
            java_lang_System.setProperty("JABM_SEED", str(int(seed)))
            java_lang_System.setProperty("seed", str(int(seed)))
        except Exception:
            pass
    # Try DesktopSimulationManager first; if missing GUI deps, fall back to SimulationManager
    SimClass = None
    for name in [
        "jmab.desktop.DesktopSimulationManager",
        "jmab.simulation.DesktopSimulationManager",
        "net.sourceforge.jabm.DesktopSimulationManager",
        "net.sourceforge.jabm.SimulationManager",
    ]:
        try:
            SimClass = jpype.JClass(name)
            break
        except Exception:
            continue
    if SimClass is None:
        raise RuntimeError("Could not load a SimulationManager class from classpath")
    SimClass.main([])


def _build_cli():
    import argparse
    p = argparse.ArgumentParser(description="Run S120 Java oracle via JPype")
    p.add_argument("--classpath", required=False, help="Classpath (colon- or semicolon-separated)")
    p.add_argument("--xml", required=False, help="Path to JMAB Spring XML config")
    p.add_argument("--out", required=False, default="artifacts/golden_java/baseline/java_baseline_series.csv",
                   help="Output CSV path written by Java or to copy from Java output")
    p.add_argument("--jvm", required=False, help="Path to libjvm.so if needed")
    p.add_argument("--dry-run", action="store_true", help="Only print the resolved options, do not start JVM")
    return p


def main():
    parser = _build_cli()
    args = parser.parse_args()
    cp = args.classpath
    xml = args.xml
    if args.dry_run:
        print(f"JPype harness dry-run: classpath={cp}, xml={xml}, jvm={args.jvm}")
        return 0
    if not cp or not xml:
        parser.print_help()
        return 2
    run_java_oracle(Path(xml), cp, jvm_path=args.jvm)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
