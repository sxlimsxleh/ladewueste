// Client-side coverage, the same rule as pipeline/geo.py plan_sites:
// a desert cell is covered by a site when the cell's centre is within radiusKm (great-circle).
// gridDisk only finds the candidate cells quickly; the distance test decides.
import { cellToLatLng, getHexagonEdgeLengthAvg, greatCircleDistance, gridDisk, latLngToCell, UNITS } from "h3-js";

export interface Site {
  lat: number;
  lon: number;
}

/** Desert cells of the board: H3 index -> area in km². */
export type DesertCells = ReadonlyMap<string, number>;

/**
 * How many rings gridDisk needs so that no cell centre within radiusKm is missed.
 * Neighbouring centres are about sqrt(3) x edge length apart; cells vary in size over the globe,
 * so the spacing is taken 20% smaller than average and one extra ring is added as margin.
 */
export function ringsFor(radiusKm: number, res: number): number {
  const spacingKm = Math.sqrt(3) * getHexagonEdgeLengthAvg(res, UNITS.km) * 0.8;
  return Math.ceil(radiusKm / spacingKm) + 1;
}

/** Desert cells whose centre lies within radiusKm of the site. */
export function coveredBy(site: Site, radiusKm: number, desert: DesertCells, res: number): string[] {
  const origin = latLngToCell(site.lat, site.lon, res);
  return gridDisk(origin, ringsFor(radiusKm, res)).filter(
    (cell) =>
      desert.has(cell) && greatCircleDistance([site.lat, site.lon], cellToLatLng(cell), UNITS.km) <= radiusKm,
  );
}

export interface CoverageResult {
  covered: Set<string>;
  /** Newly covered desert km² per site, in the order the sites were placed (overlap counted once). */
  removedKm2: number[];
  totalKm2: number;
  remainingKm2: number;
}

/** Coverage of a list of sites, computed from scratch: cheap for 10 sites, and makes undo trivial. */
export function applySites(sites: readonly Site[], radiusKm: number, desert: DesertCells, res: number): CoverageResult {
  const covered = new Set<string>();
  const removedKm2: number[] = [];
  for (const site of sites) {
    let removed = 0;
    for (const cell of coveredBy(site, radiusKm, desert, res)) {
      if (!covered.has(cell)) {
        covered.add(cell);
        removed += desert.get(cell) ?? 0;
      }
    }
    removedKm2.push(removed);
  }
  const totalKm2 = [...desert.values()].reduce((a, b) => a + b, 0);
  const removed = removedKm2.reduce((a, b) => a + b, 0);
  return { covered, removedKm2, totalKm2, remainingKm2: totalKm2 - removed };
}

/** Desert km² removed by the first k sites. */
export function removedByFirst(result: CoverageResult, k: number): number {
  return result.removedKm2.slice(0, k).reduce((a, b) => a + b, 0);
}
