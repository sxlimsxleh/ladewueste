-- Every usable station from silver reaches gold, in exactly one site.
SELECT s.station_id FROM {{ ref('stations') }} AS s
LEFT JOIN {{ ref('usable_stations') }} AS u USING (station_id)
WHERE s.usable_for_coverage AND u.site_id IS NULL
