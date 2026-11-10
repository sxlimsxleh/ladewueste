import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { AppConfig, Hex } from "@/lib/api";
import { cn } from "@/lib/utils";
import { formatCount, formatKm, formatKm2, formatKw } from "@/lib/scales";

interface SidePanelProps {
  hex: Hex | null;
  config: AppConfig | undefined;
  filtered: boolean;
  onClose: () => void;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.03] px-3 py-2 ring-1 ring-line">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className="mt-0.5 text-base font-semibold tabular-nums">{value}</div>
    </div>
  );
}

/** Details of the clicked cell. Slides in from the right; Esc or the close button hides it. */
export function SidePanel({ hex, config, filtered, onClose }: SidePanelProps) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const open = hex !== null;

  // Move keyboard focus into the panel when it opens, so Tab continues there.
  useEffect(() => {
    if (open) closeRef.current?.focus({ preventScroll: true });
  }, [open, hex?.cell]);

  return (
    <aside
      aria-label="Cell details"
      aria-hidden={!open}
      inert={!open}
      className={cn(
        "absolute right-3 top-3 z-20 max-h-[calc(100%-9rem)] w-80 overflow-y-auto rounded-xl border border-line bg-panel p-4 shadow-2xl backdrop-blur-md",
        "transition-[transform,opacity] duration-300 ease-out",
        open ? "translate-x-0 opacity-100" : "pointer-events-none translate-x-[110%] opacity-0",
      )}
    >
      {hex && (
        <>
          <div className="flex items-start justify-between gap-2">
            <div>
              <Badge variant={hex.is_desert ? "desert" : "covered"}>
                {hex.is_desert ? "Charging desert" : "Covered by a hub"}
              </Badge>
              <h2 className="mt-2 text-lg font-semibold">
                {formatKm(hex.nearest_hub_km)} <span className="text-sm font-normal text-muted">to the nearest HPC hub</span>
              </h2>
            </div>
            <Button ref={closeRef} variant="ghost" size="icon" onClick={onClose} aria-label="Close cell details">
              <X className="h-4 w-4" aria-hidden />
            </Button>
          </div>

          <p className="mt-1 text-xs text-muted">
            A hub is a site with at least {config?.hub_min_hpc_points ?? "–"} charging points of ≥{" "}
            {config?.hpc_threshold_kw ?? "–"} kW. Desert means no hub within {config?.desert_radius_km ?? "–"} km.
          </p>

          <div className="mt-4 grid grid-cols-2 gap-2">
            <Stat label="Nearest HPC point" value={formatKm(hex.nearest_hpc_km)} />
            <Stat label="Cell area" value={formatKm2(hex.area_km2)} />
            <Stat label="Charging points" value={formatCount(hex.n_points)} />
            <Stat label="HPC points" value={formatCount(hex.n_hpc_points)} />
            <Stat label="Total power" value={formatKw(hex.total_kw)} />
            <Stat label="HPC power" value={formatKw(hex.hpc_kw)} />
          </div>
          {filtered && <p className="mt-2 text-[11px] text-muted">Counts and power reflect the active filters.</p>}

          <h3 className="mt-5 text-[11px] font-medium uppercase tracking-wider text-muted">Top operators</h3>
          {hex.top_operators.length ? (
            <ol className="mt-2 space-y-1.5 text-sm">
              {hex.top_operators.map((op, i) => (
                <li key={op} className="flex gap-2">
                  <span className="w-4 text-muted tabular-nums">{i + 1}.</span>
                  <span>{op}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="mt-2 text-sm text-muted">No charging points in this cell.</p>
          )}

          <p className="mt-5 font-mono text-[11px] text-muted">H3 {hex.cell}</p>
        </>
      )}
    </aside>
  );
}
