import { describe, expect, it } from "vitest";
import { showInvisibles } from "./text";

describe("showInvisibles", () => {
  it("marks NBSP, line breaks and tabs", () => {
    expect(showInvisibles("Eichlesstraße\u00a0")).toBe("Eichlesstraße⍽");
    expect(showInvisibles("DE*ABC*E1\r\nDE*ABC*E2\tx")).toBe("DE*ABC*E1↵DE*ABC*E2⇥x");
  });
  it("marks leading, trailing and doubled spaces but not single inner ones", () => {
    expect(showInvisibles("operator: EnBW AG ")).toBe("operator: EnBW AG␣");
    expect(showInvisibles("  Orange  Charging")).toBe("␣␣Orange␣␣Charging");
  });
  it("shows a missing value as ∅", () => {
    expect(showInvisibles(null)).toBe("∅");
  });
});
