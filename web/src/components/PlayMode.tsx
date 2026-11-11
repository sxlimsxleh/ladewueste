import { Gamepad2, RotateCcw, Sparkles, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";
import type { PlanView, PlayGame } from "@/lib/usePlayGame";

/** The play-mode switch. Always visible; keyboard shortcut P. */
export function PlaySwitch({ game }: { game: PlayGame }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={game.active}
      onClick={() => game.setActive(!game.active)}
      className={cn(
        "flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium ring-1 transition-colors",
        game.active ? "bg-emerald-400/10 text-emerald-200 ring-emerald-400/40" : "bg-white/[0.03] text-fg ring-line hover:bg-white/[0.06]",
      )}
    >
      <span className="flex items-center gap-2">
        <Gamepad2 className="h-4 w-4" aria-hidden />
        Play mode
        <kbd className="rounded border border-line px-1 text-[10px] font-normal text-muted">P</kbd>
      </span>
      <span className={cn("relative h-5 w-9 rounded-full transition-colors", game.active ? "bg-emerald-400" : "bg-white/15")} aria-hidden>
        <span className={cn("absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform", game.active ? "translate-x-4" : "translate-x-0.5")} />
      </span>
    </button>
  );
}

/** Controls while playing: progress, undo, reset, auto-plan, and which plan is on screen. */
export function PlayControls({ game, planReady }: { game: PlayGame; planReady: boolean }) {
  const placed = game.userSites.length;
  return (
    <div className="space-y-3">
      <p className="text-xs leading-relaxed text-muted">
        Click the map to drop an HPC hub, or press <kbd className="rounded border border-line px-1 text-[10px]">Enter</kbd> to
        drop one at the crosshair (arrow keys move the map). Desert cells within its radius turn green.
      </p>
      <div className="flex items-center gap-1.5" aria-label={`${placed} of ${game.budget} sites placed`}>
        {Array.from({ length: game.budget }, (_, i) => (
          <span key={i} className={cn("h-1.5 flex-1 rounded-full transition-colors", i < placed ? "bg-emerald-400" : "bg-white/10")} />
        ))}
      </div>
      <div className="flex gap-1.5">
        <Button variant="outline" size="sm" onClick={game.undo} disabled={placed === 0} aria-keyshortcuts="Backspace">
          <Undo2 className="h-3.5 w-3.5" aria-hidden /> Undo
        </Button>
        <Button variant="outline" size="sm" onClick={game.reset} disabled={placed === 0 && game.algorithmSites.length === 0}>
          <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Reset
        </Button>
        <Button size="sm" className="flex-1" onClick={game.autoPlan} aria-label={`Auto-plan ${game.budget} sites with the greedy algorithm`} disabled={!planReady || game.autoPlanning}>
          <Sparkles className="h-3.5 w-3.5" aria-hidden />
          {game.autoPlanning ? "Planning…" : `Auto-plan ${game.budget}`}
        </Button>
      </div>
      <div>
        <div id="plan-view-label" className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted">
          Show on map
        </div>
        <ToggleGroup type="single" value={game.view} onValueChange={(v) => v && game.setView(v as PlanView)} aria-labelledby="plan-view-label">
          <ToggleGroupItem value="you">Your plan ({placed})</ToggleGroupItem>
          <ToggleGroupItem value="algorithm" disabled={game.algorithmSites.length === 0}>
            Algorithm ({game.algorithmSites.length})
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
    </div>
  );
}
