// Typed API client. Every path, parameter and response type comes from api-types.ts,
// which is generated from the FastAPI OpenAPI schema (`make types`) - never edited by hand.
import type { components, paths } from "./api-types";

export type AppConfig = components["schemas"]["AppConfig"];
export type Hex = components["schemas"]["Hex"];
export type HexesResponse = components["schemas"]["HexesResponse"];
export type Station = components["schemas"]["Station"];
export type StationsResponse = components["schemas"]["StationsResponse"];
export type Operator = components["schemas"]["Operator"];
export type PlanResponse = components["schemas"]["PlanResponse"];
export type QualityReport = components["schemas"]["QualityReport"];

type QueryOf<P extends keyof paths> = paths[P]["get"] extends { parameters: { query?: infer Q } } ? Q : never;

export const API_BASE: string = import.meta.env?.VITE_API_BASE ?? "http://localhost:8000";

async function get<T>(path: keyof paths, query?: Record<string, string | number | undefined | null>): Promise<T> {
  const url = new URL(path, API_BASE);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
  }
  const response = await fetch(url);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
    throw new Error(typeof body.detail === "string" ? body.detail : `${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}

export const api = {
  config: () => get<AppConfig>("/config"),
  hexes: (query: QueryOf<"/hexes">) => get<HexesResponse>("/hexes", query),
  stations: (query: QueryOf<"/stations">) => get<StationsResponse>("/stations", query),
  operators: (query: QueryOf<"/operators"> = {}) => get<Operator[]>("/operators", query),
  plan: (query: QueryOf<"/plan"> = {}) => get<PlanResponse>("/plan", query),
  quality: () => get<QualityReport>("/quality"),
};
