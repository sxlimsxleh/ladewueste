-- One row per register record with R01 (German decimals -> numbers) and
-- R06 (whitespace / non-breaking spaces) applied. Every later model builds on this.
SELECT
    record_no,
    station_id,
    {{ clean_text('operator_raw') }}       AS operator_clean,
    {{ clean_text('display_name_raw') }}   AS display_name,
    status,
    register_type,
    try_cast(n_points_raw AS INTEGER)      AS n_points,
    {{ german_decimal('station_kw_raw') }} AS station_kw,
    try_strptime(commissioned_raw, '%d.%m.%Y')::DATE AS commissioned_on,
    {{ clean_text('street_raw') }}         AS street,
    {{ clean_text('house_no_raw') }}       AS house_no,
    {{ clean_text('address_extra_raw') }}  AS address_extra,
    {{ clean_text('postcode_raw') }}       AS postcode,
    {{ clean_text('town_raw') }}           AS town,
    {{ clean_text('district_raw') }}       AS district,
    {{ clean_text('state_raw') }}          AS state,
    {{ german_decimal('lat_raw') }}        AS lat_parsed,
    {{ german_decimal('lon_raw') }}        AS lon_parsed,
    least({{ decimals('lat_raw') }}, {{ decimals('lon_raw') }}) AS coord_decimals
FROM {{ ref('stg_records') }}
