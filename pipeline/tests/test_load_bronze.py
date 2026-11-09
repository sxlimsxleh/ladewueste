"""Layout sniffing on small synthetic files that mimic the register's quirks."""

from pathlib import Path

import duckdb
import pytest

from pipeline.load_bronze import LayoutChangedError, load, sniff_layout

BASE_COLUMNS = [
    "Ladeeinrichtungs-ID", "Betreiber", "Status", "Art der Ladeeinrichtung",
    "Anzahl Ladepunkte", "Nennleistung Ladeeinrichtung [kW]", "Breitengrad", "Längengrad",
]
POINT_COLUMNS = [
    f"{name}{n}" for n in (1, 2)
    for name in ("Steckertypen", "Nennleistung Stecker", "EVSE-ID", "Public Key")
]
HEADER = BASE_COLUMNS + POINT_COLUMNS


def register_text(delimiter: str = ";", metadata_lines: int = 3) -> str:
    pad = delimiter * (len(HEADER) - 1)
    lines = [f"Ladesäulenregister Bundesnetzagentur{pad}"] + [pad] * (metadata_lines - 1)
    lines.append(delimiter.join(HEADER))
    row1 = ["1001", "Stadtwerke Köln GmbH", "In Betrieb", "Schnellladeeinrichtung", "2", "300",
            "50,93", "6,95", "DC Fahrzeugkupplung Typ Combo 2 (CCS)", "150", "DE*ABC*E1", "",
            "DC Fahrzeugkupplung Typ Combo 2 (CCS)", "150", "DE*ABC*E2", ""]
    # Second record has a quoted multi-line Public Key and a quoted delimiter inside a plug list.
    row2 = ["1002", "Müller e.K.", "In Betrieb", "Normalladeeinrichtung", "1", "22",
            "48,1", "11,5", f'"AC Typ 2 Steckdose{delimiter} AC Schuko"', f'"22{delimiter} 3,7"',
            "", '"3059 3013\n0607 2a86"', "", "", "", ""]
    lines += [delimiter.join(row1), delimiter.join(row2)]
    return "\r\n".join(lines) + "\r\n"


def test_sniffs_utf8_bom_semicolon_and_header_offset() -> None:
    raw = ("﻿" + register_text()).encode("utf-8")
    layout = sniff_layout(raw)
    assert layout.encoding == "utf-8-sig"
    assert layout.has_bom is True
    assert layout.delimiter == ";"
    assert layout.header_record_index == 3
    assert layout.n_point_groups == 2


def test_falls_back_to_cp1252() -> None:
    raw = register_text().encode("cp1252")  # 'ä', 'ö', 'ü' become single non-UTF-8 bytes
    layout = sniff_layout(raw)
    assert layout.encoding == "cp1252"
    assert layout.has_bom is False


def test_detects_comma_delimiter() -> None:
    layout = sniff_layout(register_text(delimiter=",").encode("utf-8"))
    assert layout.delimiter == ","


def test_missing_required_column_fails_loudly() -> None:
    text = register_text().replace("Breitengrad", "Latitude")
    with pytest.raises(LayoutChangedError, match="No header row"):
        sniff_layout(text.encode("utf-8"))


def test_broken_point_group_fails_loudly() -> None:
    text = register_text().replace("EVSE-ID2", "EVSE2")
    with pytest.raises(LayoutChangedError, match="group 2"):
        sniff_layout(text.encode("utf-8"))


@pytest.mark.parametrize("encoding", ["utf-8-sig", "cp1252"])
def test_load_keeps_multiline_fields_and_quoted_delimiters(tmp_path: Path, encoding: str) -> None:
    raw_path = tmp_path / "Ladesaeulenregister_test.csv"
    raw_path.write_bytes(register_text().encode(encoding))
    db_path = tmp_path / "test.duckdb"
    load(raw_path, db_path)

    con = duckdb.connect(str(db_path))
    rows = con.execute(
        'SELECT record_no, "Ladeeinrichtungs-ID", "Betreiber", "Steckertypen1", "Public Key1" '
        "FROM bronze.raw_rows ORDER BY record_no"
    ).fetchall()
    assert rows == [
        (1, "1001", "Stadtwerke Köln GmbH", "DC Fahrzeugkupplung Typ Combo 2 (CCS)", None),
        (2, "1002", "Müller e.K.", "AC Typ 2 Steckdose; AC Schuko", "3059 3013\n0607 2a86"),
    ]
    # Every value stays text in bronze: no silent typing of '50,93' into a number.
    lat_type = con.execute(
        "SELECT data_type FROM information_schema.columns "
        "WHERE table_name = 'raw_rows' AND column_name = 'Breitengrad'"
    ).fetchone()[0]
    assert lat_type == "VARCHAR"
