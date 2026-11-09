# Decisions

Each entry: the decision, the alternative we rejected, and where the AI's first attempt was wrong.

## M1 · Data source and licence
- **Decision:** download the register from the official BNetzA page; licence CC BY 4.0, attribution "Bundesnetzagentur.de" (stated on the page, checked 2026-11-09). The CSV link is discovered on the landing page because the file name carries its publication date.
- **Rejected:** hard-coding the CSV URL (breaks on every release); the XLSX (newer date, but would add an Excel dependency).
- **Note:** on 2026-11-09 the page offered the XLSX dated 30.09.2026 but the CSV dated 01.09.2026. We use the CSV and record its date + SHA-256 in `data/raw/manifest.json`.

## M1 · Encoding
- **Decision:** detect encoding by strict decode attempts (UTF-8 with optional BOM, then cp1252).
- **Where the AI was wrong:** the plan assumed an Excel cp1252 file. The current release is UTF-8 with a BOM. Detection, not assumption, caught it.

## M1 · Loading the CSV
- **Decision:** Python sniffs the layout; DuckDB `read_csv` loads with those explicit parameters (auto-detect off); the loader then cross-checks DuckDB's record count and ID sequence against Python's `csv` parse and fails on any difference.
- **Rejected:** inserting Python-parsed rows with `executemany` (correct but took 4 min vs 3 s); DuckDB auto-detection alone (would hide layout changes).
- **Where the AI was wrong:** first version used `executemany`; too slow.

## M1 · Point in Germany
- **Decision:** ~20 lines of numpy even-odd ray casting against the Natural Earth 1:10m polygon; 1 s for 116k points. Points outside but within `border_tolerance_km` (2 km) of the border count as boundary generalisation, not errors.
- **Rejected:** shapely / DuckDB spatial (extra dependency or extension download for one test).
- **Where the AI was wrong:** first measured distance to the nearest border *vertex*. 1:10m vertices are kilometres apart, so Breisach (on the Rhine) looked 2+ km outside. Switched to distance to the nearest *edge*: 291 -> 214 "genuinely wrong" points.

## M1 · What counts as a duplicate
- **Decision:** duplicate candidates = shared well-formed EVSE-ID, or identical in every column *and* carrying EVSE-IDs. Same-operator-within-20 m is a site-grouping signal, not a duplicate signal.
- **Rejected:** CLAUDE.md's first idea "same operator within ~20 m -> merge": 70,413 records match that, because sites with several chargers are registered as several devices. Merging them would delete real chargers.
- **Where the AI was wrong:** first EVSE check split only on `;` and counted junk tokens (`&`, `(NEUE`) as shared IDs; now splits on `;`/whitespace and only counts IDs matching the ISO 15118 pattern.

## M2 · Where the cleaning logic lives
- **Decision:** each rule is a dbt model that outputs only the rows it touched (before/after/action); `silver.stations` and `silver.charging_points` apply the same logic through shared macros (`clean_text`, `german_decimal`, ...), so the reported fix and the applied fix cannot drift apart. The two rules that need Python (point-in-polygon, rapidfuzz) are dbt Python models that call plain, unit-tested functions in `pipeline/`.
- **Rejected:** a Python pre-step outside dbt (then those rules would have no dbt lineage or tests); putting all logic inside one big `stations.sql` (no per-rule counts).
- **Config:** `pipeline/run_dbt.py` passes `config.yaml` values to dbt as `--vars`; `dbt_project.yml` defaults exist only so `dbt parse` works.

## M2 · Duplicates vs sites
- **Decision (approved by Selim):** only records sharing a well-formed EVSE-ID are duplicates (R13: 543 records, connected components, lowest ID stays primary, nothing deleted). "Same operator within 20 m" becomes a site grouping in milestone 3.
- **Rejected:** CLAUDE.md's original "same operator within ~20 m -> merge" (would hide 70,413 real chargers).

## M2 · Operator merges
- **Decision:** R07 merges only formatting variants automatically (case, spaces, `.`/`,`, apostrophes, hyphen vs space, `&` spacing, ß/ss). R08 legal-form and rapidfuzz matches are *suggestions* in `docs/operator_merge_review.csv`, applied only when a human adds them to `seeds/operator_overrides.csv`.
- **Where the AI was wrong:** at threshold 92 the fuzzy matcher suggested mostly different companies: Stadtwerke Kempen → Kerpen, Autohaus Meier ↔ Reier, Jana ↔ Jan Richter. Even at 96–98: Schmid/Schmidt, Hoffmann/Hofmann, Heilsbronn/Heilbronn. String similarity can't tell a typo from a different surname or town. The genuine fuzzy hits were formatting (Elektro-Rosin / Elektro Rosin, Schloß / Schloss), so those rules moved into the safe R07 key, and the threshold went up to 96 to keep the review list short. Fuzzy remains review-only.

## M2 · Coordinates
- **Decision:** flags never delete rows. `usable_for_coverage` = inside / swapped-and-fixed / within 2 km of the border, and not a placeholder, not whole-degree precision, not a duplicate (115,667 of 116,443).
- **Rejected:** dropping flagged rows (the Data Doctor could no longer show them, and a changed threshold would need a reload).

## M2 · Tests that fail when they should
- Checked by breaking the seeds on purpose: removing `AC Schuko` from `plug_type_map.csv` fails `r03_no_unknown_plug_labels` (3,871 points), and a typo in `operator_overrides.csv` fails `r08_overrides_point_to_known_operators`.
