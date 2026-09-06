import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { C } from "@/constants/theme";
import { loadThread, replyToCustomer } from "@/api/api-functions/quotations";

// The rep's side of the negotiation. PS section 3 says a rep responds to
// customer change requests; before this the counter-offer arrived as a number
// on the quotation with nowhere to answer the question that came with it.
export function CustomerThread({ quotationId, onSent }) {
  const [thread, setThread] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    loadThread(quotationId)
      .then((rows) => live && setThread(rows))
      .catch(() => live && setThread([]));
    return () => {
      live = false;
    };
  }, [quotationId]);

  const send = async () => {
    if (!draft.trim()) return;
    try {
      setThread(await replyToCustomer(quotationId, draft.trim()));
      setDraft("");
      setError("");
      onSent?.();
    } catch (err) {
      setError(err.detail || "Could not send that reply.");
    }
  };

  if (thread.length === 0 && !draft) {
    return (
      <Card className="mb-6">
        <div className="text-base font-semibold mb-1" style={{ color: C.text }}>
          Customer Conversation
        </div>
        <p className="text-sm" style={{ color: C.muted }}>
          Nothing from the customer yet. Anything they ask in the portal appears
          here, and your reply goes straight back to them.
        </p>
      </Card>
    );
  }

  return (
    <Card className="mb-6">
      <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
        Customer Conversation
      </div>

      <div className="flex flex-col gap-3 mb-4">
        {thread.map((m, i) => {
          const theirs = m.role === "Customer";
          return (
            <div
              key={i}
              className="flex flex-col"
              style={{ alignItems: theirs ? "flex-start" : "flex-end" }}
            >
              <div className="text-xs mb-1" style={{ color: C.muted }}>
                {m.author} · {m.created_at}
              </div>
              <div
                className="rounded-lg px-4 py-2.5 text-sm"
                style={{
                  maxWidth: "80%",
                  backgroundColor: theirs ? C.neutralBg : C.accent,
                  color: theirs ? C.text : "#fff",
                  borderRadius: theirs
                    ? "12px 12px 12px 2px"
                    : "12px 12px 2px 12px",
                }}
              >
                {m.body}
                {m.counter_discount_pct != null && (
                  <span className="font-medium">
                    {" "}
                    (asked for {m.counter_discount_pct}%)
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <textarea
        rows={2}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        placeholder="Reply to the customer…"
        className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150"
        style={{ border: `1px solid ${C.border}` }}
      />
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs" style={{ color: C.dangerText }}>
          {error}
        </span>
        <Button variant="secondary" onClick={send} disabled={!draft.trim()}>
          Send reply
        </Button>
      </div>
    </Card>
  );
}
