// A two-page hash router: "#/" is the map, "#/doctor" the Data Doctor. Hash URLs work on any
// static host without server rewrites, and two pages don't justify a routing library.
import { useSyncExternalStore } from "react";

export type Route = "map" | "doctor";

export function parseRoute(hash: string): Route {
  return hash.replace(/^#\/?/, "").split(/[?/]/)[0] === "doctor" ? "doctor" : "map";
}

export function hrefFor(route: Route): string {
  return route === "doctor" ? "#/doctor" : "#/";
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

export function useRoute(): Route {
  return useSyncExternalStore(subscribe, () => parseRoute(window.location.hash));
}
