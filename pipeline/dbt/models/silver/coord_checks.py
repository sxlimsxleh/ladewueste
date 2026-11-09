"""R09: coordinates inside Germany, swapped, near the border, or outside.
Thin dbt wrapper; the logic (and its unit tests) live in pipeline/germany.py."""

from pipeline.germany import classify_coordinates


def model(dbt, session):
    dbt.config(materialized="table")
    tolerance_km = float(dbt.config.get("border_tolerance_km"))
    df = dbt.ref("parsed_records").project("record_no, lat_parsed, lon_parsed").df()
    lat, lon, status, border_km = classify_coordinates(
        df["lat_parsed"].to_numpy(dtype=float, na_value=float("nan")),
        df["lon_parsed"].to_numpy(dtype=float, na_value=float("nan")),
        tolerance_km,
    )
    df["lat"], df["lon"], df["coord_status"], df["border_km"] = lat, lon, status, border_km
    return df[["record_no", "lat", "lon", "coord_status", "border_km"]]
