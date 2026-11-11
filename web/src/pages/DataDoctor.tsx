import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import { useState } from "react";
import { Footer } from "@/components/Footer";
import { Funnel } from "@/components/doctor/Funnel";
import { MergeTable } from "@/components/doctor/MergeTable";
import { RuleCard } from "@/components/doctor/RuleCard";
import { ErrorCard } from "@/components/StatusCard";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { api } from "@/lib/api";
import { registerDate } from "@/lib/scales";

const MESS_REPORT_URL = "https://github.com/sxlimsxleh/ladewueste/blob/main/docs/mess_report.md";
type RuleFilter = "all" | "fixed" | "flagged";

function Section({ id, title, intro, children }: { id: string; title: string; intro: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={id} className="mt-10 scroll-mt-20">
      <h2 id={id} className="text-lg font-semibold">
        {title}
      </h2>
      <p className="mt-1 max-w-3xl text-sm text-muted">{intro}</p>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Skeleton() {
  return (
    <div className="mt-8 animate-pulse space-y-4" role="status" aria-label="Loading the quality report">
      <div className="h-40 rounded-xl bg-white/[0.04]" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="h-72 rounded-xl bg-white/[0.04]" />
        ))}
      </div>
    </div>
  );
}

export function DataDoctor() {
  const quality = useQuery({ queryKey: ["quality"], queryFn: api.quality });
  const config = useQuery({ queryKey: ["config"], queryFn: api.config });
  const [filter, setFilter] = useState<RuleFilter>("all");
  const report = quality.data;
  const rules = (report?.rules ?? []).filter((r) => filter === "all" || (r.actions[filter] ?? 0) > 0);
  const date = registerDate(report?.source.file);

  return (
    <main className="mx-auto max-w-7xl px-6 pb-16 pt-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Data Doctor</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted">
            Every fix the pipeline makes to the Bundesnetzagentur's charging register, with counts and real examples.
            Problems are fixed when that is safe and flagged otherwise; no record is silently dropped.
          </p>
        </div>
        {report && (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-xs text-muted">
            <dt>Source</dt>
            <dd className="text-fg">
              Ladesäulenregister{date ? `, as of ${date}` : ""} ({report.source.licence}, {report.source.attribution})
            </dd>
            <dt>SHA-256</dt>
            <dd className="font-mono" title={report.source.sha256 ?? ""}>
              {report.source.sha256?.slice(0, 16) ?? "–"}…
            </dd>
            <dt>Built</dt>
            <dd>{new Date(report.generated_at).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</dd>
            <dt>Profile</dt>
            <dd>
              <a className="inline-flex items-center gap-1 text-fg underline decoration-line underline-offset-2 hover:text-sand" href={MESS_REPORT_URL} target="_blank" rel="noreferrer">
                Full mess report <ExternalLink className="h-3 w-3" aria-hidden />
              </a>
            </dd>
          </dl>
        )}
      </header>

      {quality.error ? (
        <div className="mt-10 flex justify-center">
          <ErrorCard message={quality.error.message} onRetry={() => void quality.refetch()} />
        </div>
      ) : !report ? (
        <Skeleton />
      ) : (
        <>
          <Section id="funnel" title="From raw records to a usable map" intro="How many records survive each step, and why some stations are kept out of the coverage model.">
            <Funnel report={report} />
          </Section>

          <Section
            id="rules"
            title={`${report.rules.length} cleaning rules`}
            intro="Each rule is a dbt model with its own test. Counts are register records; the examples are the first rows with different outcomes."
          >
            <ToggleGroup
              type="single"
              value={filter}
              onValueChange={(v) => v && setFilter(v as RuleFilter)}
              aria-label="Show rules"
              className="mb-4 w-auto"
            >
              <ToggleGroupItem value="all" className="px-4">All</ToggleGroupItem>
              <ToggleGroupItem value="fixed" className="px-4">Fixed</ToggleGroupItem>
              <ToggleGroupItem value="flagged" className="px-4">Flagged</ToggleGroupItem>
            </ToggleGroup>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {rules.map((rule) => (
                <RuleCard key={rule.rule_id} rule={rule} />
              ))}
            </div>
          </Section>

          <Section
            id="operators"
            title="Operator merges"
            intro={`${report.operator_merges.length} ways the register spells one operator differently, and what the pipeline did about it.`}
          >
            <MergeTable merges={report.operator_merges} />
          </Section>
        </>
      )}

      <div className="mt-12">
        <Footer config={config.data} />
      </div>
    </main>
  );
}
