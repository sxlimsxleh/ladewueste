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

## M5 · Map stack and versions
- **Decision:** MapLibre + deck.gl `MapboxOverlay` in *interleaved* mode: hexes are drawn into MapLibre's own WebGL context, so they share the camera and depth buffer with the basemap. No react-map-gl wrapper: one `useEffect` creates the map, another pushes new layers.
- **Where the AI was wrong (twice):** it first installed the newest MapLibre (6.17). Vite's pre-bundling broke MapLibre 6's separate worker file, and after working around that, deck.gl 9.4's interleaved mode crashed reading `map.transform._nearZ` (renamed in MapLibre 6). deck.gl 9.4 is built against MapLibre 5, so MapLibre is pinned to **5.24.0**. Lesson: "latest" of two libraries that touch each other's internals is not a version strategy.
- **Basemap:** OpenFreeMap "dark" (no key, free including commercial use, OSM data). Rejected: CARTO Dark Matter (free tier excludes commercial use, which matters for a customer pitch).
- **npm audit:** two advisories (`fflate`, `image-size`) come only through deck.gl's 3D-tiles/glTF loaders; the app never loads ZIP or ICNS files through them.

## M5 · Visual encoding
- **Height** = HPC kW in the cell on a square-root scale (250 m per sqrt(kW)): the busiest cell has 35 MW, the median HPC cell 1.6 MW; linear heights would show Berlin and Munich and nothing else.
- **Height vs zoom:** metres grow on screen with every zoom level, so columns that read well over Germany became a wall over Berlin. `elevationScaleForZoom` = 2^(baseZoom - zoom) keeps columns about the same screen height; at station zoom the hexes lie flat and fade so station dots stay readable.
- **Colour** = distance to the nearest hub, teal (0 km) -> indigo (25 km); deserts in sand. Cool covered cells vs a single warm desert colour makes the answer to "where?" visible at a glance.
- **Filters never recolour deserts** (same rule as the API) and the panel says so in one line.

## M5 · Dev setup
- **Decision:** the browser calls `/api/...`; Vite proxies it to FastAPI. Only port 5173 needs to be open, which is what makes Codespaces work. `allowedHosts: [".app.github.dev"]` because Vite rejects unknown Host headers by default.
- **Bug found by screenshot, not by tests:** MapLibre's CSS sets `.maplibregl-map { position: relative }`, which silently overrode `absolute inset-0`: the map was 300 px tall and hidden behind the panel. Fixed with a wrapper div. Typecheck and unit tests were green the whole time.

## M6 · Play mode: one coverage rule in two languages
- **Decision:** `web/src/lib/coverage.ts` reimplements the planner's rule in the browser: h3-js `gridDisk` only *finds candidates* (enough rings for the radius, spacing taken 20% below average, plus one ring of margin); `greatCircleDistance <= radius` *decides*. Coverage is recomputed from scratch on every change (10 sites x ~130 candidate cells), which makes undo a one-liner and keeps state minimal.
- **Proof of fairness:** `coverage.parity.test.ts` (`make parity`, needs the API) runs the algorithm's 10 picks through the browser code and compares with `/plan`: every pick's km² matches to 3 decimals. A unit test also compares `coveredBy` against brute force over a whole board, so the gridDisk shortcut never misses a cell.
- **Rejected:** plain `gridDisk(k)` rings (approximates a circle; the scores would disagree); asking the API on every click (not instant, and the game would depend on network latency).
- **Score:** you vs the algorithm's first *k* picks, where *k* = your number of sites, so 3 sites are compared with 3 sites. The greedy plan's first *k* picks are themselves the greedy plan for *k*, so this is the fair comparison.
- **Play mode stays on res 6** and turns the map into a flat board: covered cells fade back, deserts stay sand, covered deserts turn green.
- **Keyboard:** P toggles play mode, Enter drops a site at the crosshair (the map centre; arrow keys pan), Backspace undoes. All are ignored while typing in a field or focused on a button.
- **Where the AI was wrong:** the parity test first failed on `fetch` because Node resolves `localhost` to IPv6 `::1` while uvicorn listens on `127.0.0.1`; not a coverage bug, but it looked like one for a minute.

