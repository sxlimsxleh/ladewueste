"""Load config.yaml and expose the repo's standard paths.

Everything the pipeline reads and writes lives under DATA_DIR (data/ by default). Set
LADEWUESTE_DATA_DIR to point it elsewhere: CI runs the pipeline on a synthetic register in a
temporary folder, and Docker mounts the host's data/ at /data. The committed reference boundary
(data/ref/germany.geojson) always comes from the repository.
"""

import os
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config.yaml"
DATA_DIR = Path(os.environ.get("LADEWUESTE_DATA_DIR", REPO_ROOT / "data"))
RAW_DIR = DATA_DIR / "raw"
GOLD_DIR = DATA_DIR / "gold"
DUCKDB_PATH = DATA_DIR / "ladewueste.duckdb"
MANIFEST_PATH = RAW_DIR / "manifest.json"
QUALITY_REPORT_PATH = GOLD_DIR / "quality_report.json"
REF_DIR = REPO_ROOT / "data" / "ref"
GERMANY_GEOJSON = REF_DIR / "germany.geojson"
# Generated reports go to the committed docs/ only for the real data; a run on another data
# folder (CI fixture) writes them next to that data, so it can never overwrite the committed ones.
DOCS_DIR = REPO_ROOT / "docs" if "LADEWUESTE_DATA_DIR" not in os.environ else DATA_DIR / "docs"
DBT_MANIFEST_PATH = REPO_ROOT / "pipeline" / "dbt" / "target" / "manifest.json"


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)
