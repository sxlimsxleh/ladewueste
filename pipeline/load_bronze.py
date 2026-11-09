"""Bronze layer: sniff the raw register's layout and load every row, as text, into DuckDB.

Nothing is assumed about the file. We detect, in this order:
1. encoding  - strict UTF-8 first (with or without BOM), else cp1252
2. delimiter + header row - the first record that contains all REQUIRED_COLUMNS
   under one of the candidate delimiters
3. charging-point groups - the repeating Steckertypen{n}/Nennleistung Stecker{n}/... columns

If any of this fails, we raise LayoutChangedError instead of guessing.
The bronze table keeps the original German column names and every value as VARCHAR;
typing and cleaning happen later in dbt (silver).
"""

import csv
import io
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb

from pipeline.config import DUCKDB_PATH, MANIFEST_PATH, RAW_DIR

REQUIRED_COLUMNS = [
    "Ladeeinrichtungs-ID",
    "Betreiber",
    "Status",
    "Art der Ladeeinrichtung",
    "Anzahl Ladepunkte",
    "Nennleistung Ladeeinrichtung [kW]",
    "Breitengrad",
    "Längengrad",
]
# Each charging point n has exactly these four columns, in this order.
POINT_COLUMN_TEMPLATES = ["Steckertypen{n}", "Nennleistung Stecker{n}", "EVSE-ID{n}", "Public Key{n}"]
CANDIDATE_DELIMITERS = [";", ",", "\t", "|"]
CANDIDATE_ENCODINGS = ["utf-8-sig", "cp1252"]  # utf-8-sig = UTF-8, BOM stripped if present
HEADER_SEARCH_RECORDS = 50


class LayoutChangedError(Exception):
    """The raw file no longer looks like the layout this pipeline was built for."""


@dataclass
class Layout:
    encoding: str
    has_bom: bool
    delimiter: str
    header_record_index: int  # 0-based CSV record index of the column-name row
    columns: list[str]
    n_point_groups: int


def detect_encoding(raw: bytes) -> tuple[str, bool]:
    has_bom = raw.startswith(b"\xef\xbb\xbf")
    for encoding in CANDIDATE_ENCODINGS:
        try:
            raw.decode(encoding)
            return encoding, has_bom
        except UnicodeDecodeError:
            continue
    raise LayoutChangedError(f"File decodes with none of {CANDIDATE_ENCODINGS}")


def first_records(text: str, delimiter: str, limit: int) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    records = []
    for record in reader:
        records.append(record)
        if len(records) >= limit:
            break
    return records


def detect_header(text: str) -> tuple[str, int, list[str]]:
    """Find (delimiter, header record index, column names) or fail loudly."""
    for delimiter in CANDIDATE_DELIMITERS:
        for index, record in enumerate(first_records(text, delimiter, HEADER_SEARCH_RECORDS)):
            cells = [cell.strip() for cell in record]
            if all(column in cells for column in REQUIRED_COLUMNS):
                return delimiter, index, cells
    raise LayoutChangedError(
        f"No header row with columns {REQUIRED_COLUMNS} in the first "
        f"{HEADER_SEARCH_RECORDS} records for delimiters {CANDIDATE_DELIMITERS!r}"
    )


def count_point_groups(columns: list[str]) -> int:
    """Count charging-point column groups and check they are complete and contiguous."""
    numbers = sorted({int(m.group(1)) for c in columns if (m := re.fullmatch(r"Steckertypen(\d+)", c))})
    if not numbers or numbers != list(range(1, len(numbers) + 1)):
        raise LayoutChangedError(f"Charging-point groups are not numbered 1..N: {numbers}")
    for n in numbers:
        expected = [template.format(n=n) for template in POINT_COLUMN_TEMPLATES]
        start = columns.index(expected[0])
        if columns[start : start + len(expected)] != expected:
            raise LayoutChangedError(f"Charging-point group {n} is not {expected}")
    return len(numbers)


def sniff_layout(raw: bytes) -> Layout:
    encoding, has_bom = detect_encoding(raw)
    text = raw.decode(encoding)
    delimiter, header_index, columns = detect_header(text)
    if len(set(columns)) != len(columns):
        raise LayoutChangedError("Header contains duplicate column names")
    return Layout(encoding, has_bom, delimiter, header_index, columns, count_point_groups(columns))


