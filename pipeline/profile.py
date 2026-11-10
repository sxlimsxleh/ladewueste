"""Profile the bronze table and write docs/mess_report.md with real counts.

This runs BEFORE any cleaning. Each check returns a Finding: what we looked for, how many
records it affects, and a few raw examples. Nothing here changes data.
"""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

import duckdb
import numpy as np
from sklearn.neighbors import BallTree

from pipeline.config import DOCS_DIR, DUCKDB_PATH, RAW_DIR, load_config
from pipeline.germany import distance_to_border_km, load_rings, points_in_germany
from pipeline.operators import legal_key, surface_key

EARTH_RADIUS_KM = 6371.0088
LAT = '"Breitengrad"'
LON = '"Längengrad"'


@dataclass
class Finding:
    rule_id: str
    title: str
    affected: int
    detail: str
    examples: list[str] = field(default_factory=list)
    table: list[tuple] = field(default_factory=list)  # optional (label, count) rows


def scalar(con: duckdb.DuckDBPyConnection, sql: str) -> int:
    return con.execute(sql).fetchone()[0]


def german_number(column: str) -> str:
    """SQL expression parsing a German decimal ('3,7') into DOUBLE. Profiling only."""
    return f"try_cast(replace(trim({column}), ',', '.') AS DOUBLE)"


# ---------------------------------------------------------------- file layout


def check_layout(con, layout: dict, raw_bytes: bytes) -> list[Finding]:
    n_records = scalar(con, "SELECT count(*) FROM bronze.raw_rows")
    physical_lines = raw_bytes.count(b"\n")
    crlf = raw_bytes.count(b"\r\n")
    point_cols = [c for c in layout["columns"] if re.search(r"\d$", c)]
    multiline_condition = " OR ".join(f"contains(\"{c}\", chr(10))" for c in layout["columns"])
    multiline = scalar(con, f"SELECT count(*) FROM bronze.raw_rows WHERE {multiline_condition}")
    multiline_cols = [
        c for c in layout["columns"]
        if scalar(con, f'SELECT count(*) FROM bronze.raw_rows WHERE contains("{c}", chr(10))') > 0
    ]
    return [
        Finding(
            "L01", "Encoding", 0,
            f"Strict UTF-8 decode succeeds (detected `{layout['encoding']}`); "
            f"file starts with a UTF-8 BOM: **{layout['has_bom']}**. "
            "The expected cp1252/Excel encoding is *not* what this release uses, "
            "so the loader detects it instead of assuming.",
        ),
        Finding(
            "L02", "Metadata lines above the header", layout["header_record_index"] - 1,
            f"The column names are on CSV record {layout['header_record_index'] + 1}. Above them: "
            f"{layout['header_record_index'] - 1} title/disclaimer/date lines and one group-label row "
            "('Allgemeine Informationen', '1. Ladepunkt', ...). Every metadata line is padded with delimiters.",
        ),
        Finding(
            "L03", "Delimiter", 0,
            f"Delimiter `{layout['delimiter']}`. Multi-valued cells (payment systems, plug lists) "
            "use `; ` *inside* quoted fields, so naive splitting on `;` breaks rows.",
        ),
        Finding(
            "L04", "Line breaks inside quoted fields", multiline,
            f"{physical_lines:,} physical lines but {n_records:,} data records. "
            f"{crlf:,} CRLF record terminators; the {physical_lines - crlf:,} bare LFs all sit inside "
            f"quoted fields, in columns: {', '.join(multiline_cols)}. Line counting gives wrong row counts.",
        ),
        Finding(
            "L05", "Wide charging-point columns", n_records,
            f"{layout['n_point_groups']} repeating groups of 4 columns "
            f"({len(point_cols)} columns): Steckertypen{{n}}, Nennleistung Stecker{{n}}, "
            "EVSE-ID{n}, Public Key{n}. Needs an unpivot to one row per charging point.",
        ),
    ]


# ---------------------------------------------------------------- numbers


