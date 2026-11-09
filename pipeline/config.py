"""Load config.yaml and expose the repo's standard paths."""

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
RAW_DIR = REPO_ROOT / "data" / "raw"
REF_DIR = REPO_ROOT / "data" / "ref"
DOCS_DIR = REPO_ROOT / "docs"
GOLD_DIR = REPO_ROOT / "data" / "gold"
QUALITY_REPORT_PATH = GOLD_DIR / "quality_report.json"
DBT_MANIFEST_PATH = REPO_ROOT / "pipeline" / "dbt" / "target" / "manifest.json"
DUCKDB_PATH = REPO_ROOT / "data" / "ladewueste.duckdb"
MANIFEST_PATH = RAW_DIR / "manifest.json"
GERMANY_GEOJSON = REF_DIR / "germany.geojson"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
