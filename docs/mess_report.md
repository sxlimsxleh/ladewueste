# Mess report: Ladesäulenregister

Generated 2026-11-11 by `pipeline/profile.py` from the bronze table, before any cleaning.

- Source file: `Ladesaeulenregister_BNetzA_2026-09-01.csv` (55,559,083 bytes)
- SHA-256: `cdd8e38f1fa7e8512bd97caa8cf77e9f875436be1f8fe3fe1f2bd9789a504c5b`
- URL: https://data.bundesnetzagentur.de/Bundesnetzagentur/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Ladesaeulenregister_BNetzA_2026-09-01.csv
- Licence: CC BY 4.0, data © Bundesnetzagentur.de
- Data records: **116,443** charging devices (Ladeeinrichtungen), 47 columns

Counts are records (rows) unless stated otherwise.

## Summary

| ID | Problem | Affected |
|---|---|---:|
| L01 | Encoding | 0 |
| L02 | Metadata lines above the header | 9 |
| L03 | Delimiter | 0 |
| L04 | Line breaks inside quoted fields | 8,305 |
| L05 | Wide charging-point columns | 116,443 |
| N01 | German decimal commas | 116,431 |
| S01 | Plug types as `;`-separated lists | 10,490 |
| S02 | Plug list and kW list of different length | 110 |
| S03 | Plug type vocabulary | 10 |
| P01 | Implausible power (0 kW or > 1500 kW) | 1 |
| P02 | Station power below its strongest plug | 169 |
| O01 | Operator names with stray whitespace | 6,401 |
| O02 | Operator variants: case / whitespace / punctuation | 917 |
| O03 | Operator variants: differ only by legal form | 266 |
| C01 | Missing or zero coordinates | 0 |
| C02 | Coordinates outside Germany | 771 |
| C03 | Swapped latitude/longitude | 0 |
| C04 | Placeholder coordinates shared across towns | 196 |
| C05 | Low-precision coordinates (≤ 2 decimals) | 204 |
| D01 | Duplicate record IDs | 0 |
| D02 | Same EVSE-ID on several records | 1,046 |
| D03 | Exact duplicates except ID | 14,420 |
| D05 | EVSE-ID cells that are not EVSE-IDs | 3,748 |
| D04 | Same operator within 20 m | 70,415 |
| X01 | Status values | 0 |
| X02 | Charging type by register | 0 |
| X03 | Commissioning dates | 0 |
| X04 | Non-breaking spaces in text fields | 3,051 |
| X05 | Point count vs filled point groups | 0 |

## L01 · Encoding

**Affected: 0**

Strict UTF-8 decode succeeds (detected `utf-8-sig`); file starts with a UTF-8 BOM: **True**. The expected cp1252/Excel encoding is *not* what this release uses, so the loader detects it instead of assuming.

## L02 · Metadata lines above the header

**Affected: 9**

The column names are on CSV record 11. Above them: 9 title/disclaimer/date lines and one group-label row ('Allgemeine Informationen', '1. Ladepunkt', ...). Every metadata line is padded with delimiters.

## L03 · Delimiter

**Affected: 0**

Delimiter `;`. Multi-valued cells (payment systems, plug lists) use `; ` *inside* quoted fields, so naive splitting on `;` breaks rows.

## L04 · Line breaks inside quoted fields

**Affected: 8,305**

146,671 physical lines but 116,443 data records. 116,454 CRLF record terminators; the 30,217 bare LFs all sit inside quoted fields, in columns: Adresszusatz, EVSE-ID1, Public Key1, EVSE-ID2, Public Key2, EVSE-ID3, Public Key3, EVSE-ID4, Public Key4, EVSE-ID5, Public Key5, EVSE-ID6, Public Key6. Line counting gives wrong row counts.

## L05 · Wide charging-point columns

**Affected: 116,443**

6 repeating groups of 4 columns (24 columns): Steckertypen{n}, Nennleistung Stecker{n}, EVSE-ID{n}, Public Key{n}. Needs an unpivot to one row per charging point.

## N01 · German decimal commas

**Affected: 116,431**

Numbers use `,` as decimal separator. Cells containing a comma: latitude 116,431, longitude 116,435, station kW 2,980, charging-point kW cells 3,341. A plain CAST fails or (worse) mis-parses.

Examples:

- `48,304437` / `9,905832` / station kW `16,7`
- `48,675458` / `9,017369` / station kW `62,5`
- `48,561584` / `8,781898` / station kW `3,6`

## S01 · Plug types as `;`-separated lists

**Affected: 10,490**

One charging point can offer several plugs, listed in one cell with `; `, and its power cell then lists one kW value per plug. Point cells containing a list, per group: #1: 5,860, #2: 4,114, #3: 350, #4: 160, #5: 4, #6: 2

Examples:

