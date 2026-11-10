import { H3HexagonLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { MapboxOverlay } from "@deck.gl/mapbox";
import type { PickingInfo } from "@deck.gl/core";
import { useQuery } from "@tanstack/react-query";
import maplibregl from "maplibre-gl";
import { useEffect, useMemo, useRef, useState } from "react";
import { Filters } from "@/components/Filters";
import { Footer } from "@/components/Footer";
import { Legend } from "@/components/Legend";
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
import { useMapView } from "@/lib/useMapView";

const BASEMAP_STYLE = "https://tiles.openfreemap.org/styles/dark";
const GERMANY_VIEW = { center: [10.45, 51.15] as [number, number], zoom: 5.35, pitch: 45, bearing: -8 };
/** Zoom levels where the map switches to the detail resolution and starts showing stations. */
const DETAIL_ZOOM = 9;
const STATIONS_ZOOM = 11;

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

  const showDetail = (view?.zoom ?? 0) >= DETAIL_ZOOM;
  const detail = useQuery({
    queryKey: ["hexes", resDetail, minKw, operator, view?.bbox],
    queryFn: () => api.hexes({ res: resDetail!, min_kw: minKw, operator, bbox: view!.bbox }),
    enabled: showDetail && resDetail !== undefined && view !== null,
    placeholderData: (previous) => previous,
  });

  const showStations = (view?.zoom ?? 0) >= STATIONS_ZOOM;
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

  // Esc closes the side panel from anywhere.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setSelected(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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
      extruded: !showStations,
      opacity: showStations ? 0.4 : 1,
      elevationScale: elevationScaleForZoom(zoom, GERMANY_VIEW.zoom),
      getElevation: (d) => elevation(d.hpc_kw),
      getFillColor: (d) => distanceColor(d.nearest_hub_km, radiusKm, d.is_desert),
      material: { ambient: 0.55, diffuse: 0.6, shininess: 24, specularColor: [60, 64, 70] },
      pickable: true,
      autoHighlight: true,
      highlightColor: [255, 255, 255, 70],
      onClick: (info) => {
        const hex = info.object as Hex | undefined;
        if (hex && visibleHexes) setSelected({ cell: hex.cell, res: visibleHexes.res });
      },
      updateTriggers: { getFillColor: [radiusKm] },
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
    overlay.setProps({ layers: [hexLayer, selectionLayer, stationLayer] });
  }, [visibleHexes, useDetail, radiusKm, selected, showStations, stations.data, zoom]);

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
        </header>
        <div className="my-4 h-px bg-line" />
        <Filters powerClass={powerClass} onPowerClassChange={setPowerClass} operator={operator} onOperatorChange={setOperator} />
        {(hexes.isFetching || detail.isFetching) && hexes.data && (
          <div className="mt-3 h-0.5 overflow-hidden rounded bg-line" role="status" aria-label="Updating map">
            <div className="h-full w-1/3 animate-[pulse_1s_ease-in-out_infinite] bg-sand/70" />
          </div>
        )}
      </section>

      <div className="absolute bottom-8 left-3 z-10">
        <Legend radiusKm={radiusKm} showStations={showStations} />
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

      {showStations && stations.data?.truncated && (
        <div role="status" className="absolute left-1/2 bottom-8 z-20 -translate-x-1/2 rounded-lg border border-line bg-panel px-3 py-1.5 text-xs text-muted backdrop-blur-md">
          Showing the {formatCount(stations.data.limit)} most powerful stations in view. Zoom in for all.
        </div>
      )}

      {noMatches && (
        <div role="status" className="absolute left-1/2 top-3 z-20 -translate-x-1/2 rounded-lg border border-line bg-panel px-4 py-2 text-sm backdrop-blur-md">
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
