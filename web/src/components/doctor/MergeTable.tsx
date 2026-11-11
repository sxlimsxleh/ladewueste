import { Check, Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { QualityReport } from "@/lib/api";
import { formatCount } from "@/lib/scales";
import { cn } from "@/lib/utils";

type Merge = QualityReport["operator_merges"][number];

const REASON_LABEL: Record<string, string> = {
  spelling: "Spelling (R07)",
  legal_form: "Legal form (R08)",
  fuzzy: "Similar name (R08)",
};

export function MergeTable({ merges }: { merges: Merge[] }) {
  const [query, setQuery] = useState("");
  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return q ? merges.filter((m) => `${m.from_name} ${m.to_name}`.toLowerCase().includes(q)) : merges;
  }, [merges, query]);
  const pending = merges.filter((m) => !m.applied).length;

  return (
    <div className="rounded-xl border border-line bg-panel-solid">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line p-4">
        <p className="max-w-2xl text-xs leading-relaxed text-muted">
          Spelling variants are merged automatically. Names that differ by legal form or look similar are only{" "}
          <em>suggested</em>: {formatCount(pending)} wait for a person. To approve one, add a line to{" "}
          <code className="rounded bg-black/30 px-1 text-fg">pipeline/dbt/seeds/operator_overrides.csv</code> and run{" "}
          <code className="rounded bg-black/30 px-1 text-fg">make pipeline</code>.
        </p>
        <label className="relative">
          <span className="sr-only">Search operator merges</span>
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" aria-hidden />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search operators…"
            className="h-9 w-64 rounded-md border border-line bg-black/30 pl-8 pr-2.5 text-sm text-fg placeholder:text-muted outline-none focus:border-accent"
          />
        </label>
      </div>
      <div className="max-h-[28rem] overflow-y-auto">
        <table className="w-full text-left text-sm">
          <caption className="sr-only">Operator merges: automatic and suggested</caption>
          <thead className="sticky top-0 bg-panel-solid text-[11px] uppercase tracking-wider text-muted">
            <tr className="border-b border-line">
              <th scope="col" className="px-4 py-2 font-medium">From</th>
              <th scope="col" className="px-4 py-2 font-medium">To</th>
              <th scope="col" className="px-4 py-2 font-medium">Why</th>
              <th scope="col" className="px-4 py-2 text-right font-medium">Score</th>
              <th scope="col" className="px-4 py-2 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((m) => (
              <tr key={`${m.kind}-${m.from_name}-${m.to_name}`} className="border-b border-line/60 last:border-0 hover:bg-white/[0.02]">
                <td className="px-4 py-2">
                  {m.from_name} <span className="text-xs text-muted tabular-nums">({formatCount(m.from_records)})</span>
                </td>
                <td className="px-4 py-2">
                  {m.to_name}
                  {m.to_records !== null && <span className="text-xs text-muted tabular-nums"> ({formatCount(m.to_records)})</span>}
                </td>
                <td className="px-4 py-2 text-xs text-muted">{REASON_LABEL[m.reason] ?? m.reason}</td>
                <td className="px-4 py-2 text-right text-xs tabular-nums text-muted">{m.score ?? "–"}</td>
                <td className="px-4 py-2">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1",
                      m.applied ? "bg-teal/10 text-teal ring-teal/30" : "bg-white/5 text-muted ring-line",
                    )}
                  >
                    {m.applied && <Check className="h-3 w-3" aria-hidden />}
                    {m.applied ? (m.kind === "automatic" ? "merged" : "approved") : "needs review"}
                  </span>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-sm text-muted">
                  No merge involves “{query}”.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