- `AC Typ 2 Steckdose; AC Schuko` with kW `22; 22`
- `DC Fahrzeugkupplung Typ Combo 2 (CCS); DC CHAdeMO` with kW `150; 150`
- `DC Fahrzeugkupplung Typ Combo 2 (CCS); DC CHAdeMO` with kW `150; 150`

## S02 · Plug list and kW list of different length

**Affected: 110**

Point cells where the number of plugs differs from the number of kW values, so plug and power cannot be paired one-to-one. Power per point must then be taken as the max of the kW list.

Examples:

- `AC Typ 2 Steckdose; AC Typ 2 Fahrzeugkupplung` with kW `11`
- `AC Typ 2 Steckdose; AC Typ 2 Fahrzeugkupplung` with kW `11`
- `AC Typ 2 Steckdose; AC Typ 2 Fahrzeugkupplung` with kW `11`

## S03 · Plug type vocabulary

**Affected: 10**

10 distinct raw plug labels (German, with AC/DC prefix and socket-vs-cable variants). These map onto a small normalised vocabulary (Type 2, CCS, CHAdeMO, Schuko, Type 1, MCS).

| Value | Count |
|---|---:|
| AC Typ 2 Steckdose | 138,602 |
| DC Fahrzeugkupplung Typ Combo 2 (CCS) | 54,995 |
| AC Typ 2 Fahrzeugkupplung | 19,121 |
| AC Schuko | 3,871 |
| DC CHAdeMO | 3,191 |
| DC Megawatt Charging System (MCS) | 32 |
| AC Typ 1 Steckdose | 9 |
| AC CEE 5-polig | 3 |
| DC Tesla Fahrzeugkupplung (Typ 2) | 1 |
| AC CEE 3-polig | 1 |

## P01 · Implausible power (0 kW or > 1500 kW)

**Affected: 1**

Station kW: 0 zero, 1 above 1500, 0 unparsable (min 1, median 44, max 1800). Plug kW values: 0 zero, 0 above 1500, 0 unparsable. The configured max is a deliberate upper bound for megawatt (MCS) truck charging.

Examples:

- ID 1146210 (Energie Südbayern GmbH): `1800` kW
- ID 1053821 (Audi AG): `1200` kW
- ID 1053706 (Audi AG): `1200` kW

## P02 · Station power below its strongest plug

**Affected: 169**

Records whose 'Nennleistung Ladeeinrichtung' is smaller than the largest plug power listed on the same record: an internal contradiction to flag, not to fix.

## O01 · Operator names with stray whitespace

**Affected: 6,401**

425 distinct operator spellings with leading/trailing spaces, double spaces or non-breaking spaces (U+00A0). Missing operator: 0 records.

Examples:

- 'EnBW mobility+ AG und Co.KG '
- 'E-Merge Mobility GmbH '
- 'Plenitude On The Road  S.r.l.'

## O02 · Operator variants: case / whitespace / punctuation

**Affected: 917**

11,755 distinct raw operator strings. 44 groups of spellings become identical after ignoring case, whitespace, `.`/`,`/apostrophes, hyphen vs space, `&` spacing and ß vs ss (pipeline/operators.py surface_key). Safe to merge.

Examples:

- `CUBOS Service GmbH` (485) ⟷ `Cubos Service GmbH` (1)
- `nonoxx pro GmbH` (153) ⟷ `Nonoxx Pro GmbH` (2)
- `Orange Charging B.V.` (78) ⟷ `Orange  Charging B.V.` (42)
- `KreuterMedeleSchäfer GmbH & Co. KG.` (13) ⟷ `KreuterMedeleSchäfer GmbH & Co. KG` (6)
- `Auto Weber Gmbh & Co KG` (10) ⟷ `Auto Weber GmbH & Co. KG` (1) ⟷ `Auto-Weber GmbH & Co. KG` (1)

## O03 · Operator variants: differ only by legal form

**Affected: 266**

51 further groups become identical when a trailing legal form (GmbH, AG, GmbH & Co. KG, SE, e.K., B.V., ...) is removed. NOT safe to auto-merge: 'Autohaus Schneider GmbH' and 'Autohaus Schneider e.K.' may be different companies. Goes to the review table, combined with rapidfuzz clustering.

Examples:

- `Hochsauerlandenergie GmbH` (23) ⟷ `Hochsauerlandenergie` (2)
- `S&G Automobil AG` (14) ⟷ `S & G Automobil GmbH` (10)
- `Autohaus Bruno Widmann GmbH & Co. KG` (11) ⟷ `Autohaus Bruno Widmann GmbH` (8)
- `Franz Rüschkamp GmbH & Co. KG` (16) ⟷ `Franz Rüschkamp GmbH & Co.KG` (1)
- `Autohaus Hofmann GmbH` (8) ⟷ `Autohaus Hofmann e.K. ` (1)

