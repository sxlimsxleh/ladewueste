import type { QualityReport } from "@/lib/api";
import { formatCount, formatPercent } from "@/lib/scales";

interface Step {
  label: string;
  value: number;
  note?: string;
}

/**
 * One funnel as horizontal bars: a single hue (magnitude, not identity), every bar labelled with
 * its exact value, so the bars are readable without colour and double as the table view.
 */
function FunnelGroup({ title, steps }: { title: string; steps: Step[] }) {
  const max = Math.max(...steps.map((s) => s.value), 1);
  return (
    <figure className="rounded-xl border border-line bg-panel-solid p-4">
      <figcaption className="text-[11px] font-medium uppercase tracking-wider text-muted">{title}</figcaption>
      <ol className="mt-3 space-y-3">
        {steps.map((step, i) => {
          const previous = steps[i - 1];
          const share = previous ? formatPercent(step.value, previous.value) : null;
          return (
            <li key={step.label} title={`${step.label}: ${formatCount(step.value)}${share ? ` (${share} of previous step)` : ""}`}>
              <div className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-fg">{step.label}</span>
                <span className="tabular-nums text-fg">
                  {formatCount(step.value)}
                  {share && <span className="ml-1.5 text-xs text-muted">{share}</span>}
                </span>
              </div>
              <div className="mt-1 h-2 rounded-[4px] bg-white/[0.04]">
                <div className="h-full rounded-[4px] bg-sand/85" style={{ width: `${(100 * step.value) / max}%` }} />
              </div>
              {step.note && <div className="mt-1 text-xs text-muted">{step.note}</div>}
            </li>
          );
        })}
      </ol>
    </figure>
  );
}

export function Funnel({ report }: { report: QualityReport }) {
  const f = report.funnel;
  const excluded = f.stations - f.stations_usable;
  const reasons = f.excluded_by_reason;
  const maxReason = Math.max(...reasons.map((r) => r.count), 1);

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <div className="space-y-4 lg:col-span-2">
        <FunnelGroup
          title="Register records → stations"
          steps={[
            { label: "Raw records in the CSV", value: f.raw_records },
            { label: "Stations after cleaning", value: f.stations, note: "Nothing is dropped: problems are fixed or flagged." },
            { label: "Usable for the coverage model", value: f.stations_usable },
          ]}
        />
        <FunnelGroup
          title="Charging points"
          steps={[
            { label: "Charging points (unpivoted)", value: f.charging_points },
            { label: "At usable stations", value: f.charging_points_usable },
            { label: "HPC points (≥ 150 kW) at usable stations", value: f.hpc_points_usable },
          ]}
        />
      </div>

      <div className="space-y-4">
        <figure className="rounded-xl border border-line bg-panel-solid p-4">
          <figcaption className="text-[11px] font-medium uppercase tracking-wider text-muted">
            Why {formatCount(excluded)} stations are not usable
          </figcaption>
          <ul className="mt-3 space-y-3">
            {reasons.map((r) => (
              <li key={r.reason_id} title={`${r.label}: ${formatCount(r.count)} stations`}>
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span>{r.label}</span>
                  <span className="tabular-nums">{formatCount(r.count)}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-[4px] bg-white/[0.04]">
                  <div className="h-full rounded-[4px] bg-muted/70" style={{ width: `${(100 * r.count) / maxReason}%` }} />
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-muted">
            Each station is counted once, under the first reason that applies. They stay in the data, flagged.
          </p>
        </figure>
        <figure className="rounded-xl border border-line bg-panel-solid p-4">
          <figcaption className="text-[11px] font-medium uppercase tracking-wider text-muted">Operators</figcaption>
          <div className="mt-2 flex items-baseline gap-2 tabular-nums">
            <span className="text-2xl font-semibold">{formatCount(f.operators_as_registered)}</span>
            <span className="text-sm text-muted">spellings →</span>
            <span className="text-2xl font-semibold text-sand">{formatCount(f.operators_canonical)}</span>
            <span className="text-sm text-muted">operators</span>
          </div>
          <p className="mt-1 text-xs text-muted">Among usable stations, after merging spelling variants and approved merges.</p>
        </figure>
      </div>
    </div>
  );
}
