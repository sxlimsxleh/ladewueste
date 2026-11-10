import { legendGradient } from "@/lib/scales";

export function Legend({ radiusKm, showStations }: { radiusKm: number; showStations: boolean }) {
  return (
    <div className="rounded-lg border border-line bg-panel px-3 py-2 text-[11px] text-muted backdrop-blur-md">
      <div className="mb-1 font-medium text-fg">Distance to nearest HPC hub</div>
      <div className="flex items-center gap-2">
        <div className="h-2 w-36 rounded-full" style={{ background: legendGradient() }} aria-hidden />
        <div className="h-2 w-6 rounded-full bg-sand shadow-[0_0_8px_var(--color-sand)]" aria-hidden />
      </div>
      <div className="mt-0.5 flex w-[12.5rem] justify-between tabular-nums">
        <span>0 km</span>
        <span>{radiusKm} km</span>
        <span className="text-sand">desert</span>
      </div>
      <div className="mt-1">Height: HPC power in the cell</div>
      {showStations && (
        <div className="mt-1.5 flex items-center gap-3">
          <span className="flex items-center gap-1">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-white ring-1 ring-ink" aria-hidden /> HPC station
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-slate-400 ring-1 ring-ink" aria-hidden /> other
          </span>
        </div>
      )}
    </div>
  );
}
