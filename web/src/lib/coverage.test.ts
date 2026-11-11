import { cellArea, cellToLatLng, greatCircleDistance, gridDisk, latLngToCell, UNITS } from "h3-js";
import { describe, expect, it } from "vitest";
import { applySites, coveredBy, type DesertCells, removedByFirst, ringsFor } from "./coverage";

const RES = 6;
const CENTRE = latLngToCell(52.0, 10.0, RES);

/** A board where every cell within 12 rings of the centre is desert. */
function board(): DesertCells {
  return new Map(gridDisk(CENTRE, 12).map((c) => [c, cellArea(c, UNITS.km2)]));
}

describe("coveredBy", () => {
  it("covers exactly the desert cells whose centre is within the radius", () => {
    const desert = board();
    const site = { lat: 52.03, lon: 10.05 };
    const got = new Set(coveredBy(site, 25, desert, RES));
    // Brute force over the whole board, no gridDisk shortcut.
    const expected = [...desert.keys()].filter(
      (c) => greatCircleDistance([site.lat, site.lon], cellToLatLng(c), UNITS.km) <= 25,
    );
    expect(got).toEqual(new Set(expected));
    expect(got.size).toBeGreaterThan(40);
  });

  it("uses enough rings to reach the radius", () => {
    // At res 6 neighbouring centres are ~6.4 km apart: 25 km needs ~4 rings, plus margin.
    expect(ringsFor(25, RES)).toBeGreaterThanOrEqual(5);
  });

  it("ignores cells that are not desert", () => {
    expect(coveredBy({ lat: 52, lon: 10 }, 25, new Map(), RES)).toEqual([]);
  });
});

describe("applySites", () => {
  it("counts overlapping coverage once", () => {
    const desert = board();
    const site = { lat: 52, lon: 10 };
    const result = applySites([site, site], 25, desert, RES);
    expect(result.removedKm2[1]).toBe(0);
    expect(result.remainingKm2).toBeCloseTo(result.totalKm2 - result.removedKm2[0]!, 6);
  });

  it("is order-independent in total and undo is just a shorter list", () => {
    const desert = board();
    const a = { lat: 52.0, lon: 9.8 };
    const b = { lat: 52.1, lon: 10.3 };
    const ab = applySites([a, b], 25, desert, RES);
    const ba = applySites([b, a], 25, desert, RES);
    expect(ab.remainingKm2).toBeCloseTo(ba.remainingKm2, 6);
    expect(applySites([a], 25, desert, RES).remainingKm2).toBeCloseTo(ab.totalKm2 - ab.removedKm2[0]!, 6);
    expect(removedByFirst(ab, 1)).toBe(ab.removedKm2[0]);
  });
});
