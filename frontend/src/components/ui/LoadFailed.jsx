import { Button } from "@/components/ui/Button";
import { C } from "@/constants/theme";

// What a screen shows when its data could not be loaded. There is no mock
// fallback any more, so without this a failed request left the page blank with
// no explanation - which reads as "the feature is broken" rather than "the API
// is not answering".
export function LoadFailed({ error, onRetry }) {
  const message =
    error?.status === 403
      ? "Your role does not have access to this data."
      : error?.detail || "Could not reach the server.";

  return (
    <div
      className="rounded-lg px-6 py-10 text-center"
      style={{ backgroundColor: C.neutralBg, border: `1px solid ${C.border}` }}
    >
      <div className="text-base font-semibold mb-1" style={{ color: C.text }}>
        This screen could not load
      </div>
      <p className="text-sm mb-5" style={{ color: C.muted }}>
        {message} Check that the API is running on port 8000, then try again.
      </p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
