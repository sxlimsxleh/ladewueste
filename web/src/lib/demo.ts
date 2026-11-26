// Static demo mode (VITE_DEMO=1, used for the GitHub Pages build): instead of calling the API,
// the client reads JSON files that api/export_demo.py produced from the real API. Only the
// requests the demo needs exist as files; anything else is reported as "not in the static demo".
import { POWER_CLASSES } from "./scales";

export const DEMO: boolean = import.meta.env.VITE_DEMO === "1";

/** The full app, for the "run it yourself" links in demo mode. */
export const REPO_URL = "https://github.com/sxlimsxleh/ladewueste";

type Query = Record<string, string | number | undefined | null> | undefined;

/** File name for a request, or null if the static demo cannot answer it. Mirrors export_demo.py. */
export function demoFile(path: string, query: Query): string | null {
  const q = Object.fromEntries(Object.entries(query ?? {}).filter(([, v]) => v !== undefined && v !== null));
  const keys = Object.keys(q).sort().join(",");
  if (path === "/config" && keys === "") return "config.json";
  if (path === "/quality" && keys === "") return "quality.json";
  if (path === "/plan" && keys === "n" && Number(q.n) === 10) return "plan-10.json";
  if (path === "/hexes" && (keys === "res" || keys === "min_kw,res")) {
    const minKw = q.min_kw === undefined ? null : Number(q.min_kw);
    if (!POWER_CLASSES.some((c) => c.minKw === minKw)) return null;
    return `hexes-${q.res}-${minKw ?? "all"}.json`;
  }
  return null;
}
