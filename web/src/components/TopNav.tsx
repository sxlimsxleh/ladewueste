import { Map as MapIcon, Stethoscope } from "lucide-react";
import { hrefFor, type Route } from "@/lib/router";
import { cn } from "@/lib/utils";

const ITEMS: { route: Route; label: string; icon: typeof MapIcon }[] = [
  { route: "map", label: "Desert map", icon: MapIcon },
  { route: "doctor", label: "Data Doctor", icon: Stethoscope },
];

/** Switch between the two pages. Plain links, so they work with the keyboard and the back button. */
export function TopNav({ current }: { current: Route }) {
  return (
    <nav aria-label="Pages" className="flex gap-0.5 rounded-full border border-line bg-panel p-0.5 shadow-xl backdrop-blur-md">
      {ITEMS.map(({ route, label, icon: Icon }) => (
        <a
          key={route}
          href={hrefFor(route)}
          aria-current={current === route ? "page" : undefined}
          className={cn(
            "flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
            current === route ? "bg-white/10 text-fg" : "text-muted hover:text-fg",
          )}
        >
          <Icon className="h-3.5 w-3.5" aria-hidden />
          {label}
        </a>
      ))}
    </nav>
  );
}
