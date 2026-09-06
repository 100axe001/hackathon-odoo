import { Button } from "@/components/ui/Button";
import { C } from "@/constants/theme";

// What a screen shows when its data could not be loaded. There is no mock
// fallback any more, so without this a failed request left the page blank with
// no explanation - which reads as "the feature is broken" rather than "the API
// is not answering".
export function LoadFailed({ error, onRetry, retryLabel = "Try again" }) {
  // A record that is gone is not a broken screen. Telling someone who just
  // deleted a quotation to check that the API is running would send them
  // looking for a fault that is not there.
  const missing = error?.status === 404;
  const message = missing
    ? error?.detail || "That record no longer exists."
    : error?.status === 403
      ? "Your role does not have access to this data."
      : error?.detail || "Could not reach the server.";

  return (
    <div
      className="rounded-lg px-6 py-10 text-center"
      style={{ backgroundColor: C.neutralBg, border: `1px solid ${C.border}` }}
    >
      <div className="text-base font-semibold mb-1" style={{ color: C.text }}>
        {missing ? "Nothing here" : "This screen could not load"}
      </div>
      <p className="text-sm mb-5" style={{ color: C.muted }}>
        {message}
        {!missing &&
          " Check that the API is running on port 8000, then try again."}
      </p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {retryLabel}
        </Button>
      )}
    </div>
  );
}
