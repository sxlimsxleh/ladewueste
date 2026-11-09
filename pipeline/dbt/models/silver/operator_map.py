"""R07 + R08: one row per cleaned operator spelling -> canonical operator.
Thin dbt wrapper; the logic (and its unit tests) live in pipeline/operators.py."""

from pipeline.operators import build_operator_map


def model(dbt, session):
    dbt.config(materialized="table")
    threshold = float(dbt.config.get("operator_fuzzy_threshold"))
    counts = (
        dbt.ref("parsed_records")
        .aggregate("operator_clean, count(*) AS n_records", "operator_clean")
        .filter("operator_clean IS NOT NULL")
        .df()
    )
    overrides = dbt.ref("operator_overrides").df()
    return build_operator_map(counts, overrides, threshold)
