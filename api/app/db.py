"""Read-only access to the gold Parquet files through an in-memory DuckDB.

Each Parquet file becomes a view of the same name. Every request gets its own cursor
(cheap, thread-safe), because FastAPI runs sync endpoints in a thread pool.
"""

import json
from pathlib import Path
from typing import Any

import duckdb

from pipeline.config import GOLD_DIR

GOLD_FILES = ["hexes", "points", "stations", "sites", "operators"]
QUALITY_FILE = "quality_report.json"


class DataNotReady(Exception):
    """The gold files are missing: the pipeline has not been run yet."""


def gold_dir_from_env() -> Path:
    """data/gold by default; follows LADEWUESTE_DATA_DIR (see pipeline/config.py), e.g. inside Docker."""
    return GOLD_DIR


class GoldStore:
    def __init__(self, gold_dir: Path) -> None:
        missing = [f"{n}.parquet" for n in GOLD_FILES if not (gold_dir / f"{n}.parquet").exists()]
        if not (gold_dir / QUALITY_FILE).exists():
            missing.append(QUALITY_FILE)
        if missing:
            raise DataNotReady(f"Missing in {gold_dir}: {', '.join(missing)}. Run `make pipeline`.")
        self.gold_dir = gold_dir
        self.con = duckdb.connect(":memory:")
        for name in GOLD_FILES:
            path = str(gold_dir / f"{name}.parquet").replace("'", "''")
            self.con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")

    def rows(self, sql: str, params: list[Any] | None = None) -> list[dict[str, Any]]:
        """Run a query and return rows as dicts (column name -> value)."""
        cursor = self.con.cursor()
        try:
            result = cursor.execute(sql, params or [])
            columns = [c[0] for c in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]
        finally:
            cursor.close()

    def quality_report(self) -> dict[str, Any]:
        return json.loads((self.gold_dir / QUALITY_FILE).read_text(encoding="utf-8"))
