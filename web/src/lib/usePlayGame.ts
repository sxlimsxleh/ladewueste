import { useCallback, useEffect, useMemo, useState } from "react";
import type { Hex, PlanResponse } from "./api";
import { applySites, type CoverageResult, type DesertCells, removedByFirst, type Site } from "./coverage";

export type PlanView = "you" | "algorithm";

/** Milliseconds between two algorithm sites dropping in during "Auto-plan". */
export const AUTO_PLAN_STEP_MS = 650;

interface Options {
  hexes: Hex[] | undefined; // the map resolution, unfiltered: deserts never depend on filters
  plan: PlanResponse | undefined; // the algorithm's picks for the same budget
  radiusKm: number;
  res: number | undefined;
  budget: number;
}

export interface PlayGame {
  active: boolean;
  setActive: (active: boolean) => void;
  view: PlanView;
  setView: (view: PlanView) => void;
  userSites: Site[];
  algorithmSites: Site[]; // the ones dropped in so far
  shownSites: Site[]; // the sites of the plan on screen
  shown: CoverageResult;
  desertKm2: number;
  /** Desert km² removed by you and by the algorithm's first k picks, k = number of your sites. */
  score: { k: number; you: number; algorithm: number } | null;
  budget: number;
  autoPlanning: boolean;
  drop: (site: Site) => void;
  undo: () => void;
  reset: () => void;
  autoPlan: () => void;
}

export function usePlayGame({ hexes, plan, radiusKm, res, budget }: Options): PlayGame {
  const [active, setActive] = useState(false);
  const [view, setView] = useState<PlanView>("you");
  const [userSites, setUserSites] = useState<Site[]>([]);
  const [algorithmShown, setAlgorithmShown] = useState(0);
  const [autoPlanning, setAutoPlanning] = useState(false);

  const desert: DesertCells = useMemo(
    () => new Map((hexes ?? []).filter((h) => h.is_desert).map((h) => [h.cell, h.area_km2])),
    [hexes],
  );
  const allAlgorithmSites = useMemo(() => (plan?.sites ?? []).map((s) => ({ lat: s.lat, lon: s.lon })), [plan]);
  const algorithmSites = useMemo(() => allAlgorithmSites.slice(0, algorithmShown), [allAlgorithmSites, algorithmShown]);

  const compute = useCallback(
    (sites: Site[]) => applySites(sites, radiusKm, desert, res ?? 0),
    [radiusKm, desert, res],
  );
  const user = useMemo(() => compute(userSites), [compute, userSites]);
  const algorithmShownResult = useMemo(() => compute(algorithmSites), [compute, algorithmSites]);
  const algorithmFull = useMemo(() => compute(allAlgorithmSites), [compute, allAlgorithmSites]);

  // Auto-plan: drop the algorithm's sites one by one; the last step also ends the animation.
  useEffect(() => {
    if (!autoPlanning || algorithmShown >= allAlgorithmSites.length) return;
    const id = window.setTimeout(
      () => {
        setAlgorithmShown(algorithmShown + 1);
        if (algorithmShown + 1 >= allAlgorithmSites.length) setAutoPlanning(false);
      },
      algorithmShown === 0 ? 150 : AUTO_PLAN_STEP_MS,
    );
    return () => window.clearTimeout(id);
  }, [autoPlanning, algorithmShown, allAlgorithmSites.length]);

  const k = userSites.length;
  return {
    active,
    setActive,
    view,
    setView,
    userSites,
    algorithmSites,
    shownSites: view === "you" ? userSites : algorithmSites,
    shown: view === "you" ? user : algorithmShownResult,
    desertKm2: user.totalKm2,
    score: k > 0 && plan ? { k, you: user.totalKm2 - user.remainingKm2, algorithm: removedByFirst(algorithmFull, k) } : null,
    budget,
    autoPlanning,
    drop: (site) => {
      setView("you");
      setUserSites((sites) => (sites.length < budget ? [...sites, site] : sites));
    },
    undo: () => setUserSites((sites) => sites.slice(0, -1)),
    reset: () => {
      setUserSites([]);
      setAlgorithmShown(0);
      setAutoPlanning(false);
      setView("you");
    },
    autoPlan: () => {
      if (!plan || plan.sites.length === 0) return;
      setAlgorithmShown(0);
      setView("algorithm");
      setAutoPlanning(true);
    },
  };
}