## C01 · Missing or zero coordinates

**Affected: 0**

0 records with an empty/unparsable coordinate, 0 with 0.

## C02 · Coordinates outside Germany

**Affected: 771**

771 records fall outside the Natural Earth 1:10m boundary. 557 are within 2 km of the border, which matches the polygon's generalisation (e.g. along the Rhine) and should be accepted with a tolerance. 214 are more than 2 km outside: genuinely wrong. Of those, 188 are the placeholder coordinate in C04; the other 26 are individual errors (typos, truncated or foreign coordinates).

Examples:

- ID 1139576 amba operations GmbH, Wendlingen am Neckar: `53,65512`, `8,256581`
- ID 1135634 amba operations GmbH, Stuttgart: `53,65512`, `8,256581`
- ID 1135635 amba operations GmbH, Stuttgart: `53,65512`, `8,256581`

## C03 · Swapped latitude/longitude

**Affected: 0**

Of the 771 outside points, 0 land inside Germany after swapping lat and lon. The rule is kept (cheap, safe) but this release has no swapped pairs.

## C04 · Placeholder coordinates shared across towns

**Affected: 196**

Coordinates used by stations in ≥ 4 different towns. A charger cannot be in several towns at once, so these are placeholders, not locations. Must be flagged and excluded from the coverage model.

Examples:

- `54,32459`, `7,36405`: 188 records in 19 towns, 1 operator(s), e.g. amba operations GmbH
- `52,516181`, `13,376935`: 8 records in 6 towns, 5 operator(s), e.g. Autohaus Hoffmann & Söhne  GmbH

## C05 · Low-precision coordinates (≤ 2 decimals)

**Affected: 204**

204 records have latitude or longitude with ≤ 2 decimals (≈1 km or worse); 19 are whole degrees (≈100 km). Flag; whole degrees are unusable.

Examples:

- ID 1076086 Annegret  Litz, Bad Krozingen: `48`, `7,700324`
- ID 1158939 Wirelane GmbH, Bad Saarow: `52,24914`, `13`
- ID 1140585 Robert Bosch GmbH, Lollar: `50,649507`, `8`

## D01 · Duplicate record IDs

**Affected: 0**

Ladeeinrichtungs-ID is unique per record.

## D02 · Same EVSE-ID on several records

**Affected: 1,046**

821 well-formed EVSE-IDs (the European charging-point identifier, which should be unique) appear on more than one record; 1,046 records are involved. The strongest duplicate signal in the register.

Examples:

- EVSE `DE*003*EMEGAKP02*01` on records ['1158823', '1158827']
- EVSE `DE*003*EMEGAKP02*02` on records ['1158823', '1158827']
- EVSE `DE*122*E7020101` on records ['1083873', '1084495']

## D03 · Exact duplicates except ID

**Affected: 14,420**

Extra records identical in every column apart from Ladeeinrichtungs-ID. 14,353 of them have no EVSE-ID: most likely identical devices at one site (e.g. 4 identical wallboxes in one car park), which the register cannot tell apart. Only the 67 that also repeat the same EVSE-IDs are real duplicate candidates.

## D05 · EVSE-ID cells that are not EVSE-IDs

**Affected: 3,748**

5,198 distinct EVSE-ID cells on 3,748 records contain a token that is not a valid ISO 15118 EVSE-ID (free text, truncated IDs, internal numbers). 1,364 cells hold several IDs separated by ';', tabs or line breaks.

Examples:

- `'\t7137745'`
- `'\tDEDEIS001701'`
- `'\tDEDEIS001702'`

## D04 · Same operator within 20 m

**Affected: 70,415**

Records that have another record of the same operator within 20 m. Mostly NOT duplicates: a site with 8 chargers is registered as 8 devices at one address. So this is a site-grouping signal; only records also sharing EVSE-IDs (D02) or all values (D03) are duplicate candidates.

## X01 · Status values

**Affected: 0**

Only operational records are published.

| Value | Count |
|---|---:|
| In Betrieb | 116,423 |
| In Wartung | 20 |

## X02 · Charging type by register

**Affected: 0**

The register's own normal/fast split (fast = DC, > 22 kW by the Ladesäulenverordnung), not our HPC ≥ 150 kW threshold.

| Value | Count |
|---|---:|
| Normalladeeinrichtung | 85,288 |
| Schnellladeeinrichtung | 31,155 |

## X03 · Commissioning dates

**Affected: 0**

Format DD.MM.YYYY; 0 unparsable; range 1992-10-01 – 2026-09-01.

## X04 · Non-breaking spaces in text fields

**Affected: 3,051**

Records with U+00A0 in operator, street, house number or town. Invisible, but breaks equality and grouping.

## X05 · Point count vs filled point groups

**Affected: 0**

'Anzahl Ladepunkte' disagrees with the number of filled Steckertypen{n} groups.
