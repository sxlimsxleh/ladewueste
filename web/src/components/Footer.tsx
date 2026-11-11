import type { AppConfig } from "@/lib/api";
import { registerDate } from "@/lib/scales";

/** Data credit, required by the register's CC BY 4.0 licence. The basemap credit is MapLibre's own control. */
export function Footer({ config }: { config: AppConfig | undefined }) {
  const date = registerDate(config?.data_file);
  return (
    <footer className="pointer-events-auto rounded-md bg-ink/70 px-2 py-1 text-[11px] text-muted backdrop-blur">
      Data:{" "}
      <a className="underline decoration-line underline-offset-2 hover:text-fg" href="https://www.bundesnetzagentur.de/ladesaeulenkarte" target="_blank" rel="noreferrer">
        {config?.attribution ?? "Bundesnetzagentur.de"}
      </a>
      , Ladesäulenregister{date ? ` (as of ${date})` : ""},{" "}
      <a className="underline decoration-line underline-offset-2 hover:text-fg" href={config?.licence_url ?? "https://creativecommons.org/licenses/by/4.0/"} target="_blank" rel="noreferrer">
        {config?.licence ?? "CC BY 4.0"}
      </a>
      , processed by Ladewüste · Boundary: Natural Earth
    </footer>
  );
}
