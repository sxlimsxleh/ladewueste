-- R05: a station with an implausible power value always carries the R05 flag.
SELECT s.station_id, s.station_kw, s.max_point_kw, s.flags
FROM {{ ref('stations') }} AS s
WHERE (s.station_kw = 0 OR s.station_kw > {{ var('max_plausible_point_kw') }}
       OR s.max_point_kw = 0 OR s.max_point_kw > {{ var('max_plausible_point_kw') }}
       OR s.station_kw < s.max_point_kw)
  AND NOT list_contains(s.flags, 'R05')
