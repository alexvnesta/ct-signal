from __future__ import annotations

import json

from . import config, questions
from .sources import datacommons


def main() -> None:
    catalog = questions.load_catalog()
    report = {}
    for indicator in catalog.get("stackup", []):
        variables = [indicator["dcid"]]
        if indicator.get("denominator"):
            variables.append(indicator["denominator"])
        try:
            payload = datacommons.observations(variables)
            covered = datacommons._latest_by_entity(payload, indicator["dcid"])
            status = "ok" if len(covered) >= 40 else f"thin:{len(covered)}"
            ct = covered.get(datacommons.CT)
            report[indicator["id"]] = {
                "status": status,
                "states": len(covered),
                "ct": ct,
            }
        except Exception as exc:
            report[indicator["id"]] = {"status": f"error:{exc}"}
        line = report[indicator["id"]]
        print(f"{indicator['id']:22s} {line['status']}")
    out = config.OUTPUT_DIR.parent / "data" / "validation_report.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
