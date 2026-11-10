// shadcn/ui-style wrapper around Radix ToggleGroup: arrow keys move between items, Space/Enter selects.
import * as ToggleGroupPrimitive from "@radix-ui/react-toggle-group";
import type { ComponentProps } from "react";
import { cn } from "@/lib/utils";

export function ToggleGroup({ className, ...props }: ComponentProps<typeof ToggleGroupPrimitive.Root>) {
  return (
    <ToggleGroupPrimitive.Root
      className={cn("inline-flex w-full rounded-md border border-line bg-black/20 p-0.5", className)}
      {...props}
    />
  );
}

export function ToggleGroupItem({ className, ...props }: ComponentProps<typeof ToggleGroupPrimitive.Item>) {
  return (
    <ToggleGroupPrimitive.Item
      className={cn(
        "flex-1 rounded px-2 py-1.5 text-xs font-medium text-muted transition-colors hover:text-fg",
        "data-[state=on]:bg-white/10 data-[state=on]:text-fg",
        className,
      )}
      {...props}
    />
  );
}
