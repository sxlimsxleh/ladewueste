"""Export the gold tables to data/gold/*.parquet. The API reads only these files."""

import duckdb

from pipeline.config import DUCKDB_PATH, GOLD_DIR

# gold table -> parquet file name
TABLES = {
    "hexes": "hexes",
    "points": "points",
    "usable_stations": "stations",
    "sites": "sites",
    "operators": "operators",
}


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DUCKDB_PATH))  # same mode as dbt: run_all keeps dbt's connection open in-process
    for table, name in TABLES.items():
        path = GOLD_DIR / f"{name}.parquet"
        con.execute(f"COPY gold.{table} TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
        rows = con.execute(f"SELECT count(*) FROM '{path}'").fetchone()[0]
        print(f"{path.name:<16} {rows:>8,} rows  {path.stat().st_size / 1e6:6.1f} MB")
    con.close()


if __name__ == "__main__":
    main()
