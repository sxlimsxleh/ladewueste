import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { IconLayer, ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import { useQuery } from "@tanstack/react-query";
import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { Filters } from "@/components/Filters";
import { Footer } from "@/components/Footer";
import { DesertCounter } from "@/components/DesertCounter";
import { Legend } from "@/components/Legend";
import { PlayControls, PlaySwitch } from "@/components/PlayMode";
import { SidePanel } from "@/components/SidePanel";
import { ErrorCard, LoadingCard } from "@/components/StatusCard";
import { api, type Hex, type Station } from "@/lib/api";
import {
  distanceColor,
  elevation,
  elevationScaleForZoom,
  formatCount,
  formatKm,
  formatKm2,
  formatKw,
  formatPercent,
  POWER_CLASSES,
  type PowerClassId,
} from "@/lib/scales";
import type { Site } from "@/lib/coverage";
import { useMapView } from "@/lib/useMapView";
import { usePlayGame } from "@/lib/usePlayGame";

const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/dark";
const GERMANY_VIEW = { center: [10.45, 51.15] as [number, number], zoom: 5.35, pitch: 45, bearing: -8 };
/** Zoom levels where the map switches to the detail resolution and starts showing stations. */
const DETAIL_ZOOM = 9;
const STATIONS_ZOOM = 11;
/** Sites per game, for you and for the algorithm. */
const PLAY_BUDGET = 10;
const GREEN: [number, number, number, number] = [74, 222, 128, 235];
const USER_PIN: [number, number, number] = [255, 255, 255];
const ALGORITHM_PIN: [number, number, number] = [167, 139, 250];
/** A map pin, drawn as an SVG mask so deck.gl can colour it per plan. */
const PIN_ICON = {
  url:
    "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(
      `<svg xmlns="http://www.w3.org/2000/svg" width="48" height="64" viewBox="0 0 48 64"><path d="M24 2C12 2 3 11 3 23c0 15 21 38 21 38s21-23 21-38C45 11 36 2 24 2z" fill="white"/><circle cx="24" cy="23" r="8" fill="black"/></svg>`,
    ),
  width: 48,
  height: 64,
  anchorY: 62,
  mask: true,
};

/** True when a key press belongs to a text field or button, not to the map. */
function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLElement && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT", "BUTTON"].includes(target.tagName));
}

function tooltipFor(info: PickingInfo): { html: string; style: Record<string, string> } | null {
  const style = {
    background: "rgba(17,22,30,0.94)",
    color: "#e6edf3",
    fontSize: "12px",
    padding: "8px 10px",
    borderRadius: "8px",
    border: "1px solid rgba(148,163,184,0.16)",
  };
  const hex = info.object as Hex | undefined;
  if (info.layer?.id.startsWith("hexes") && hex) {
    const status = hex.is_desert
      ? `<span style="color:#e8be78">Desert</span>`
      : `<span style="color:#5eead4">Covered</span>`;
    return {
      html: `${status} · ${formatKm(hex.nearest_hub_km)} to a hub<br/>${formatCount(hex.n_hpc_points)} HPC points · ${formatKw(hex.hpc_kw)}`,
      style,
    };
  }
  const station = info.object as Station | undefined;
  if (info.layer?.id === "stations" && station) {
    return {
      html: `<b>${station.operator}</b><br/>${formatKw(station.max_point_kw)} max · ${station.n_points} points<br/>${[station.street, station.house_no].filter(Boolean).join(" ")}, ${station.town ?? ""}`,
      style,
    };
  }
  return null;
}