def check_decimal_commas(con, n_groups: int) -> Finding:
    point_kw = " + ".join(
        f"count(*) FILTER (WHERE contains(\"Nennleistung Stecker{n}\", ','))" for n in range(1, n_groups + 1)
    )
    lat = scalar(con, "SELECT count(*) FROM bronze.raw_rows WHERE contains(\"Breitengrad\", ',')")
    lon = scalar(con, "SELECT count(*) FROM bronze.raw_rows WHERE contains(\"Längengrad\", ',')")
    station_kw = scalar(
        con, "SELECT count(*) FROM bronze.raw_rows WHERE contains(\"Nennleistung Ladeeinrichtung [kW]\", ',')"
    )
    points = scalar(con, f"SELECT {point_kw} FROM bronze.raw_rows")
    examples = [
        f"`{r[0]}` / `{r[1]}` / station kW `{r[2]}`"
        for r in con.execute(
            "SELECT \"Breitengrad\", \"Längengrad\", \"Nennleistung Ladeeinrichtung [kW]\" "
            "FROM bronze.raw_rows WHERE contains(\"Nennleistung Ladeeinrichtung [kW]\", ',') LIMIT 3"
        ).fetchall()
    ]
    return Finding(
        "N01", "German decimal commas", lat,
        "Numbers use `,` as decimal separator. Cells containing a comma: "
        f"latitude {lat:,}, longitude {lon:,}, station kW {station_kw:,}, "
        f"charging-point kW cells {points:,}. A plain CAST fails or (worse) mis-parses.",
        examples,
    )


def check_power(con, n_groups: int, max_kw: float) -> list[Finding]:
    station = german_number('"Nennleistung Ladeeinrichtung [kW]"')
    unnest_points = " UNION ALL ".join(
        f"SELECT \"Ladeeinrichtungs-ID\" AS id, unnest(string_split(\"Nennleistung Stecker{n}\", ';')) AS kw "
        f"FROM bronze.raw_rows WHERE \"Nennleistung Stecker{n}\" IS NOT NULL"
        for n in range(1, n_groups + 1)
    )
    con.execute(f"CREATE OR REPLACE TEMP VIEW plug_kw AS SELECT id, {german_number('kw')} AS kw, kw AS raw FROM ({unnest_points})")
    station_zero = scalar(con, f"SELECT count(*) FROM bronze.raw_rows WHERE {station} = 0")
    station_high = scalar(con, f"SELECT count(*) FROM bronze.raw_rows WHERE {station} > {max_kw}")
    station_unparsable = scalar(con, f"SELECT count(*) FROM bronze.raw_rows WHERE {station} IS NULL")
    plug_zero = scalar(con, "SELECT count(*) FROM plug_kw WHERE kw = 0")
    plug_high = scalar(con, f"SELECT count(*) FROM plug_kw WHERE kw > {max_kw}")
    plug_unparsable = scalar(con, "SELECT count(*) FROM plug_kw WHERE kw IS NULL")
    stats = con.execute(f"SELECT min({station}), median({station}), max({station}) FROM bronze.raw_rows").fetchone()
    top = con.execute(
        f"SELECT \"Ladeeinrichtungs-ID\", \"Betreiber\", \"Nennleistung Ladeeinrichtung [kW]\" FROM bronze.raw_rows "
        f"ORDER BY {station} DESC LIMIT 3"
    ).fetchall()
    # Station power should be at least the most powerful plug on it.
    below_max_plug = scalar(
        con,
        f"SELECT count(*) FROM bronze.raw_rows r JOIN (SELECT id, max(kw) AS m FROM plug_kw GROUP BY id) p "
        f"ON r.\"Ladeeinrichtungs-ID\" = p.id WHERE {station} < p.m",
    )
    return [
        Finding(
            "P01", f"Implausible power (0 kW or > {max_kw:g} kW)",
            station_zero + station_high + plug_zero + plug_high,
            f"Station kW: {station_zero} zero, {station_high} above {max_kw:g}, {station_unparsable} unparsable "
            f"(min {stats[0]:g}, median {stats[1]:g}, max {stats[2]:g}). "
            f"Plug kW values: {plug_zero} zero, {plug_high} above {max_kw:g}, {plug_unparsable} unparsable. "
            "The configured max is a deliberate upper bound for megawatt (MCS) truck charging.",
            [f"ID {r[0]} ({r[1]}): `{r[2]}` kW" for r in top],
        ),
        Finding(
            "P02", "Station power below its strongest plug", below_max_plug,
            "Records whose 'Nennleistung Ladeeinrichtung' is smaller than the largest plug power "
            "listed on the same record: an internal contradiction to flag, not to fix.",
        ),
    ]


