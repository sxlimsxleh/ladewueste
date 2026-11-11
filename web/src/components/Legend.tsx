import { legendGradient } from "@/lib/scales";

interface LegendProps {
  radiusKm: number;
  showStations: boolean;
  playing?: boolean;
}

export function Legend({ radiusKm, showStations, playing = false }: LegendProps) {
  if (playing) return <PlayLegend radiusKm={radiusKm} />;
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

function PlayLegend({ radiusKm }: { radiusKm: number }) {
  return (
    <div className="space-y-1 rounded-lg border border-line bg-panel px-3 py-2 text-[11px] text-muted backdrop-blur-md">
      <div className="font-medium text-fg">Play mode</div>
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-4 rounded-sm bg-sand" aria-hidden /> Desert: no hub within {radiusKm} km
      </div>
      <div className="flex items-center gap-2">
        <span className="h-2.5 w-4 rounded-sm bg-emerald-400" aria-hidden /> Covered by the plan on screen
      </div>
      <div className="flex items-center gap-2">
        <span className="h-3 w-4 rounded-full border border-emerald-400/70" aria-hidden /> {radiusKm} km around each site
      </div>
      <div className="flex items-center gap-3 pt-0.5">
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-white" aria-hidden /> your site
        </span>
        <span className="flex items-center gap-1">
          <span className="h-2.5 w-2.5 rounded-full bg-violet-400" aria-hidden /> algorithm
        </span>
      </div>
    </div>
  );
}