export function DesertMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<MapboxOverlay | null>(null);
  const [map, setMap] = useState<maplibregl.Map | null>(null);
  const view = useMapView(map);

  const [powerClass, setPowerClass] = useState<PowerClassId>("all");
  const [operator, setOperator] = useState<string | null>(null);
  const [selected, setSelected] = useState<{ cell: string; res: number } | null>(null);
  const minKw = POWER_CLASSES.find((c) => c.id === powerClass)?.minKw ?? null;
  const filtered = minKw !== null || operator !== null;

  const config = useQuery({ queryKey: ["config"], queryFn: api.config });
  const resMap = config.data?.h3_res_map;
  const resDetail = config.data?.h3_res_detail;
  const radiusKm = config.data?.desert_radius_km ?? 25;

  const hexes = useQuery({
    queryKey: ["hexes", resMap, minKw, operator],
    queryFn: () => api.hexes({ res: resMap!, min_kw: minKw, operator }),
    enabled: resMap !== undefined,
    placeholderData: (previous) => previous, // keep the old map while a filter loads: no flashing
  });

  const plan = useQuery({
    queryKey: ["plan", PLAY_BUDGET],
    queryFn: () => api.plan({ n: PLAY_BUDGET }),
    enabled: hexes.data !== undefined, // fetched in the background so Auto-plan and the score are instant
  });
  const game = usePlayGame({ hexes: hexes.data?.hexes, plan: plan.data, radiusKm, res: resMap, budget: PLAY_BUDGET });
  const playing = game.active;

  // Play mode always uses the map resolution: "a cell" must not change meaning mid-game.
  const showDetail = !playing && (view?.zoom ?? 0) >= DETAIL_ZOOM;
  const detail = useQuery({
    queryKey: ["hexes", resDetail, minKw, operator, view?.bbox],
    queryFn: () => api.hexes({ res: resDetail!, min_kw: minKw, operator, bbox: view!.bbox }),
    enabled: showDetail && resDetail !== undefined && view !== null,
    placeholderData: (previous) => previous,
  });

  const showStations = !playing && (view?.zoom ?? 0) >= STATIONS_ZOOM;
  const stations = useQuery({
    queryKey: ["stations", view?.bbox],
    queryFn: () => api.stations({ bbox: view!.bbox, limit: 3000 }),
    enabled: showStations && view !== null,
    placeholderData: (previous) => previous,
  });

  // Create the map once. deck.gl draws into MapLibre's own WebGL context ("interleaved"),
  // so hexagons and basemap labels share one depth buffer and one camera.
  useEffect(() => {
    if (!containerRef.current) return;
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      ...GERMANY_VIEW,
      maxPitch: 60,
      attributionControl: { compact: true },
    });
    instance.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
    if (import.meta.env.DEV) (window as unknown as { __ladewuesteMap?: maplibregl.Map }).__ladewuesteMap = instance; // for screenshot scripts
    const overlay = new MapboxOverlay({ interleaved: true, layers: [], getTooltip: tooltipFor });
    instance.addControl(overlay);
    overlayRef.current = overlay;
    instance.on("load", () => setMap(instance));
    return () => {
      overlayRef.current = null;
      instance.remove();
    };
  }, []);

  // Keyboard: Esc closes the panel; P toggles play mode; in play mode Enter drops a site at the
  // crosshair (map centre) and Backspace undoes. Ignored while typing in a field or on a button.
  const gameRef = useRef(game);
  gameRef.current = game;
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelected(null);
      if (event.metaKey || event.ctrlKey || event.altKey || isTypingTarget(event.target)) return;
      const current = gameRef.current;
      if (event.key === "p" || event.key === "P") {
        current.setActive(!current.active);
      } else if (current.active && event.key === "Enter" && map) {
        const centre = map.getCenter();
        current.drop({ lat: centre.lat, lon: centre.lng });
      } else if (current.active && event.key === "Backspace") {
        event.preventDefault();
        current.undo();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [map]);

  // In play mode a click anywhere on the map drops a site; the side panel stays closed.
  useEffect(() => {
    if (!map || !playing) return;
    setSelected(null);
    const onClick = (event: maplibregl.MapMouseEvent) => {
      const site: Site = { lat: event.lngLat.lat, lon: event.lngLat.lng };
      gameRef.current.drop(site);
    };
    map.on("click", onClick);
    map.getCanvas().style.cursor = "crosshair";
    return () => {
      map.off("click", onClick);
      map.getCanvas().style.cursor = "";
    };
  }, [map, playing]);

  const zoom = view?.zoom ?? GERMANY_VIEW.zoom;
  const useDetail = showDetail && detail.data !== undefined && detail.data.res === resDetail;
  const visibleHexes = useDetail ? detail.data : hexes.data;

  const selectedHex = useMemo(() => {
    if (!selected) return null;
    const source = selected.res === resMap ? hexes.data : detail.data;
    return source?.hexes.find((h) => h.cell === selected.cell) ?? null;
  }, [selected, resMap, hexes.data, detail.data]);

  useEffect(() => {
    const overlay = overlayRef.current;
    if (!overlay) return;
    const hexLayer = new H3HexagonLayer<Hex>({
      id: useDetail ? "hexes-detail" : "hexes-map",
      data: visibleHexes?.hexes ?? [],
      getHexagon: (d) => d.cell,
      // Once station dots appear, the hexes lie flat and step back so the dots stay readable.
      // Play mode is a flat game board; once station dots appear the hexes also lie flat.
      extruded: !showStations && !playing,
      opacity: showStations ? 0.4 : 1,
      elevationScale: elevationScaleForZoom(zoom, GERMANY_VIEW.zoom),
      getElevation: (d) => elevation(d.hpc_kw),
      getFillColor: (d) => {
        if (!playing) return distanceColor(d.nearest_hub_km, radiusKm, d.is_desert);
        if (d.is_desert) return game.shown.covered.has(d.cell) ? GREEN : distanceColor(0, radiusKm, true);
        const [r, g, b] = distanceColor(d.nearest_hub_km, radiusKm, false);
        return [r, g, b, 45]; // covered cells fade back: the game is about the deserts
      },
      material: { ambient: 0.55, diffuse: 0.6, shininess: 24, specularColor: [60, 64, 70] },
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 70],
      onClick: (info) => {
        const hex = info.object as Hex | undefined;
        if (!playing && hex && visibleHexes) setSelected({ cell: hex.cell, res: visibleHexes.res });
      },
      updateTriggers: { getFillColor: [radiusKm, playing, game.shown.covered] },
      transitions: { getElevation: { duration: 600 }, getFillColor: { duration: 400 } },
    });
    const selectionLayer = new H3HexagonLayer<{ cell: string }>({
      id: "selection",
      data: selected ? [{ cell: selected.cell }] : [],
      getHexagon: (d) => d.cell,
      extruded: false,
      filled: false,
      stroked: true,
      getLineColor: [255, 255, 255, 230],
      lineWidthUnits: "pixels",
      getLineWidth: 2,
    });
    const stationLayer = new ScatterplotLayer<Station>({
      id: "stations",
      data: showStations ? (stations.data?.stations ?? []) : [],
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) => (d.n_hpc_points > 0 ? 6 : 4),
      radiusUnits: "pixels",
      billboard: true, // round on screen, even on a tilted map
      getFillColor: (d) => (d.n_hpc_points > 0 ? [255, 255, 255, 235] : [148, 163, 184, 200]),
      stroked: true,
      getLineColor: [11, 15, 20, 255],
      lineWidthUnits: "pixels",
      getLineWidth: 1,
      pickable: true,
      parameters: { depthCompare: "always" }, // always on top of the hexes
    });
    const pinColor = game.view === "you" ? USER_PIN : ALGORITHM_PIN;
    const sites = playing ? game.shownSites.map((site, i) => ({ ...site, rank: i + 1 })) : [];
    const ringLayer = new ScatterplotLayer<Site & { rank: number }>({
      id: `rings-${game.view}`,
      data: sites,
      getPosition: (d) => [d.lon, d.lat],
      getRadius: radiusKm * 1000, // metres: the coverage radius, true to scale
      filled: true,
      getFillColor: [74, 222, 128, 22],
      stroked: true,
      getLineColor: [74, 222, 128, 170],
      lineWidthUnits: "pixels",
      getLineWidth: 1.5,
      // A new ring grows from the pin to the full radius.
      transitions: { getRadius: { duration: 700, enter: () => [0] } },
      parameters: { depthCompare: "always" },
    });
    const pinLayer = new IconLayer<Site & { rank: number }>({
      id: `pins-${game.view}`,
      data: sites,
      getPosition: (d) => [d.lon, d.lat],
      getIcon: () => PIN_ICON,
      getSize: 30,
      sizeUnits: "pixels",
      getColor: pinColor,
      billboard: true,
      parameters: { depthCompare: "always" },
    });
    overlay.setProps({ layers: [hexLayer, selectionLayer, stationLayer, ringLayer, pinLayer] });
  }, [visibleHexes, useDetail, radiusKm, selected, showStations, stations.data, zoom, playing, game.shown, game.shownSites, game.view]);

  const national = hexes.data && !filtered ? hexes.data : undefined;
  const noMatches = hexes.data !== undefined && filtered && hexes.data.hexes.every((h) => h.n_points === 0);
  const error = config.error ?? hexes.error;

  return (
    <div className="relative h-full w-full overflow-hidden bg-ink">
      {/* MapLibre's CSS makes its container position: relative, so the sizing lives on a wrapper. */}
      <div className="absolute inset-0">
        <div ref={containerRef} className="h-full w-full" aria-label="Map of Germany's HPC charging coverage" />
      </div>

      <section
        aria-label="Map controls"
        className="absolute left-3 top-3 z-10 w-80 rounded-xl border border-line bg-panel p-4 shadow-2xl backdrop-blur-md"
      >
        <header>
          <h1 className="text-lg font-semibold tracking-tight">Ladewüste</h1>
          <p className="text-xs text-muted">Where Germany runs out of fast chargers</p>
        </header>
        <div className="mt-3">
          <PlaySwitch game={game} />
        </div>
        {playing ? (
          <div className="mt-4 space-y-4">
            <DesertCounter game={game} />
            <div className="h-px bg-line" />
            <PlayControls game={game} planReady={plan.data !== undefined} />
          </div>
        ) : (
        <>
        <div>
          <div className="mt-4 text-[11px] font-medium uppercase tracking-wider text-muted">Charging desert</div>
          <div className="mt-0.5 flex items-baseline gap-2 whitespace-nowrap" aria-live="polite">
            <span className="text-3xl font-semibold tabular-nums text-sand">
              {hexes.data ? formatKm2(hexes.data.desert_km2) : "–"}
            </span>
            <span className="text-sm text-muted">
              {hexes.data
                ? `${formatPercent(hexes.data.desert_km2, hexes.data.total_km2)} of Germany`
                : hexes.error
                  ? "unavailable"
                  : "loading"}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted">
            more than {radiusKm} km from an HPC hub
            {national ? ` · ${formatCount(national.hexes.filter((h) => h.is_desert).length)} of ${formatCount(national.hexes.length)} cells` : ""}
          </p>
        </div>
        <div className="my-4 h-px bg-line" />
        <Filters powerClass={powerClass} onPowerClassChange={setPowerClass} operator={operator} onOperatorChange={setOperator} />
        </>
        )}
        {(hexes.isFetching || detail.isFetching) && hexes.data && (
          <div className="mt-3 h-0.5 overflow-hidden rounded bg-line" role="status" aria-label="Updating map">
            <div className="h-full w-1/3 animate-[pulse_1s_ease-in-out_infinite] bg-sand/70" />
          </div>
        )}
      </section>

      <div className="absolute bottom-8 left-3 z-10">
        <Legend radiusKm={radiusKm} showStations={showStations} playing={playing} />
      </div>

      <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center">
        <div className="pointer-events-auto">
          {error ? (
            <ErrorCard
              message={error.message}
              onRetry={() => {
                void config.refetch();
                void hexes.refetch();
              }}
            />
          ) : !hexes.data ? (
            <LoadingCard label="Loading 10,959 hexagons…" />
          ) : null}
        </div>
      </div>

      {playing && (
        // The crosshair marks where Enter drops a site (the map centre).
        <div className="pointer-events-none absolute left-1/2 top-1/2 z-10 -translate-x-1/2 -translate-y-1/2" aria-hidden>
          <div className="h-6 w-6 rounded-full border border-white/50" />
          <div className="absolute left-1/2 top-1/2 h-1 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white" />
        </div>
      )}

      {showStations && stations.data?.truncated && (
        <div role="status" className="absolute left-1/2 bottom-8 z-20 -translate-x-1/2 rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted backdrop-blur-md">
          Showing the {formatCount(stations.data.limit)} most powerful stations in view. Zoom in for all.
        </div>
      )}

      {noMatches && (
        <div role="status" className="absolute left-1/2 top-16 z-20 -translate-x-1/2 rounded-lg border border-line bg-panel px-4 py-2 text-sm backdrop-blur-md">
          No charging points match these filters.
        </div>
      )}

      <SidePanel hex={selectedHex} config={config.data} filtered={filtered} onClose={() => setSelected(null)} />

      <div className="pointer-events-none absolute bottom-1.5 left-3 z-10">
        <Footer config={config.data} />
      </div>
    </div>
  );
}
