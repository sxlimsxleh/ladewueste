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

export const API_BASE: string = import.meta.env.VITE_API_BASE ?? "/api";

const API_UNREACHABLE = "Can't reach the API. Start it with `make api` (port 8000), then try again.";

/** Thrown for non-2xx responses; `status` lets the UI tell "data not built" (503) from other errors. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function get<T>(path: keyof paths, query?: Record<string, string | number | undefined | null>): Promise<T> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null) params.set(key, String(value));
  }
  const url = `${API_BASE}${path}${params.size ? `?${params}` : ""}`;
  let response: Response;
  try {
    response = await fetch(url);
  } catch {
    throw new ApiError(API_UNREACHABLE, 0);
  }
  // 502/504 come from the dev proxy when nothing listens on the API port.
  if (response.status === 502 || response.status === 504) throw new ApiError(API_UNREACHABLE, response.status);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const message = typeof body.detail === "string" ? body.detail : `${response.status} ${response.statusText}`;
    throw new ApiError(message, response.status);
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
