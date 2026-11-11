import { ArrowRight } from "lucide-react";
import { formatKm2, formatPercent } from "@/lib/scales";
import { useAnimatedNumber } from "@/lib/useAnimatedNumber";
import type { PlayGame } from "@/lib/usePlayGame";

/** "Desert area: X km² -> Y km²" for the plan on screen, plus "you vs the algorithm". */
export function DesertCounter({ game }: { game: PlayGame }) {
  const remaining = useAnimatedNumber(game.shown.remainingKm2);
  const removed = game.desertKm2 - game.shown.remainingKm2;
  const planLabel = game.view === "you" ? "your plan" : "the algorithm's plan";

  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wider text-muted">Desert area · {planLabel}</div>
      <div className="mt-1 flex items-baseline gap-2 whitespace-nowrap tabular-nums">
        <span className="text-sm text-muted line-through decoration-muted/60">{formatKm2(game.desertKm2)}</span>
        <ArrowRight className="h-3.5 w-3.5 self-center text-muted" aria-hidden />
        <span className="text-3xl font-semibold text-sand">{formatKm2(remaining)}</span>
      </div>
      <div className="mt-1 text-xs text-muted" aria-live="polite">
        {removed > 0 ? (
          <>
            <span className="font-medium text-emerald-300">−{formatPercent(removed, game.desertKm2)}</span> with{" "}
            {game.shownSites.length} site{game.shownSites.length === 1 ? "" : "s"}
          </>
        ) : (
          "No sites placed yet"
        )}
      </div>
      <Score game={game} />
    </div>
  );
}

function Score({ game }: { game: PlayGame }) {
  if (!game.score) {
    return (
      <p className="mt-3 rounded-md bg-white/[0.03] px-3 py-2 text-xs text-muted ring-1 ring-line">
        Place your first site to compete with the greedy algorithm.
      </p>
    );
  }
  const { k, you, algorithm } = game.score;
  const ratio = algorithm > 0 ? you / algorithm : 1;
  const finished = k === game.budget;
  const youWidth = `${Math.min(100, (100 * you) / Math.max(you, algorithm, 1))}%`;
  const algorithmWidth = `${Math.min(100, (100 * algorithm) / Math.max(you, algorithm, 1))}%`;

  return (
    <div className="mt-3 rounded-md bg-white/[0.03] px-3 py-2.5 ring-1 ring-line" aria-live="polite">
      <div className="flex items-baseline justify-between text-xs">
        <span className="font-medium text-fg">You vs the algorithm</span>
        <span className="text-muted">with {k} site{k === 1 ? "" : "s"} each</span>
      </div>
      <Bar label="You" value={you} width={youWidth} className="bg-emerald-400" />
      <Bar label="Algorithm" value={algorithm} width={algorithmWidth} className="bg-violet-400" />
      <p className="mt-2 text-xs">
        {ratio >= 1 ? (
          <span className="font-medium text-emerald-300">
            {finished ? "You beat the algorithm!" : "You're ahead of the algorithm."}
          </span>
        ) : (
          <span className="text-muted">
            You reach <span className="font-medium text-fg">{Math.round(ratio * 100)}%</span> of the algorithm
            {finished ? ". Final score." : "."}
          </span>
        )}
      </p>
    </div>
  );
}

function Bar({ label, value, width, className }: { label: string; value: number; width: string; className: string }) {
  return (
    <div className="mt-2">
      <div className="flex justify-between text-[11px] tabular-nums text-muted">
        <span>{label}</span>
        <span>−{formatKm2(value)}</span>
      </div>
      <div className="mt-0.5 h-1.5 rounded-full bg-white/5">
        <div className={`h-full rounded-full transition-[width] duration-500 ${className}`} style={{ width }} />
      </div>
    </div>
  );
}
