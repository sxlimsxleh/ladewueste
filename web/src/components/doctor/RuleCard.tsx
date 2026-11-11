import { ArrowDown, CheckCircle2, Flag, Wrench } from "lucide-react";
import type { QualityReport } from "@/lib/api";
import { formatCount } from "@/lib/scales";
import { showInvisibles } from "@/lib/text";
import { cn } from "@/lib/utils";

type Rule = QualityReport["rules"][number];
// The example action is a literal union in the schema; `actions` is a plain string-keyed map.
type Action = Rule["examples"][number]["action"];

/** Actions carry an icon and a word, never colour alone. */
const ACTION_STYLE: Record<Action, { label: string; icon: typeof Flag; className: string }> = {
  fixed: { label: "fixed", icon: Wrench, className: "bg-teal/10 text-teal ring-teal/30" },
  flagged: { label: "flagged", icon: Flag, className: "bg-sand/10 text-sand ring-sand/40" },
  accepted: { label: "accepted", icon: CheckCircle2, className: "bg-white/5 text-muted ring-line" },
};

export function ActionChip({ action, count }: { action: Action; count?: number }) {
  const { label, icon: Icon, className } = ACTION_STYLE[action];
  return (
    <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1", className)}>
      <Icon className="h-3 w-3" aria-hidden />
      {count !== undefined && <span className="tabular-nums">{formatCount(count)}</span>} {label}
    </span>
  );
}

export function RuleCard({ rule }: { rule: Rule }) {
  const actions = (Object.entries(rule.actions) as [Action, number][]).filter(([, n]) => n > 0);
  return (
    <article id={`rule-${rule.rule_id}`} className="flex flex-col rounded-xl border border-line bg-panel-solid p-4" aria-labelledby={`rule-${rule.rule_id}-title`}>
      <header className="flex items-start justify-between gap-3">
        <div>
          <span className="font-mono text-[11px] text-muted">{rule.rule_id}</span>
          <h3 id={`rule-${rule.rule_id}-title`} className="text-sm font-semibold leading-snug">
            {rule.title}
          </h3>
        </div>
        <div className="text-right">
          <div className="text-xl font-semibold tabular-nums">{formatCount(rule.rows_affected)}</div>
          <div className="text-[11px] text-muted">records</div>
        </div>
      </header>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {actions.map(([action, n]) => (
          <ActionChip key={action} action={action} count={n} />
        ))}
      </div>
      <p className="mt-3 text-xs leading-relaxed text-muted">{rule.why}</p>

      <ol className="mt-3 space-y-2" aria-label="Examples">
        {rule.examples.map((example, i) => (
          <li key={i} className="rounded-lg bg-black/25 p-2.5 ring-1 ring-line">
            <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider text-muted">
              <span>
                Station {example.station_id ?? "–"}
                {example.point_no ? ` · point ${example.point_no}` : ""}
              </span>
              <ActionChip action={example.action} />
            </div>
            <div className="break-all font-mono text-xs text-muted">
              <span className="sr-only">Before: </span>
              {showInvisibles(example.before)}
            </div>
            <ArrowDown className="my-0.5 h-3 w-3 text-muted" aria-hidden />
            <div className="break-all font-mono text-xs text-fg">
              <span className="sr-only">After: </span>
              {showInvisibles(example.after)}
            </div>
          </li>
        ))}
      </ol>
      <footer className="mt-auto pt-3 font-mono text-[10px] text-muted">dbt model: {rule.model}</footer>
    </article>
  );
}
