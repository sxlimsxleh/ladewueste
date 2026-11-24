# Demo kit

Everything needed to show Ladewüste: links, a 30-second pitch, a 3-minute walkthrough, likely
questions with short answers, a fallback plan, and a LinkedIn post draft.

| | |
|---|---|
| **Live demo** (static, no install) | https://sxlimsxleh.github.io/ladewueste/ |
| **Video** (75 s) | [`docs/demo/ladewueste-demo.mp4`](demo/ladewueste-demo.mp4) |
| **Code + deployment memo** | https://github.com/sxlimsxleh/ladewueste |

The live demo is the real web app reading precomputed API answers, rebuilt weekly from the latest
register. Two things need the full app (`make pipeline && make api && make web`, or Docker): the
operator filter and street-level zoom with station dots.

## The 30-second pitch

> Germany publishes a register of every public charging station: 116,000 records, as a CSV that
> looks hand-made in Excel. I built the pipeline that cleans it, with every fix counted and tested,
> and a map that answers one question: where does Germany run out of *fast* chargers? It turns out
> 19,318 km², 5.4% of the country, is more than 25 km from a proper fast-charging hub. You can
> drop your own hubs on the map and race an optimisation algorithm to cover it.

## The 3-minute walkthrough (live demo)

1. **The number (0:00).** Point at **19,318 km²**. "Sand means more than 25 km from a hub: a site
   with at least six chargers of 150 kW or more."
2. **The decision behind it (0:30).** Click a sand cell around Salzwedel (north-east of Wolfsburg):
   some of them have several fast chargers and one 2 km away, yet they are deserts. "If one charger counted, Germany would have
   almost no deserts (62 km²). Half the fast-charging sites have fewer than four chargers, often one
   at a car dealer. Profiling the data first changed the question."
3. **Filters (1:00).** Switch to **300+** kW. Heights drop, the sand doesn't move. "Filters change
   what you see, never the definition of a desert."
4. **Play mode (1:20).** Press **P**. Let the other person drop two or three hubs; desert cells turn
   green and the counter drops. Click **Auto-plan 10** and read the score. "The browser recomputes
   coverage itself, and a test proves it matches the Python planner to the km² for every pick, so
   the game is fair."
5. **Data Doctor (2:10).** Switch tabs. Show the funnel (116,443 records, nothing dropped, 776 kept
   out of the model with a reason each), then card **R10**: "196 stations from 19 cities, all at
   one point in the North Sea. A placeholder. Flagged, not guessed."
6. **Close (2:45).** "It's a starting point, not an answer: no demand weighting yet, chargers across
   the border are missing, and the hub size is an assumption to confirm with the customer."

## Likely questions, short answers

**Why hubs and not single chargers?**
With single chargers only 62 km² is "desert", so the map says nothing. An operator planning HPC sites
competes with hubs, not with one 150 kW unit at a car dealer. The threshold is one value in
`config.yaml` and is flagged as an assumption.

**Why a greedy algorithm?**
Placing sites to cover the most area is the maximum-coverage problem (NP-hard). Greedy is fast, easy
to explain, and provably within about 63% of the best possible plan. An integer-programming solver
could beat it for the real 20-site decision; that is listed as a next step.

**How do you know the cleaning is right?**
Every rule is a dbt model with its own test (55 tests), and every rule reports how many records it
touched with real before/after examples (the Data Doctor). The profile of the raw file was written
*before* any cleaning, so the rules come from counted problems, not guesses. I also broke inputs on
purpose to check that the tests fail.

**What happens when the Bundesnetzagentur changes the file?**
The loader detects encoding, header row, delimiter and column groups, and stops with a clear error
if the layout changes. A weekly GitHub Actions job downloads the real file and runs everything, so a
format change shows up in CI before anyone's map breaks.

**What did the AI get wrong?**
Several things, all logged in `DECISIONS.md`. Fuzzy operator matching suggested merging different
companies (Stadtwerke Kempen into Kerpen). Hub distance was first measured to the *average* position
of a site that stretches over hundreds of metres. The newest MapLibre broke deck.gl's 3D mode. The
first map rendered 300 px tall while every test was green: the screenshot caught it, not the tests.

**Why not drop the bad rows?**
Then nobody could see them. Flags keep every record and a single `usable_for_coverage` decides what
the model uses: 115,667 of 116,443 stations.

**How would this scale to other countries or a real customer?**
The pipeline is driven by `config.yaml` and the register's layout checks. A new country needs its own
loader and boundary; a real customer would add demand data (traffic, population), cross-border
chargers, and their own sites as an operator filter.

**Is the data licensed for this?**
Yes: the register is CC BY 4.0 (credited as Bundesnetzagentur.de in the app and README), the boundary
is public domain, the basemap is OpenStreetMap via OpenFreeMap. The raw file is never committed.

## If the live demo fails

- **Map stays blank:** the viewer's browser has no WebGL (some locked-down laptops). Switch to the
  video, or share your own screen.
- **Page doesn't load:** play the MP4 from the repo; it shows the same flow.
- **You need the operator filter or station dots:** run the full app in a Codespace
  (`make setup && make pipeline`, then `make api` and `make web`).

## LinkedIn post draft

> **Where does Germany run out of fast chargers?**
>
> The Bundesnetzagentur publishes every public charging station in Germany: 116,443 records in one
> CSV. It's open data, and it's messy: line breaks inside fields, German decimal commas, the same
> operator spelled five ways, and 196 stations from 19 cities placed at a single point in the North Sea.
>
> I built **Ladewüste** ("charging desert") to turn it into something an expansion team can use:
> - a tested pipeline (DuckDB + dbt, 13 cleaning rules, 55 tests, nothing silently dropped)
> - a 3D map of Germany in H3 hexagons
> - a game: drop your own fast-charging hubs and race a greedy optimisation algorithm
>
> The most interesting part wasn't code. Counting any single fast charger as coverage, Germany has
> almost no gaps left. Counting real hubs (6+ chargers at one site), **19,318 km²** is more than
> 25 km from one. The definition was the decision.
>
> 🔗 Try it (no install): https://sxlimsxleh.github.io/ladewueste/
> 💻 Code and design decisions: https://github.com/sxlimsxleh/ladewueste
>
> Data: Bundesnetzagentur.de (CC BY 4.0). Built with Python, DuckDB, dbt, FastAPI, React, deck.gl.
>
> #DataEngineering #EMobility #OpenData #dbt

Attach `docs/demo/ladewueste-demo.mp4` to the post: native video gets more reach than a link.

## Re-recording the video

The video is rendered frame by frame from the static demo, so it can be regenerated after changes:

```bash
cd web && VITE_DEMO=1 npx vite --port 5174    # needs web/public/demo-data: uv run python -m api.export_demo
node docs/demo/record_demo.cjs http://localhost:5174/ /tmp/frames   # in another terminal
docs/demo/make_video.sh /tmp/frames
```
