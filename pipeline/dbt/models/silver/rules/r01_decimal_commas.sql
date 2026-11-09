-- R01: German decimal commas in latitude, longitude and station power.
SELECT
    'R01' AS rule_id, s.record_no, s.station_id, NULL::INTEGER AS point_no, 'fixed' AS action,
    concat_ws(' | ', s.lat_raw, s.lon_raw, s.station_kw_raw || ' kW') AS before,
    concat_ws(' | ', p.lat_parsed::VARCHAR, p.lon_parsed::VARCHAR, p.station_kw::VARCHAR || ' kW') AS after
FROM {{ ref('stg_records') }} AS s
JOIN {{ ref('parsed_records') }} AS p USING (record_no)
WHERE contains(s.lat_raw, ',') OR contains(s.lon_raw, ',') OR contains(s.station_kw_raw, ',')