# ---------------------------------------------------------------- plugs


def check_plugs(con, n_groups: int) -> list[Finding]:
    lists = []
    mismatch = 0
    tokens: Counter[str] = Counter()
    for n in range(1, n_groups + 1):
        plugs, kws = f'"Steckertypen{n}"', f'"Nennleistung Stecker{n}"'
        lists.append(scalar(con, f"SELECT count(*) FROM bronze.raw_rows WHERE contains({plugs}, ';')"))
        mismatch += scalar(
            con,
            f"SELECT count(*) FROM bronze.raw_rows WHERE {plugs} IS NOT NULL "
            f"AND len(string_split({plugs}, ';')) <> len(string_split({kws}, ';'))",
        )
        for token, count in con.execute(
            f"SELECT trim(t), count(*) FROM (SELECT unnest(string_split({plugs}, ';')) AS t FROM bronze.raw_rows) GROUP BY 1"
        ).fetchall():
            tokens[token] += count
    mismatch_examples = [
        f"`{r[0]}` with kW `{r[1]}`"
        for r in con.execute(
            "SELECT \"Steckertypen1\", \"Nennleistung Stecker1\" FROM bronze.raw_rows "
            "WHERE len(string_split(\"Steckertypen1\", ';')) <> len(string_split(\"Nennleistung Stecker1\", ';')) LIMIT 3"
        ).fetchall()
    ]
    list_examples = [
        f"`{r[0]}` with kW `{r[1]}`"
        for r in con.execute(
            "SELECT \"Steckertypen1\", \"Nennleistung Stecker1\" FROM bronze.raw_rows "
            "WHERE contains(\"Nennleistung Stecker1\", ';') LIMIT 3"
        ).fetchall()
    ]
    return [
        Finding(
            "S01", "Plug types as `;`-separated lists", sum(lists),
            "One charging point can offer several plugs, listed in one cell with `; `, and its power cell "
            "then lists one kW value per plug. Point cells containing a list, per group: "
            + ", ".join(f"#{i + 1}: {c:,}" for i, c in enumerate(lists)),
            list_examples,
        ),
        Finding(
            "S02", "Plug list and kW list of different length", mismatch,
            "Point cells where the number of plugs differs from the number of kW values, so plug and power "
            "cannot be paired one-to-one. Power per point must then be taken as the max of the kW list.",
            mismatch_examples,
        ),
        Finding(
            "S03", "Plug type vocabulary", len(tokens),
            f"{len(tokens)} distinct raw plug labels (German, with AC/DC prefix and socket-vs-cable variants). "
            "These map onto a small normalised vocabulary (Type 2, CCS, CHAdeMO, Schuko, Type 1, MCS).",
            table=tokens.most_common(),
        ),
    ]


# ---------------------------------------------------------------- operators


def check_operators(con) -> list[Finding]:
    operators = con.execute('SELECT "Betreiber", count(*) FROM bronze.raw_rows GROUP BY 1').fetchall()
    null_ops = sum(n for name, n in operators if name is None)
    names = [(name, n) for name, n in operators if name is not None]
    whitespace = [(name, n) for name, n in names if name != name.strip() or "  " in name or "\xa0" in name]

    def collapse(key_fn) -> dict[str, list[tuple[str, int]]]:
        groups: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
        for name, n in names:
            groups[key_fn(name)].append((name, n))
        return {k: v for k, v in groups.items() if len(v) > 1}

    surface = collapse(surface_key)
    legal = collapse(legal_key)
    # Groups that only merge because of the legal form: their members still differ after surface_key.
    legal_only = {k: v for k, v in legal.items() if len({surface_key(name) for name, _ in v}) > 1}

    def show(groups: dict, k: int) -> list[str]:
        ranked = sorted(groups.values(), key=lambda v: (-sum(n for _, n in v), min(name for name, _ in v)))[:k]
        return [" ⟷ ".join(f"`{name}` ({n})" for name, n in sorted(group, key=lambda x: (-x[1], x[0]))) for group in ranked]

    return [
        Finding(
            "O01", "Operator names with stray whitespace", sum(n for _, n in whitespace),
            f"{len(whitespace)} distinct operator spellings with leading/trailing spaces, double spaces or "
            f"non-breaking spaces (U+00A0). Missing operator: {null_ops} records.",
            [repr(name) for name, _ in sorted(whitespace, key=lambda x: -x[1])[:3]],
        ),
        Finding(
            "O02", "Operator variants: case / whitespace / punctuation", sum(n for v in surface.values() for _, n in v),
            f"{len(names):,} distinct raw operator strings. {len(surface)} groups of spellings become identical "
            "after ignoring case, whitespace, `.`/`,`/apostrophes, hyphen vs space, `&` spacing and ß vs ss "
            "(pipeline/operators.py surface_key). Safe to merge.",
            show(surface, 5),
        ),
        Finding(
            "O03", "Operator variants: differ only by legal form", sum(n for v in legal_only.values() for _, n in v),
            f"{len(legal_only)} further groups become identical when a trailing legal form "
            "(GmbH, AG, GmbH & Co. KG, SE, e.K., B.V., ...) is removed. NOT safe to auto-merge: "
            "'Autohaus Schneider GmbH' and 'Autohaus Schneider e.K.' may be different companies. "
            "Goes to the review table, combined with rapidfuzz clustering.",
            show(legal_only, 5),
        ),
    ]


