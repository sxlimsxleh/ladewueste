// Python (pipeline/geo.py, served by /plan) and the browser (coverage.ts) must agree to the km²,
// or "you vs the algorithm" is not a fair game. Needs a running API with real data:
//   LADEWUESTE_API_URL=http://127.0.0.1:8000 npx vitest run coverage.parity   (127.0.0.1: Node resolves localhost to IPv6)
// Skipped otherwise (e.g. in CI, which has no gold data).
import { describe, expect, it } from "vitest";
import type { AppConfig, HexesResponse, PlanResponse } from "./api";
import { applySites } from "./coverage";

const API = process.env.LADEWUESTE_API_URL;

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API}${path}`);
  if (!response.ok) throw new Error(`${path}: ${response.status}`);
  return (await response.json()) as T;
}

describe.skipIf(!API)("coverage parity with the Python planner", () => {
  it("removes the same desert km² per pick as /plan", async () => {
    const config = await get<AppConfig>("/config");
    const hexes = await get<HexesResponse>(`/hexes?res=${config.h3_res_map}`);
    const plan = await get<PlanResponse>("/plan?n=10");
    const desert = new Map(hexes.hexes.filter((h) => h.is_desert).map((h) => [h.cell, h.area_km2]));

    const result = applySites(
      plan.sites.map((s) => ({ lat: s.lat, lon: s.lon })),
      plan.radius_km,
      desert,
      config.h3_res_map,
    );

    expect(result.totalKm2).toBeCloseTo(plan.desert_km2_before, 3);
    plan.sites.forEach((site, i) => {
      expect(result.removedKm2[i], `pick ${site.rank}`).toBeCloseTo(site.desert_km2_removed, 3);
    });
    expect(result.remainingKm2).toBeCloseTo(plan.desert_km2_after, 3);
  }, 30_000);
});
