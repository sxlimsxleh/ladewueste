"""Write data/gold/quality_report.json and docs/operator_merge_review.csv from the silver layer.

quality_report.json is what the Data Doctor page shows: the funnel from raw records to
usable stations, and one entry per cleaning rule with counts and 3 before/after examples.
Rule titles and "why it matters" come from dbt's manifest (meta in models/silver/_silver.yml),
so each rule is described in exactly one place.
"""

import csv
import json
from datetime import UTC, datetime
from typing import Any

import duckdb

from pipeline.config import (
    DBT_MANIFEST_PATH,
    DOCS_DIR,
    DUCKDB_PATH,
    MANIFEST_PATH,
    QUALITY_REPORT_PATH,
    load_config,
)

N_EXAMPLES = 3


def rule_metadata() -> list[dict[str, str]]:
    """Rule models and their meta, sorted by rule id, from dbt's manifest.json."""
    manifest = json.loads(DBT_MANIFEST_PATH.read_text(encoding="utf-8"))
    rules = []
    for node in manifest["nodes"].values():
        meta = node.get("config", {}).get("meta") or node.get("meta") or {}
        if node["resource_type"] == "model" and "rule_id" in meta:
            rules.append({"rule_id": meta["rule_id"], "title": meta["title"], "why": meta["why"], "model": node["name"]})
    if not rules:
        raise RuntimeError(f"No rule models with meta.rule_id in {DBT_MANIFEST_PATH}; run dbt first.")
    return sorted(rules, key=lambda r: r["rule_id"])


def rule_entry(con: duckdb.DuckDBPyConnection, rule: dict[str, str]) -> dict[str, Any]:
    rule_id = rule["rule_id"]
    actions = dict(con.execute(
        "SELECT action, count(*) FROM silver.rule_findings WHERE rule_id = ? GROUP BY action ORDER BY action",
        [rule_id],
    ).fetchall())
    records = con.execute(
        "SELECT count(DISTINCT record_no) FROM silver.rule_findings WHERE rule_id = ?", [rule_id]
    ).fetchone()[0]
    # Three varied examples: first one row per distinct outcome ('after'), taking turns across
    # actions (flagged first) so a rule with flagged and accepted rows shows both. If a rule has
    # fewer than three outcomes, further rows of the same outcomes fill the remaining slots.
    examples = con.execute(
        """
        WITH ranked AS (
            SELECT *, row_number() OVER (PARTITION BY after ORDER BY record_no) AS nth_of_outcome
            FROM silver.rule_findings WHERE rule_id = ?
        )
        SELECT station_id, point_no, action, before, after FROM ranked
        ORDER BY nth_of_outcome,
                 row_number() OVER (PARTITION BY nth_of_outcome, action ORDER BY record_no),
                 action = 'flagged' DESC, action
        LIMIT ?
        """,
        [rule_id, N_EXAMPLES],
    ).fetchall()
    return {
        **rule,
        "rows_affected": records,
        "finding_rows": sum(actions.values()),
        "actions": actions,
        "examples": [
            {"station_id": s, "point_no": p, "action": a, "before": b, "after": af} for s, p, a, b, af in examples
        ],
    }


# Why a station is not usable for coverage, checked in this order; each station counts once,
# under the first reason that applies (the amba placeholder is also "outside Germany", but the
# placeholder is the more useful explanation).
EXCLUSION_REASONS = [
    ("placeholder", "Placeholder coordinate (R10)", "is_placeholder_coord"),
    ("outside", "Outside Germany or missing (R09)", "coord_status NOT IN ('inside', 'swapped', 'border_tolerance')"),
    ("whole_degree", "Whole-degree coordinates (R11)", "coord_decimals = 0"),
    ("duplicate", "Duplicate record (R13)", "duplicate_of IS NOT NULL"),
]