# ---------------------------------------------------------------- coordinates


def check_coordinates(con, cfg: dict) -> list[Finding]:
    rows = con.execute(
        f'SELECT "Ladeeinrichtungs-ID", "Betreiber", "Ort", {LAT}, {LON}, '
        f"{german_number(LAT)}, {german_number(LON)} FROM bronze.raw_rows"
    ).fetchall()
    ids = [r[0] for r in rows]
    ops = [r[1] for r in rows]
    towns = [r[2] for r in rows]
    raw_lat = [r[3] for r in rows]
    raw_lon = [r[4] for r in rows]
    lat = np.array([r[5] if r[5] is not None else np.nan for r in rows])
    lon = np.array([r[6] if r[6] is not None else np.nan for r in rows])

    missing = int(np.sum(np.isnan(lat) | np.isnan(lon)))
    zero = int(np.sum((lat == 0) | (lon == 0)))
    inside = points_in_germany(lat, lon)
    outside = np.where(~inside & ~np.isnan(lat) & ~np.isnan(lon))[0]
    swap_inside = points_in_germany(lon[outside], lat[outside])

    rings = load_rings()
    border_km = np.array([distance_to_border_km(lat[i], lon[i], rings) for i in outside])
    tolerance = cfg["border_tolerance_km"]
    near = outside[border_km <= tolerance]
    far = outside[border_km > tolerance]

    def decimals(value: str) -> int:
        return len(value.split(",")[1]) if "," in value else 0

    max_dec = cfg["low_precision_decimals"]
    low_precision = [i for i in range(len(rows)) if min(decimals(raw_lat[i]), decimals(raw_lon[i])) <= max_dec]
    integer_coords = [i for i in low_precision if min(decimals(raw_lat[i]), decimals(raw_lon[i])) == 0]

    placeholders = con.execute(
        f'SELECT "Breitengrad", "Längengrad", count(DISTINCT "Ort") AS towns, count(*) AS n, '
        f'count(DISTINCT "Betreiber") AS ops, any_value("Betreiber") FROM bronze.raw_rows '
        f'GROUP BY 1, 2 HAVING towns >= {cfg["placeholder_min_towns"]} ORDER BY n DESC'
    ).fetchall()

    def example(i: int) -> str:
        return f"ID {ids[i]} {ops[i]}, {towns[i]}: `{raw_lat[i]}`, `{raw_lon[i]}`"

    placeholder_coords = {(p[0], p[1]) for p in placeholders}
    far_placeholder = [i for i in far if (raw_lat[i], raw_lon[i]) in placeholder_coords]
    far_other = [i for i in far if (raw_lat[i], raw_lon[i]) not in placeholder_coords]

    return [
        Finding(
            "C01", "Missing or zero coordinates", missing + zero,
            f"{missing} records with an empty/unparsable coordinate, {zero} with 0.",
        ),
        Finding(
            "C02", "Coordinates outside Germany", len(outside),
            f"{len(outside)} records fall outside the Natural Earth 1:10m boundary. "
            f"{len(near)} are within {tolerance:g} km of the border, which matches the polygon's generalisation "
            f"(e.g. along the Rhine) and should be accepted with a tolerance. "
            f"{len(far)} are more than {tolerance:g} km outside: genuinely wrong. Of those, "
            f"{len(far_placeholder)} are the placeholder coordinate in C04; the other {len(far_other)} are "
            "individual errors (typos, truncated or foreign coordinates).",
            [example(i) for i in far_other[:3]],
        ),
        Finding(
            "C03", "Swapped latitude/longitude", int(swap_inside.sum()),
            f"Of the {len(outside)} outside points, {int(swap_inside.sum())} land inside Germany after swapping "
            "lat and lon. The rule is kept (cheap, safe) but this release has no swapped pairs.",
        ),
        Finding(
            "C04", "Placeholder coordinates shared across towns", sum(p[3] for p in placeholders),
            f"Coordinates used by stations in ≥ {cfg['placeholder_min_towns']} different towns. "
            "A charger cannot be in several towns at once, so these are placeholders, not locations. "
            "Must be flagged and excluded from the coverage model.",
            [f"`{p[0]}`, `{p[1]}`: {p[3]} records in {p[2]} towns, {p[4]} operator(s), e.g. {p[5]}" for p in placeholders],
        ),
        Finding(
            "C05", f"Low-precision coordinates (≤ {max_dec} decimals)", len(low_precision),
            f"{len(low_precision)} records have latitude or longitude with ≤ {max_dec} decimals "
            f"(≈1 km or worse); {len(integer_coords)} are whole degrees (≈100 km). Flag; whole degrees are unusable.",
            [example(i) for i in integer_coords[:3]],
        ),
    ]


