-- Staging: English column names, values still raw text. No cleaning happens here,
-- so every rule model can show the true "before" value.
SELECT
    record_no,
    "Ladeeinrichtungs-ID"                AS station_id,
    "Betreiber"                          AS operator_raw,
    "Anzeigename (Karte)"                AS display_name_raw,
    "Status"                             AS status,
    "Art der Ladeeinrichtung"            AS register_type,
    "Anzahl Ladepunkte"                  AS n_points_raw,
    "Nennleistung Ladeeinrichtung [kW]"  AS station_kw_raw,
    "Inbetriebnahmedatum"                AS commissioned_raw,
    "Straße"                             AS street_raw,
    "Hausnummer"                         AS house_no_raw,
    "Adresszusatz"                       AS address_extra_raw,
    "Postleitzahl"                       AS postcode_raw,
    "Ort"                                AS town_raw,
    "Kreis/kreisfreie Stadt"             AS district_raw,
    "Bundesland"                         AS state_raw,
    "Breitengrad"                        AS lat_raw,
    "Längengrad"                         AS lon_raw
    {%- for n in range(1, var('n_point_groups') + 1) %},
    "Steckertypen{{ n }}"           AS p{{ n }}_plugs_raw,
    "Nennleistung Stecker{{ n }}"   AS p{{ n }}_kw_raw,
    "EVSE-ID{{ n }}"                AS p{{ n }}_evse_raw
    {%- endfor %}
FROM {{ source('bronze', 'raw_rows') }}
