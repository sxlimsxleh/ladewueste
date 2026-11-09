-- R03: every raw plug label is in seeds/plug_type_map.csv. Fails loudly when BNetzA adds a label.
SELECT record_no, point_no, plugs_raw FROM {{ ref('charging_points') }} WHERE n_unknown_labels > 0