# ---------------------------------------------------------------- duplicates


def check_duplicates(con, cfg: dict, n_groups: int) -> list[Finding]:
    id_dupes = scalar(
        con, 'SELECT count(*) - count(DISTINCT "Ladeeinrichtungs-ID") FROM bronze.raw_rows'
    )
    # EVSE-ID cells separate several IDs with ';', tabs or line breaks; EVSE-IDs never contain whitespace.
    evse_cells = " UNION ALL ".join(
        f'SELECT "Ladeeinrichtungs-ID" AS id, "EVSE-ID{n}" AS cell FROM bronze.raw_rows '
        f'WHERE "EVSE-ID{n}" IS NOT NULL'
        for n in range(1, n_groups + 1)
    )
    # ISO 15118 / eMI3 EVSE-ID: country (2) + operator (3) + 'E' + up to 31 chars, '*' separators optional.
    evse_pattern = r"^[A-Z]{2}\*?[A-Z0-9]{3}\*?E[A-Z0-9*]{1,31}$"
    con.execute(
        "CREATE OR REPLACE TEMP VIEW evse AS SELECT * FROM ("
        f"SELECT id, cell, upper(unnest(regexp_split_to_array(cell, '[;\\s]+'))) AS evse FROM ({evse_cells})"
        ") WHERE evse <> ''"
    )
    # Only well-formed IDs count as a duplicate signal; junk tokens like '&' would match across operators.
    shared_valid = (
        f"SELECT evse, list(DISTINCT id ORDER BY id) AS ids FROM evse WHERE regexp_full_match(evse, '{evse_pattern}') "
        "GROUP BY evse HAVING count(DISTINCT id) > 1"
    )
    evse_shared = con.execute(f"SELECT count(*), sum(len(ids)) FROM ({shared_valid})").fetchone()
    records_sharing = scalar(con, f"SELECT count(DISTINCT id) FROM (SELECT unnest(ids) AS id FROM ({shared_valid}))")
    evse_examples = [
        f"EVSE `{r[0]}` on records {r[1]}"
        for r in con.execute(f"SELECT * FROM ({shared_valid}) ORDER BY evse LIMIT 3").fetchall()
    ]
    invalid_evse = con.execute(
        f"SELECT count(DISTINCT id), count(DISTINCT cell) FROM evse WHERE NOT regexp_full_match(evse, '{evse_pattern}')"
    ).fetchone()
    invalid_examples = [
        f"`{r[0]!r}`"
        for r in con.execute(
            f"SELECT DISTINCT cell FROM evse WHERE NOT regexp_full_match(evse, '{evse_pattern}') ORDER BY cell LIMIT 3"
        ).fetchall()
    ]
    multi_id_cells = scalar(con, "SELECT count(*) FROM (SELECT id, cell FROM evse GROUP BY id, cell HAVING count(*) > 1)")
    non_id_columns = [c[0] for c in con.execute("DESCRIBE bronze.raw_rows").fetchall()
                      if c[0] not in ("record_no", "Ladeeinrichtungs-ID")]
    exact_with, exact_without = con.execute(
        "SELECT coalesce(sum(n - 1) FILTER (WHERE has_evse), 0), coalesce(sum(n - 1) FILTER (WHERE NOT has_evse), 0) "
        'FROM (SELECT count(*) AS n, any_value("EVSE-ID1" IS NOT NULL) AS has_evse FROM bronze.raw_rows GROUP BY '
        + ", ".join(f'"{c}"' for c in non_id_columns)
        + " HAVING n > 1)"
    ).fetchone()

    rows = con.execute(
        f'SELECT "Betreiber", {german_number(LAT)}, {german_number(LON)} FROM bronze.raw_rows'
    ).fetchall()
    by_operator: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    for op, la, lo in rows:
        if la is not None and lo is not None:
            by_operator[surface_key(op or "")].append((la, lo))
    radius = cfg["site_radius_m"] / 1000 / EARTH_RADIUS_KM
    colocated = 0
    for points in by_operator.values():
        if len(points) < 2:
            continue
        coords = np.radians(np.array(points))
        counts = BallTree(coords, metric="haversine").query_radius(coords, r=radius, count_only=True)
        colocated += int(np.sum(counts > 1))
    return [
        Finding("D01", "Duplicate record IDs", id_dupes, "Ladeeinrichtungs-ID is unique per record."),
        Finding(
            "D02", "Same EVSE-ID on several records", records_sharing,
            f"{evse_shared[0]:,} well-formed EVSE-IDs (the European charging-point identifier, which should be "
            f"unique) appear on more than one record; {records_sharing:,} records are involved. "
            "The strongest duplicate signal in the register.",
            evse_examples,
        ),
        Finding(
            "D03", "Exact duplicates except ID", int(exact_with + exact_without),
            "Extra records identical in every column apart from Ladeeinrichtungs-ID. "
            f"{int(exact_without):,} of them have no EVSE-ID: most likely identical devices at one site "
            "(e.g. 4 identical wallboxes in one car park), which the register cannot tell apart. "
            f"Only the {int(exact_with):,} that also repeat the same EVSE-IDs are real duplicate candidates.",
        ),
        Finding(
            "D05", "EVSE-ID cells that are not EVSE-IDs", int(invalid_evse[0]),
            f"{int(invalid_evse[1]):,} distinct EVSE-ID cells on {int(invalid_evse[0]):,} records contain a token "
            "that is not a valid ISO 15118 EVSE-ID (free text, truncated IDs, internal numbers). "
            f"{multi_id_cells:,} cells hold several IDs separated by ';', tabs or line breaks.",
            invalid_examples,
        ),
        Finding(
            "D04", f"Same operator within {cfg['site_radius_m']} m", colocated,
            f"Records that have another record of the same operator within {cfg['site_radius_m']} m. "
            "Mostly NOT duplicates: a site with 8 chargers is registered as 8 devices at one address. "
            "So this is a site-grouping signal; only records also sharing EVSE-IDs (D02) or all values (D03) "
            "are duplicate candidates.",
        ),
    ]


