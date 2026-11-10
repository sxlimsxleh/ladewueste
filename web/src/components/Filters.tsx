import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { api } from "@/lib/api";
import { formatCount, POWER_CLASSES, type PowerClassId } from "@/lib/scales";

interface FiltersProps {
  powerClass: PowerClassId;
  onPowerClassChange: (id: PowerClassId) => void;
  operator: string | null;
  onOperatorChange: (operator: string | null) => void;
}

/** Wait until the user stops typing before searching the API. */
function useDebounced<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export function Filters({ powerClass, onPowerClassChange, operator, onOperatorChange }: FiltersProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const q = useDebounced(search.trim(), 200);
  const operators = useQuery({
    queryKey: ["operators", q],
    queryFn: () => api.operators({ q: q || null, limit: 30 }),
    enabled: open,
    placeholderData: (previous) => previous,
  });
  // cmdk highlights nothing when results arrive from the API, so Enter would do nothing.
  // Highlight the first result each time the list changes, so "type, Enter" works.
  const [highlighted, setHighlighted] = useState("");
  const first = operators.data?.[0]?.operator ?? "";
  useEffect(() => setHighlighted(first), [first]);

  return (
    <div className="space-y-3">
      <div>
        <div id="power-label" className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted">
          Charging power (kW)
        </div>
        <ToggleGroup
          type="single"
          value={powerClass}
          onValueChange={(value) => value && onPowerClassChange(value as PowerClassId)}
          aria-labelledby="power-label"
        >
          {POWER_CLASSES.map((c) => (
            <ToggleGroupItem key={c.id} value={c.id}>
              {c.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      <div>
        <div id="operator-label" className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-muted">
          Operator
        </div>
        <div className="flex gap-1">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="min-w-0 flex-1 justify-between font-normal"
                aria-labelledby="operator-label"
                aria-expanded={open}
                role="combobox"
              >
                <span className={operator ? "truncate" : "truncate text-muted"}>{operator ?? "All operators"}</span>
                <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted" aria-hidden />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-80">
              {/* The API filters, so cmdk's own fuzzy filter is switched off. */}
              <Command shouldFilter={false} value={highlighted} onValueChange={setHighlighted}>
                <CommandInput placeholder="Search operators…" value={search} onValueChange={setSearch} />
                <CommandList>
                  {operators.isFetching && !operators.data ? (
                    <div className="px-2 py-3 text-center text-xs text-muted">Searching…</div>
                  ) : (
                    <CommandEmpty>No operator matches “{search}”.</CommandEmpty>
                  )}
                  {operators.data?.map((o) => (
                    <CommandItem
                      key={o.operator}
                      value={o.operator}
                      onSelect={() => {
                        onOperatorChange(o.operator);
                        setOpen(false);
                      }}
                    >
                      <span className="flex min-w-0 items-center gap-2">
                        <Check className={o.operator === operator ? "h-4 w-4 text-sand" : "h-4 w-4 opacity-0"} aria-hidden />
                        <span className="truncate">{o.operator}</span>
                      </span>
                      <span className="shrink-0 text-xs text-muted">{formatCount(o.n_hpc_points)} HPC</span>
                    </CommandItem>
                  ))}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
          {operator && (
            <Button variant="ghost" size="icon" className="h-9 w-9" onClick={() => onOperatorChange(null)} aria-label="Clear operator filter">
              <X className="h-4 w-4" aria-hidden />
            </Button>
          )}
        </div>
      </div>

      <p className="text-[11px] leading-snug text-muted">
        Filters change the counts and heights. Deserts stay fixed: they depend only on HPC hubs.
      </p>
    </div>
  );
}
