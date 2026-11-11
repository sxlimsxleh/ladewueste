// Pure functions that turn data into colours, heights and text. Unit-tested in scales.test.ts.

export type RGB = [number, number, number];
export type RGBA = [number, number, number, number];

/** Covered cells: teal right next to a hub, cooling to indigo at the desert radius. */
const COVERED_STOPS: ReadonlyArray<{ at: number; color: RGB }> = [
  { at: 0, color: [94, 234, 212] }, // teal
  { at: 0.4, color: [56, 189, 248] }, // sky
  { at: 1, color: [99, 102, 241] }, // indigo
];
/** Desert cells stand out in warm sand against the cool covered cells and the dark map. */
export const SAND: RGB = [232, 190, 120];
export const COVERED_ALPHA = 150;
export const DESERT_ALPHA = 235;

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Colour for a cell from its distance to the nearest hub. */
export function distanceColor(nearestHubKm: number, radiusKm: number, isDesert: boolean): RGBA {
  if (isDesert) return [...SAND, DESERT_ALPHA];
  const t = Math.min(Math.max(nearestHubKm / radiusKm, 0), 1);
  for (let i = 1; i < COVERED_STOPS.length; i++) {
    const lo = COVERED_STOPS[i - 1]!;
    const hi = COVERED_STOPS[i]!;
    if (t <= hi.at) {
      const local = (t - lo.at) / (hi.at - lo.at);
      return [
        Math.round(lerp(lo.color[0], hi.color[0], local)),
        Math.round(lerp(lo.color[1], hi.color[1], local)),
        Math.round(lerp(lo.color[2], hi.color[2], local)),
        COVERED_ALPHA,
      ];
    }
  }
  return [...COVERED_STOPS[COVERED_STOPS.length - 1]!.color, COVERED_ALPHA];
}

/** CSS gradient matching distanceColor, for the legend. */
export function legendGradient(): string {
  const stops = COVERED_STOPS.map((s) => `rgb(${s.color.join(",")}) ${s.at * 100}%`);
  return `linear-gradient(to right, ${stops.join(", ")})`;
}

/** Metres of extrusion per sqrt(kW). A square-root scale keeps big cities from dwarfing the rest. */
export const ELEVATION_PER_SQRT_KW = 250;

export function elevation(hpcKw: number): number {
  return Math.sqrt(Math.max(hpcKw, 0)) * ELEVATION_PER_SQRT_KW;
}

/**
 * Heights are in metres, but one metre covers twice as many pixels per zoom level. Without
 * correction a column that reads well over all of Germany becomes a wall when zoomed into a city.
 * Scaling by 2^(baseZoom - zoom) keeps columns about the same height on screen at every zoom.
 */
export function elevationScaleForZoom(zoom: number, baseZoom: number): number {
  return Math.min(1, 2 ** (baseZoom - zoom));
}

const integer = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

export function formatKm2(km2: number): string {
  return `${integer.format(km2)} km²`;
}

export function formatKm(km: number): string {
  return `${oneDecimal.format(km)} km`;
}

export function formatKw(kw: number): string {
  return kw >= 1000 ? `${oneDecimal.format(kw / 1000)} MW` : `${integer.format(kw)} kW`;
}

export function formatCount(n: number): string {
  return integer.format(n);
}

export function formatPercent(part: number, whole: number): string {
  return whole > 0 ? `${oneDecimal.format((100 * part) / whole)}%` : "–";
}

/** "min_lon,min_lat,max_lon,max_lat", padded by a fraction of its size so panning doesn't refetch at once. */
export function bboxParam(
  west: number,
  south: number,
  east: number,
  north: number,
  pad = 0.15,
): string {
  const dx = (east - west) * pad;
  const dy = (north - south) * pad;
  const clamp = (v: number, lim: number) => Math.min(Math.max(v, -lim), lim);
  return [clamp(west - dx, 180), clamp(south - dy, 90), clamp(east + dx, 180), clamp(north + dy, 90)]
    .map((v) => v.toFixed(3))
    .join(",");
}

/** Power classes for the filter. minKw null = all points. */
export const POWER_CLASSES = [
  { id: "all", label: "All", minKw: null },
  { id: "50", label: "50+", minKw: 50 },
  { id: "150", label: "150+", minKw: 150 },
  { id: "300", label: "300+", minKw: 300 },
] as const;

export type PowerClassId = (typeof POWER_CLASSES)[number]["id"];

/** "Ladesaeulenregister_BNetzA_2026-09-01.csv" -> "01.09.2026" (German date, as the register writes it). */
export function registerDate(file: string | null | undefined): string | null {
  const match = file?.match(/(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[3]}.${match[2]}.${match[1]}` : null;
}