def parse_records(raw: bytes, layout: Layout) -> list[list[str]]:
    """All data records after the header, parsed with a real CSV parser
    (fields may contain quoted delimiters and line breaks)."""
    text = raw.decode(layout.encoding)
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=layout.delimiter)
    records = list(reader)[layout.header_record_index + 1 :]
    bad = [i for i, r in enumerate(records) if len(r) != len(layout.columns)]
    if bad:
        raise LayoutChangedError(
            f"{len(bad)} records do not have {len(layout.columns)} fields "
            f"(first at data record {bad[0] + 1})"
        )
    return records


def utf8_copy(raw_path: Path, raw: bytes, layout: Layout) -> Path:
    """DuckDB's CSV reader expects UTF-8. If the file is cp1252, write a transcoded copy
    next to it (data/raw/ is gitignored) and read that instead."""
    if layout.encoding == "utf-8-sig":
        return raw_path
    utf8_path = raw_path.with_suffix(".utf8.csv")
    utf8_path.write_text(raw.decode(layout.encoding), encoding="utf-8", newline="")
    return utf8_path


def load(raw_path: Path, db_path: Path = DUCKDB_PATH) -> Layout:
    raw = raw_path.read_bytes()
    layout = sniff_layout(raw)
    records = parse_records(raw, layout)  # Python's parse is the reference we cross-check against
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    # DuckDB reads the file with the parameters we sniffed - its own auto-detection is off.
    # `skip` counts physical lines, while header_record_index counts CSV records. They match as
    # long as the metadata above the header has no quoted line breaks; if that ever changes,
    # check_against_python_parse below fails loudly.
    column_types = {c: "VARCHAR" for c in layout.columns}
    con.execute(
        """
        CREATE OR REPLACE TABLE bronze.raw_rows AS
        SELECT row_number() OVER () AS record_no, *
        FROM read_csv(?, delim = ?, quote = '"', escape = '"', header = false,
                      skip = ?, columns = ?, auto_detect = false, strict_mode = true)
        """,
        [str(utf8_copy(raw_path, raw, layout)), layout.delimiter,
         layout.header_record_index + 1, column_types],
    )
    check_against_python_parse(con, records, layout)

    con.execute("DROP TABLE IF EXISTS bronze.load_info")
    con.execute(
        "CREATE TABLE bronze.load_info AS SELECT ? AS source_file, ? AS source_sha256, "
        "? AS layout_json, ? AS data_records",
        [raw_path.name, manifest.get("sha256"), json.dumps(asdict(layout)), len(records)],
    )
    con.close()
    return layout


def check_against_python_parse(
    con: duckdb.DuckDBPyConnection, records: list[list[str]], layout: Layout
) -> None:
    """Fail loudly if DuckDB and Python's csv module disagree on what the file contains."""
    n_duckdb = con.execute("SELECT count(*) FROM bronze.raw_rows").fetchone()[0]
    if n_duckdb != len(records):
        raise LayoutChangedError(f"DuckDB read {n_duckdb} records, Python csv read {len(records)}")
    id_index = layout.columns.index("Ladeeinrichtungs-ID")
    duckdb_ids = [r[0] for r in con.execute(
        'SELECT "Ladeeinrichtungs-ID" FROM bronze.raw_rows ORDER BY record_no').fetchall()]
    python_ids = [r[id_index] or None for r in records]  # DuckDB reads empty fields as NULL
    if duckdb_ids != python_ids:
        first = next(i for i, (a, b) in enumerate(zip(duckdb_ids, python_ids)) if a != b)
        raise LayoutChangedError(f"DuckDB and Python disagree at data record {first + 1}")


def find_raw_file() -> Path:
    files = sorted(RAW_DIR.glob("Ladesaeulenregister*.csv"))
    if not files:
        raise FileNotFoundError(f"No register CSV in {RAW_DIR}. Run `make download` first.")
    return files[-1]


def main() -> None:
    raw_path = find_raw_file()
    layout = load(raw_path)
    print(
        f"Loaded {raw_path.name}: encoding={layout.encoding} bom={layout.has_bom} "
        f"delimiter={layout.delimiter!r} header_record={layout.header_record_index} "
        f"columns={len(layout.columns)} point_groups={layout.n_point_groups}"
    )


if __name__ == "__main__":
    main()
