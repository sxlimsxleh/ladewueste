import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LoadingCard({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 rounded-xl border border-line bg-panel px-5 py-4 shadow-2xl backdrop-blur-md">
      <Loader2 className="h-5 w-5 animate-spin text-sand" aria-hidden />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="max-w-md rounded-xl border border-red-400/30 bg-panel px-5 py-4 shadow-2xl backdrop-blur-md">
      <div className="flex items-center gap-2 font-medium text-red-300">
        <AlertTriangle className="h-4 w-4" aria-hidden /> Could not load the map data
      </div>
      <p className="mt-2 text-sm text-muted">{message}</p>
      <Button variant="outline" size="sm" className="mt-3" onClick={onRetry}>
        Try again
      </Button>
    </div>
  );
}
