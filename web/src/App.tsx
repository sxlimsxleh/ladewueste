import { TopNav } from "@/components/TopNav";
import { DataDoctor } from "@/pages/DataDoctor";
import { DesertMap } from "@/pages/DesertMap";
import { useRoute } from "@/lib/router";

export function App() {
  const route = useRoute();
  return (
    <div className="relative h-full w-full">
      {/* The map stays mounted underneath, so a game in progress survives a visit to the Data Doctor. */}
      <div className="h-full w-full" inert={route !== "map"} aria-hidden={route !== "map"}>
        <DesertMap />
      </div>
      {route === "doctor" && (
        <div className="absolute inset-0 z-40 overflow-y-auto bg-ink">
          {/* A solid bar under the page switch, so scrolled content never runs behind it. */}
          <div className="sticky top-0 z-10 h-14 border-b border-line bg-ink/90 backdrop-blur" aria-hidden />
          <DataDoctor />
        </div>
      )}
      <div className="pointer-events-none absolute left-1/2 top-3 z-50 -translate-x-1/2">
        <div className="pointer-events-auto">
          <TopNav current={route} />
        </div>
      </div>
    </div>
  );
}
