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

## M3 · What a "charging desert" is
- **Decision (approved by Selim):** desert = no **HPC hub** (a site with >= 6 HPC points) within 25 km. Result: 600 res-6 cells, 19,318 km² (5.4% of Germany). `hub_min_hpc_points` is in `config.yaml` and is an assumption to confirm with the customer.
- **Rejected:** CLAUDE.md's original "nearest single HPC point > 25 km". On the real data that leaves 62 km² (2 cells, both on the border): the max distance anywhere is 25.4 km. Of 9,706 sites with an HPC point, 4,594 have fewer than 4, often one 150 kW charger at a car dealer, which is not what an expansion team means by coverage. Also rejected: lowering the radius to 10 km (keeps counting lone chargers as coverage) and changing radius and hub size together (harder to explain).
- **Lesson:** the brief's definition came from before the data was profiled. Running the numbers first turned "build the planner" into a question for the customer, which is the actual FDE job.

## M3 · Coverage rule shared by planner and play mode
- **Decision:** covered = cell centre within the radius, great-circle. The planner uses BallTree; the browser will use h3-js `gridDisk` to find candidates and the same distance filter, so the user's score and the algorithm's are computed identically.
- **Rejected:** plain `gridDisk(k)` rings: a hexagonal ring only approximates a circle, so the two scores would disagree slightly.
- **Objective:** maximise uncovered desert **km²** (cell areas vary with latitude), not cell count, to match the "Desert area: X km² → Y km²" counter.

## M3 · Sites and hubs
- **Decision:** sites are connected components (union-find over BallTree neighbour pairs, per operator): A–B and B–C within 20 m make A, B, C one site even if A–C is 40 m. A site is named after its lowest station_id, which stays stable between runs.
- **Where the AI was wrong:** hub distance was first measured to each hub site's *average* position. A dbt test (`nearest HPC point <= nearest hub`) failed on 9 cells: a chained site can stretch over hundreds of metres (the Tesla factory site has 513 stations) and its centre is not where any charger is. Now measured to the hub's actual HPC points.

## M3 · Known limitation: borders
- HPC chargers just across the border (NL, BE, LU, FR, CH, AT, CZ, PL, DK) are not in the register, so border areas look more like deserts than they are: planner pick #18 on the default run sits at the Swiss border near Waldshut. No foreign data source is in scope; documented here and for the README's limits.

## M4 · API shape
- **Decision:** the API reads only `data/gold/*.parquet` through an in-memory DuckDB (one view per file, one cursor per request). It opens the files on first request, so it starts before the pipeline has run and answers 503 "run `make pipeline`" instead of crashing.
- **Decision:** `/hexes` filters (min_kw, operator) re-aggregate counts and height from `points`, but never change `is_desert` or distances: coverage is defined by hubs, and a display filter must not make deserts appear or vanish.
- **Decision:** res 7 needs a bbox (all 76,744 cells would be ~15 MB of JSON); res 6 is 3.6 MB raw, 0.8 MB gzipped.
- **Added (approved):** `/config` (so the browser uses the planner's exact parameters) and `/operators?q=` (filter dropdown).
- **Rejected:** loading the DuckDB file the pipeline writes (couples the API to dbt internals and locks the file during a pipeline run).

## M4 · Typed contract
- **Decision:** Pydantic models -> `api/openapi.json` (committed) -> `openapi-typescript` -> `web/src/lib/api-types.ts` (committed, never hand-edited). A pytest fails when the committed schema drifts from the code; checked by adding a field without regenerating.
- **Checked:** the generated types reject a missing `res`, a string `min_kw` and a misspelt response field at compile time.
- **Tooling:** TypeScript pinned to 5.9.3, not the new 7.0: openapi-typescript declares `typescript ^5.x`, typescript-eslint supports `< 6.1`.
- **API tests** run on a 3-cell synthetic gold folder built in `conftest.py`, so CI needs no 55 MB download.
