import type { Map as MaplibreMap } from "maplibre-gl";
import { useEffect, useState } from "react";
import { bboxParam } from "./scales";

export interface MapView {
  zoom: number;
  bbox: string; // padded "min_lon,min_lat,max_lon,max_lat" for API queries
}

/** Zoom and visible box, updated when the user stops moving the map (not on every frame). */
export function useMapView(map: MaplibreMap | null): MapView | null {
  const [view, setView] = useState<MapView | null>(null);
  useEffect(() => {
    if (!map) return;
    const update = () => {
      const b = map.getBounds();
      setView({ zoom: map.getZoom(), bbox: bboxParam(b.getWest(), b.getSouth(), b.getEast(), b.getNorth()) });
    };
    update();
    map.on("moveend", update);
    return () => {
      map.off("moveend", update);
    };
  }, [map]);
  return view;
}
