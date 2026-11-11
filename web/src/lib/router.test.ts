import { describe, expect, it } from "vitest";
import { hrefFor, parseRoute } from "./router";

describe("parseRoute", () => {
  it("maps hashes to pages, defaulting to the map", () => {
    expect(parseRoute("")).toBe("map");
    expect(parseRoute("#/")).toBe("map");
    expect(parseRoute("#/doctor")).toBe("doctor");
    expect(parseRoute("#doctor")).toBe("doctor");
    expect(parseRoute("#/doctor?rule=R09")).toBe("doctor");
    expect(parseRoute("#/nonsense")).toBe("map");
  });
  it("round-trips with hrefFor", () => {
    expect(parseRoute(hrefFor("doctor"))).toBe("doctor");
    expect(parseRoute(hrefFor("map"))).toBe("map");
  });
});
