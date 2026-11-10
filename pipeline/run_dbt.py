"""Run dbt with every tunable value taken from config.yaml (rule 4: config, not constants).

Usage: python -m pipeline.run_dbt [dbt command and args]   (default: build)

Runs dbt in-process (dbtRunner) from the repo root so dbt Python models can
`import pipeline.*`. The number of charging-point column groups comes from the
bronze load (it is detected from the file, not assumed).
"""

import json
import os
import sys

import duckdb
from dbt.cli.main import dbtRunner

from pipeline.config import DUCKDB_PATH, REPO_ROOT, load_config

DBT_DIR = REPO_ROOT / "pipeline" / "dbt"


def dbt_vars() -> dict:
    config = load_config()
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    layout = json.loads(con.execute("SELECT layout_json FROM bronze.load_info").fetchone()[0])
    con.close()
    cleaning, coverage = config["cleaning"], config["coverage"]
    return {
        "n_point_groups": layout["n_point_groups"],
        "hpc_threshold_kw": coverage["hpc_threshold_kw"],
        "max_plausible_point_kw": cleaning["max_plausible_point_kw"],
        "border_tolerance_km": cleaning["border_tolerance_km"],
        "placeholder_min_towns": cleaning["placeholder_min_towns"],
        "low_precision_decimals": cleaning["low_precision_decimals"],
        "operator_fuzzy_threshold": cleaning["operator_fuzzy_threshold"],
        "site_radius_m": cleaning["site_radius_m"],
        "desert_radius_km": coverage["desert_radius_km"],
        "hub_min_hpc_points": coverage["hub_min_hpc_points"],
        "h3_res_map": coverage["h3_resolutions"]["map"],
        "h3_res_detail": coverage["h3_resolutions"]["detail"],
    }


def run(args: list[str]) -> bool:
    os.environ["LADEWUESTE_DUCKDB"] = str(DUCKDB_PATH)
    command = [
        *args,
        "--project-dir", str(DBT_DIR),
        "--profiles-dir", str(DBT_DIR),
        "--vars", json.dumps(dbt_vars()),
    ]
    return dbtRunner().invoke(command).success


def main() -> None:
    if not run(sys.argv[1:] or ["build"]):
        sys.exit(1)


if __name__ == "__main__":
    main()