## M7 · Data Doctor
- **Routing:** a 20-line hash router (`#/`, `#/doctor`) on `useSyncExternalStore` + `hashchange`. Works on any static host without rewrites; links stay real `<a href>`, so keyboard, middle-click and the back button work. **Rejected:** react-router (a dependency for two pages).
- **The map stays mounted** under the Data Doctor (`inert` + `aria-hidden`), so a play-mode game survives a visit to the other page; checked by placing a site, switching pages and switching back.
- **Contract change (approved):** `/quality` gained `funnel.excluded_by_reason` and `operator_merges` instead of a new route: one request for the whole page, and the merge table is only 111 rows. `report.py` builds the merges once and writes both the JSON and the committed CSV from it (the CSV came out byte-identical).
- **Exclusion reasons** are exclusive and ordered (placeholder -> outside -> whole-degree -> duplicate), so 196 + 26 + 17 + 537 = 776 = stations - usable stations; `report.py` raises if any unusable station matches no reason.
- **Funnel chart:** single-hue horizontal bars (magnitude, not identity), every bar labelled with its exact value and % of the previous step, so nothing depends on reading a bar length or a colour. Actions (fixed / flagged / accepted) are chips with an icon *and* a word.
- **Where the AI was wrong:** the R06 example showed "EnBW mobility+ AG und Co.KG" -> identical text, because the removed character was a trailing space. `showInvisibles` now also marks leading, trailing and doubled spaces (␣). And the source of that very helper contained a literal non-breaking space instead of the ` ` escape: correct at runtime, invisible in review. Replaced with the escape; `web/src` has no literal NBSP left.

## M8 · Docker
- **Decision:** one Python image for the API *and* the pipeline (different commands), an nginx image for the web build. Data lives in a mounted volume, never in an image; the API mounts it read-only. `pipeline/run_all.py` is the single entry point used by `make pipeline`, the Docker `pipeline` service and CI.
- **Verified end to end:** from an empty `data/` folder the pipeline container downloaded the register, passed all 85 dbt nodes and produced the same gold tables (115,667 stations, 207,668 points); `docker compose up` then served the app, `/api/plan` and `/api/quality` through nginx.
- **Image size:** the API image is 1.3 GB, mostly dbt, SciPy, pandas and DuckDB (742 MB venv). **Where the AI was wrong:** the first build was 2.2 GB because uv's download cache was baked into a layer; now a BuildKit cache mount.
- **Corporate proxies:** an optional `extra_ca` BuildKit secret is trusted only during package installs and never stored. Needed in the development sandbox; equally needed at customers with TLS inspection.

## M8 · CI
- **Decision:** every push runs Python lint + tests, the full pipeline with all dbt tests on a **synthetic register fixture** (generated by a committed script, checked to match it), web lint/typecheck/tests/build and both Docker builds; a **weekly** workflow downloads the real register.
- **Rejected:** downloading the real file on every push (55 MB from a government server, CI depending on their uptime) and committing a sample of real data (rule 3).
- **Where the fixture caught a design flaw:** the test "every approved operator merge names known operators" failed on the fixture, because the real approvals don't exist in invented data. The same would happen to the real pipeline the day an approved operator leaves the register. Split into an *error* when an approval points to a non-existent target (a typo) and a *warning* when the source name is not in this release (stale, harmless).
- **Lint:** `ruff check` and eslint (with the React hooks rules) are enforced. The hooks rules found four real issues (setState inside effects, a ref written during render), all fixed by deriving state instead of syncing it; no rule is disabled. `ruff format` is *not* enforced: it would rewrite 21 files for formatting only.
- **Reports from non-default data folders** go next to that data, never into the committed `docs/`, so a fixture run cannot overwrite the real mess report.

## M8 · Licence
- Code under MIT (Selim's choice). Data licences are separate and credited in the README and the UI footer: Bundesnetzagentur CC BY 4.0, Natural Earth public domain, OpenStreetMap ODbL via OpenFreeMap.
