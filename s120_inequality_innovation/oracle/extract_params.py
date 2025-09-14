from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Tuple
import xml.etree.ElementTree as ET
import yaml


def _flatten_xml(elem: ET.Element, prefix: str = "") -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    tag = elem.tag.split("}")[-1]
    key_base = f"{prefix}/{tag}" if prefix else tag
    text = (elem.text or "").strip()
    if text:
        data[key_base] = text
    for k, v in elem.attrib.items():
        data[f"{key_base}@{k}"] = v
    for child in list(elem):
        data.update(_flatten_xml(child, key_base))
    return data


def extract_params(xml_path: Path) -> Dict[str, Any]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    return _flatten_xml(root)


def load_mapping(map_yaml: Path) -> Dict[str, str]:
    with open(map_yaml, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {str(k): str(v) for k, v in data.items()}


def mapping_report(extracted: Dict[str, Any], mapping: Dict[str, str]) -> Tuple[str, int, int]:
    lines = ["# Params Mapping Report", "", "XML Key | YAML Key | XML Value", "---|---|---"]
    mapped = 0
    for xk, yk in mapping.items():
        if xk in extracted:
            lines.append(f"{xk} | {yk} | {extracted[xk]}")
            mapped += 1
        else:
            lines.append(f"{xk} | {yk} | MISSING")
    unmapped = [k for k in extracted.keys() if k not in mapping]
    lines.append("")
    lines.append(f"Unmapped XML keys: {len(unmapped)}")
    for k in sorted(unmapped)[:50]:
        lines.append(f"- {k}")
    return "\n".join(lines), mapped, len(unmapped)


def main():
    import argparse
    p = argparse.ArgumentParser(description="Extract JMAB XML params to JSON; optional mapping report")
    p.add_argument("--xml", type=Path, required=True)
    p.add_argument("--out", type=Path, default=Path("artifacts/golden_java/params_extracted.json"))
    p.add_argument("--map", type=Path, help="YAML mapping file (XML key -> YAML dotted key)")
    p.add_argument("--report", action="store_true", help="Also generate mapping report markdown next to --out or in reports/")
    args = p.parse_args()
    data = extract_params(args.xml)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(f"Wrote {args.out}")
    if args.report and args.map:
        mapping = load_mapping(args.map)
        md, mapped, unmapped = mapping_report(data, mapping)
        report_path = Path("reports/params_mapping.md")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(md, encoding="utf-8")
        print(f"Report written to {report_path} (mapped={mapped}, unmapped={unmapped})")


if __name__ == "__main__":
    main()
