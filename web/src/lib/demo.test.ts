import { describe, expect, it } from "vitest";
import { demoFile } from "./demo";

describe("demoFile", () => {
  it("maps the requests the demo needs to files", () => {
    expect(demoFile("/config", undefined)).toBe("config.json");
    expect(demoFile("/quality", {})).toBe("quality.json");
    expect(demoFile("/plan", { n: 10 })).toBe("plan-10.json");
    expect(demoFile("/hexes", { res: 6, min_kw: null, operator: null })).toBe("hexes-6-all.json");
    expect(demoFile("/hexes", { res: 6, min_kw: 150, operator: undefined })).toBe("hexes-6-150.json");
  });
  it("refuses what the static demo cannot answer", () => {
    expect(demoFile("/hexes", { res: 6, operator: "Tesla Germany GmbH" })).toBeNull();
    expect(demoFile("/hexes", { res: 7, bbox: "13,52,14,53" })).toBeNull();
    expect(demoFile("/hexes", { res: 6, min_kw: 75 })).toBeNull();
    expect(demoFile("/plan", { n: 5 })).toBeNull();
    expect(demoFile("/stations", { bbox: "13,52,14,53" })).toBeNull();
  });
});
