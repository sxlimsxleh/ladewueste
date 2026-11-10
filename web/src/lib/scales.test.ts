import { describe, expect, it } from "vitest";
import {
  bboxParam,
  COVERED_ALPHA,
  DESERT_ALPHA,
  distanceColor,
  elevation,
  elevationScaleForZoom,
  formatKm2,
  formatKw,
  formatPercent,
  registerDate,
  SAND,
} from "./scales";

describe("distanceColor", () => {
  it("is teal next to a hub and indigo at the radius", () => {
    expect(distanceColor(0, 25, false)).toEqual([94, 234, 212, COVERED_ALPHA]);
    expect(distanceColor(25, 25, false)).toEqual([99, 102, 241, COVERED_ALPHA]);
  });
  it("interpolates between stops", () => {
    expect(distanceColor(10, 25, false)).toEqual([56, 189, 248, COVERED_ALPHA]); // exactly the 0.4 stop
    const mid = distanceColor(5, 25, false); // halfway to the 0.4 stop
    expect(mid[0]).toBe(75);
  });
  it("uses sand for deserts, whatever the distance", () => {
    expect(distanceColor(3, 25, true)).toEqual([...SAND, DESERT_ALPHA]);
  });
  it("clamps distances outside 0..radius", () => {
    expect(distanceColor(99, 25, false)).toEqual(distanceColor(25, 25, false));
    expect(distanceColor(-1, 25, false)).toEqual(distanceColor(0, 25, false));
  });
});

describe("elevation", () => {
  it("grows with the square root of kW", () => {
    expect(elevation(400)).toBe(4 * elevation(25));
    expect(elevation(0)).toBe(0);
    expect(elevation(-5)).toBe(0);
  });
});

describe("elevationScaleForZoom", () => {
  it("is 1 at or below the base zoom and halves per extra zoom level", () => {
    expect(elevationScaleForZoom(5, 5.35)).toBe(1);
    expect(elevationScaleForZoom(6.35, 5.35)).toBe(0.5);
    expect(elevationScaleForZoom(8.35, 5.35)).toBe(0.125);
  });
});

describe("formatting", () => {
  it("formats areas, power and shares", () => {
    expect(formatKm2(19317.85)).toBe("19,318 km²");
    expect(formatKw(300)).toBe("300 kW");
    expect(formatKw(973350)).toBe("973.4 MW");
    expect(formatPercent(19318, 356218)).toBe("5.4%");
    expect(formatPercent(1, 0)).toBe("–");
  });
  it("reads the register date from the file name", () => {
    expect(registerDate("Ladesaeulenregister_BNetzA_2026-09-01.csv")).toBe("01.09.2026");
    expect(registerDate(null)).toBeNull();
  });
});

describe("bboxParam", () => {
  it("pads the box and clamps to valid ranges", () => {
    expect(bboxParam(10, 50, 12, 52)).toBe("9.700,49.700,12.300,52.300");
    expect(bboxParam(-180, -90, 180, 90)).toBe("-180.000,-90.000,180.000,90.000");
  });
});
