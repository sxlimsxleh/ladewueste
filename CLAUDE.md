# Ladewüste — where Germany runs out of fast chargers

Turn the Bundesnetzagentur's public charger register (a messy, Excel-generated CSV) into a playful web app: a 3D desert map, a "drop a charger" play mode, and a Data Doctor page that shows every cleaning fix with counts.

I (Selim) own this code and must explain every line in interviews. Work in small steps, plan first, ask before adding dependencies or changing interfaces below.

## Customer scenario (fictional)

Voltbahn GmbH, a charge-point operator, wants to choose its next 20 high-power charging (HPC, >= 150 kW) sites. Their analyst can't work with the raw register. Deliver: trustworthy cleaned data, a coverage model, and a tool the expansion team actually enjoys using.

## Non-negotiable rules

1. **Profile before cleaning.** First produce `docs/mess_report.md` with real counts of every problem found in the raw file. Never assume the format; detect encoding, header offset and delimiter in code, and fail loudly if the layout changes.
2. **Every cleaning rule is a dbt model + a dbt test**, and every rule emits a count into `quality_report.json` (rule id, description, rows affected, 3 before/after examples). Fix when safe, otherwise flag; never silently drop.
3. **Raw data is never committed** (`data/raw/` gitignored). The pipeline is reproducible from the downloaded file with one command.
4. **Config, not constants:** HPC threshold (150 kW), desert radius (km), H3 resolutions live in `config.yaml`.
5. **Typed contracts end to end:** Pydantic response models in the API; generated TypeScript types in the web app (from the OpenAPI schema).
6. **UI quality matters:** it should look and feel like a product, not a notebook. Dark map, smooth transitions, loading and empty states, keyboard-accessible controls, works on a laptop screen.
7. Credit the Bundesnetzagentur as data source in the UI footer and README (check the licence on the download page).

## Stack

- pipeline/: Python 3.11, uv, DuckDB, dbt-duckdb, h3 (h3-py v4), rapidfuzz, scikit-learn (BallTree, haversine), pyyaml
- api/: FastAPI, Pydantic v2, DuckDB reading gold Parquet, pytest, httpx TestClient
- web/: React + TypeScript + Vite, MapLibre GL + deck.gl (H3HexagonLayer, ScatterplotLayer, IconLayer), h3-js, Tailwind + shadcn/ui, TanStack Query, openapi-typescript; a free no-key basemap style
- ops: Docker Compose (api + web), GitHub Actions (dbt build + test, pytest, tsc --noEmit, eslint), Makefile

## Layout

```
data/raw/                 # Ladesaeulenregister CSV (gitignored)
data/ref/germany.geojson  # Natural Earth admin-0 boundary for Germany
config.yaml
pipeline/
  load_bronze.py          # sniff encoding/header/delimiter, load raw rows as text into DuckDB
  profile.py              # writes docs/mess_report.md
  dbt/models/
    silver/stations.sql         # one row per station: typed, coords parsed, operator normalised
    silver/charging_points.sql  # unpivoted: one row per charging point (power_kw, plug_types[])
    gold/hexes.sql              # per H3 cell: points, total kW, HPC count, nearest HPC km, is_desert
    gold/operators.sql
  geo.py                  # nearest-HPC distance (BallTree), desert flag, greedy planner
  report.py               # quality_report.json
  export.py               # gold -> data/gold/*.parquet
api/app/
  main.py  models.py  db.py
  routes: GET /hexes?res=6|7&min_kw=  GET /stations?bbox=  GET /quality  GET /plan?n=10&radius_km=
web/src/
  pages/DesertMap.tsx  pages/DataDoctor.tsx
  components/PlayMode.tsx  SidePanel.tsx  Filters.tsx  DesertCounter.tsx
  lib/api.ts (typed client)  lib/coverage.ts (h3-js gridDisk coverage)
docs/mess_report.md
DECISIONS.md              # decision, rejected alternative, where the AI got it wrong
```

## Cleaning rules to investigate (confirm with the profile, then implement what's real)

- metadata lines above the header; semicolon delimiter; non-UTF-8 encoding
- German decimal commas in lat/lon and kW
- wide columns per charging point (power + plug types for point 1..N) -> unpivot
- plug types as comma-separated lists -> array, normalised vocabulary (Type 2, CCS, CHAdeMO, Schuko, ...)
- operator name variants (case, whitespace, legal suffixes GmbH / AG / AG & Co. KG / SE) -> canonical name via rules + rapidfuzz clustering; export the merge table for review
- coordinates outside Germany's boundary, swapped lat/lon (swap if the swap lands inside), zero/null coords -> flag
- duplicate stations: records sharing a valid EVSE-ID -> flag `duplicate_of`, keep provenance (decided in M1/M2: "same operator within ~20 m" is a *site*, not a duplicate)
- implausible power values (0, or above a sane max) -> flag

## Coverage model

- Universe: H3 cells (res 6 for the map, res 7 for detail) whose centre lies inside Germany.
- Site: usable stations of the same operator within `site_radius_m` (20 m) of each other. HPC hub: a site with >= `hub_min_hpc_points` (6) HPC points.
- `nearest_hpc_km` per cell from cell centre to the nearest HPC charging point; `nearest_hub_km` to the nearest HPC point of a hub (BallTree haversine).
- `is_desert = nearest_hub_km > desert_radius_km` (config, default 25). Decided in M3: with "any HPC point" only 62 km² of Germany was desert at 25 km.
- Coverage rule (planner and play mode): a cell is covered by a site if its centre is within `desert_radius_km` great-circle distance of the site.
- Greedy planner: candidate = any desert cell; pick the cell that covers the most uncovered desert km²; mark them covered; repeat n times. Return sites in pick order with "desert km² removed" per pick.
- Play mode does the same coverage update client-side with h3-js (`gridDisk` for candidates, then the distance filter) so it's instant; API `/plan` is the benchmark the user competes against.

## Screens

1. **Desert map:** dark basemap, extruded H3 hexes (elevation = fast-charging kW within the cell, colour = nearest HPC distance; desert cells in a sand colour). Filters: power class, operator. Click a cell -> side panel (counts, kW, top operators, nearest HPC distance).
2. **Play mode:** toggle on; click to drop a virtual HPC site; covered desert cells turn green with a short animation; counter "Desert area: X km² -> Y km²" and "You vs the algorithm" score; "Auto-plan 10 sites" animates the API plan; reset button.
3. **Data Doctor:** funnel from raw rows to clean stations and charging points; one card per rule (count, why it matters, before/after examples); the operator merge table.

## Milestones (commit after each, tests green)

1. Setup + bronze loader + `docs/mess_report.md` with real counts
2. Silver models + dbt tests + quality_report.json
3. Gold: hexes, nearest-HPC, deserts, planner + unit tests (planner on a tiny synthetic grid)
4. API endpoints + pytest + OpenAPI -> TS types
5. Web: desert map + side panel
6. Web: play mode + counter + auto-plan
7. Web: Data Doctor
8. Docker Compose, GitHub Actions, README as a deployment memo for Voltbahn (problem, mess found, what shipped, design decisions with rejected alternatives, limits: no demand weighting yet)

## Commands (keep working)

```
make setup      # uv sync + npm install
make pipeline   # bronze -> dbt build -> gold parquet -> quality_report.json
make api        # uvicorn on :8000
make web        # vite dev server on :5173
make test       # dbt test + pytest + tsc
```

## Working agreement

- Plan mode first for every milestone; show the plan before code.
- Readable over clever; type hints and TS strict mode.
- After each milestone: 5-bullet explanation of what you built + one thing I should double-check by hand.