def excluded_by_reason(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    cases = " ".join(f"WHEN {condition} THEN '{rid}'" for rid, _, condition in EXCLUSION_REASONS)
    counts = dict(con.execute(
        f"SELECT CASE {cases} ELSE 'other' END AS reason, count(*) FROM silver.stations "
        "WHERE NOT usable_for_coverage GROUP BY 1"
    ).fetchall())
    if "other" in counts:
        raise RuntimeError(f"{counts['other']} unusable stations match no known exclusion reason")
    return [{"reason_id": rid, "label": label, "count": counts.get(rid, 0)} for rid, label, _ in EXCLUSION_REASONS]


def funnel(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    stations = con.execute(
        """
        SELECT count(*), count(*) FILTER (WHERE usable_for_coverage),
               count(*) FILTER (WHERE duplicate_of IS NOT NULL),
               count(DISTINCT operator), count(DISTINCT operator_as_registered)
        FROM silver.stations
        """
    ).fetchone()
    points = con.execute(
        """
        SELECT count(*), count(*) FILTER (WHERE s.usable_for_coverage),
               count(*) FILTER (WHERE s.usable_for_coverage AND c.is_hpc)
        FROM silver.charging_points AS c JOIN silver.stations AS s USING (station_id)
        """
    ).fetchone()
    return {
        "raw_records": con.execute("SELECT count(*) FROM bronze.raw_rows").fetchone()[0],
        "stations": stations[0],
        "stations_usable": stations[1],
        "stations_duplicate": stations[2],
        "operators_as_registered": stations[4],
        "operators_canonical": stations[3],
        "charging_points": points[0],
        "charging_points_usable": points[1],
        "hpc_points_usable": points[2],
        "excluded_by_reason": excluded_by_reason(con),
    }


MERGE_COLUMNS = ["kind", "from_name", "from_records", "to_name", "to_records", "reason", "score", "applied"]


def operator_merges(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Every automatic (R07) and suggested (R08) operator merge, for the CSV and the Data Doctor."""
    rows = con.execute(
        """
        WITH sizes AS (SELECT surface_canonical, sum(n_records) AS n FROM silver.operator_map GROUP BY 1)
        SELECT 'automatic' AS kind, operator_clean AS from_name, n_records AS from_records,
               surface_canonical AS to_name, NULL::BIGINT AS to_records, 'spelling' AS reason,
               NULL::INTEGER AS score, true AS applied
        FROM silver.operator_map WHERE operator_clean <> surface_canonical
        UNION ALL
        SELECT DISTINCT 'suggested', m.surface_canonical, f.n, m.suggested_target, t.n,
               m.suggestion_reason, round(m.suggestion_score)::INTEGER, m.approved
        FROM silver.operator_map AS m
        JOIN sizes AS f ON f.surface_canonical = m.surface_canonical
        JOIN sizes AS t ON t.surface_canonical = m.suggested_target
        WHERE m.suggested_target IS NOT NULL
        ORDER BY kind, reason DESC, score DESC, from_name
        """
    ).fetchall()
    return [dict(zip(MERGE_COLUMNS, row)) for row in rows]


def write_merge_review(merges: list[dict[str, Any]]) -> None:
    """docs/operator_merge_review.csv: the same merges as a reviewable, committed file."""
    path = DOCS_DIR / "operator_merge_review.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(MERGE_COLUMNS)
        for m in merges:
            kind = "automatic (R07)" if m["kind"] == "automatic" else "suggested (R08)"
            writer.writerow([kind, m["from_name"], m["from_records"], m["to_name"], m["to_records"],
                             m["reason"], m["score"], "yes" if m["applied"] else "no"])


def build_report() -> dict[str, Any]:
    config = load_config()
    source = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")) if MANIFEST_PATH.exists() else {}
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    report = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": {
            "file": source.get("file"),
            "sha256": source.get("sha256"),
            "licence": config["source"]["licence"],
            "attribution": config["source"]["attribution"],
        },
        "funnel": funnel(con),
        "rules": [rule_entry(con, rule) for rule in rule_metadata()],
        "operator_merges": operator_merges(con),
    }
    con.close()
    return report


def main() -> None:
    report = build_report()
    QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUALITY_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_merge_review(report["operator_merges"])
    print(f"Wrote {QUALITY_REPORT_PATH} ({len(report['rules'])} rules) and "
          f"{len(report['operator_merges'])} operator merges for review")


if __name__ == "__main__":
    main()
