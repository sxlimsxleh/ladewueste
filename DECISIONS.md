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