# ---------------------------------------------------------------- other columns


def check_other(con) -> list[Finding]:
    status = con.execute('SELECT "Status", count(*) FROM bronze.raw_rows GROUP BY 1 ORDER BY 2 DESC').fetchall()
    kind = con.execute('SELECT "Art der Ladeeinrichtung", count(*) FROM bronze.raw_rows GROUP BY 1 ORDER BY 2 DESC').fetchall()
    dates = con.execute(
        "SELECT count(*) FILTER (WHERE try_strptime(\"Inbetriebnahmedatum\", '%d.%m.%Y') IS NULL), "
        "min(try_strptime(\"Inbetriebnahmedatum\", '%d.%m.%Y'))::DATE, "
        "max(try_strptime(\"Inbetriebnahmedatum\", '%d.%m.%Y'))::DATE FROM bronze.raw_rows"
    ).fetchone()
    nbsp = scalar(
        con,
        "SELECT count(*) FROM bronze.raw_rows WHERE contains(\"Straße\", chr(160)) OR contains(\"Betreiber\", chr(160)) "
        "OR contains(\"Ort\", chr(160)) OR contains(\"Hausnummer\", chr(160))",
    )
    count_mismatch_sql = " + ".join(
        f'("Steckertypen{n}" IS NOT NULL)::INT' for n in range(1, 7)
    )
    count_mismatch = scalar(
        con, f'SELECT count(*) FROM bronze.raw_rows WHERE try_cast("Anzahl Ladepunkte" AS INT) <> {count_mismatch_sql}'
    )
    return [
        Finding("X01", "Status values", 0, "Only operational records are published.", table=status),
        Finding(
            "X02", "Charging type by register", 0,
            "The register's own normal/fast split (fast = DC, > 22 kW by the Ladesäulenverordnung), "
            "not our HPC ≥ 150 kW threshold.", table=kind,
        ),
        Finding(
            "X03", "Commissioning dates", dates[0],
            f"Format DD.MM.YYYY; {dates[0]} unparsable; range {dates[1]} – {dates[2]}.",
        ),
        Finding(
            "X04", "Non-breaking spaces in text fields", nbsp,
            "Records with U+00A0 in operator, street, house number or town. Invisible, but breaks equality and grouping.",
        ),
        Finding(
            "X05", "Point count vs filled point groups", count_mismatch,
            "'Anzahl Ladepunkte' disagrees with the number of filled Steckertypen{n} groups.",
        ),
    ]


