-- R01: every non-empty raw number must parse. A failure means a new number format appeared.
SELECT s.record_no, s.lat_raw, s.lon_raw, s.station_kw_raw
FROM {{ ref('stg_records') }} AS s JOIN {{ ref('parsed_records') }} AS p USING (record_no)
WHERE (s.lat_raw IS NOT NULL AND p.lat_parsed IS NULL)
   OR (s.lon_raw IS NOT NULL AND p.lon_parsed IS NULL)
   OR (s.station_kw_raw IS NOT NULL AND p.station_kw IS NULL)