# ---------------------------------------------------------------- render


def render(findings: list[Finding], load_info: dict, manifest: dict) -> str:
    layout = json.loads(load_info["layout_json"])
    lines = [
        "# Mess report: Ladesäulenregister",
        "",
        f"Generated {date.today().isoformat()} by `pipeline/profile.py` from the bronze table, before any cleaning.",
        "",
        f"- Source file: `{load_info['source_file']}` ({manifest.get('bytes', 0):,} bytes)",
        f"- SHA-256: `{load_info['source_sha256']}`",
        f"- URL: {manifest.get('url', 'n/a')}",
        f"- Licence: {manifest.get('licence', 'CC BY 4.0')}, data © {manifest.get('attribution', 'Bundesnetzagentur.de')}",
        (
            f"- Data records: **{load_info['data_records']:,}** charging devices (Ladeeinrichtungen), "
            f"{len(layout['columns'])} columns"
        ),
        "",
        "Counts are records (rows) unless stated otherwise.",
        "",
        "## Summary",
        "",
        "| ID | Problem | Affected |",
        "|---|---|---:|",
    ]
    lines += [f"| {f.rule_id} | {f.title} | {f.affected:,} |" for f in findings]
    lines.append("")
    for f in findings:
        lines += [f"## {f.rule_id} · {f.title}", "", f"**Affected: {f.affected:,}**", "", f.detail, ""]
        if f.examples:
            lines += ["Examples:", ""] + [f"- {e}" for e in f.examples] + [""]
        if f.table:
            lines += ["| Value | Count |", "|---|---:|"] + [f"| {v} | {n:,} |" for v, n in f.table] + [""]
    return "\n".join(lines)


def build_report() -> str:
    cfg = load_config()["cleaning"]
    con = duckdb.connect(str(DUCKDB_PATH))
    load_info = dict(zip(
        ["source_file", "source_sha256", "layout_json", "data_records"],
        con.execute("SELECT * FROM bronze.load_info").fetchone(),
    ))
    layout = json.loads(load_info["layout_json"])
    n_groups = layout["n_point_groups"]
    raw_bytes = (RAW_DIR / load_info["source_file"]).read_bytes()
    manifest_path = RAW_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}

    findings: list[Finding] = []
    findings += check_layout(con, layout, raw_bytes)
    findings.append(check_decimal_commas(con, n_groups))
    findings += check_plugs(con, n_groups)
    findings += check_power(con, n_groups, cfg["max_plausible_point_kw"])
    findings += check_operators(con)
    findings += check_coordinates(con, cfg)
    findings += check_duplicates(con, cfg, n_groups)
    findings += check_other(con)
    con.close()
    return render(findings, load_info, manifest)


def main() -> None:
    DOCS_DIR.mkdir(exist_ok=True)
    out = DOCS_DIR / "mess_report.md"
    out.write_text(build_report(), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
