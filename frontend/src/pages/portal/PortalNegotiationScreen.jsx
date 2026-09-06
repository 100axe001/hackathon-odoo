import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Td, Th, Tr } from "@/components/ui/Table";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { Input } from "@/components/ui/Input";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { money } from "@/utils/money";
import {
  confirmQuotation,
  loadPortalQuotation,
  negotiate,
} from "@/api/api-functions/portal";

export function PortalNegotiationScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [status, setStatus] = useState("");
  const [counterDiscount, setCounterDiscount] = useState("");
  const [deliveryDate, setDeliveryDate] = useState("");
  const [note, setNote] = useState("");
  const [showBanner, setShowBanner] = useState(false);
  const [banner, setBanner] = useState("");

  useEffect(() => {
    loadPortalQuotation(id).then((d) => {
      setDetail(d);
      setStatus(d.status);
    });
  }, [id]);

  const submitRequest = async () => {
    try {
      const result = await negotiate(
        id,
        counterDiscount === "" ? null : Number(counterDiscount),
        deliveryDate,
        note,
      );
      setStatus(result.status);
      setBanner("Your request has been sent to the deal desk.");
      setShowBanner(true);
      loadPortalQuotation(id).then(setDetail).catch(setLoadError);
    } catch {
      setBanner("Could not send that request. Please try again.");
      setShowBanner(true);
    }
  };

  // The client does not decide whether the terms need review. It cannot: the
  // ceiling is min(customer tier, product category) per line, resolved from
  // configuration. The server re-scores and tells us - PS section 7 requires
  // the rule to live in application logic, not here.
  const confirm = async () => {
    try {
      const result = await confirmQuotation(id);
      setStatus(result.status);
      setBanner(
        result.reentered_approval
          ? `Your terms need another review. ${result.explanation} It is now with ${result.required_approval.join(" then ")}.`
          : "Confirmed. Your order is moving to fulfillment.",
      );
      setShowBanner(true);
      // Re-read so the buttons go: the quotation is no longer the customer's
      // to act on, and leaving them there is what made a second click look
      // like the first one had failed.
      setDetail(await loadPortalQuotation(id));
    } catch (err) {
      setBanner(err.detail || "Could not confirm. Please try again.");
      setShowBanner(true);
    }
  };

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!detail) return null;

  return (
    <div className="max-w-[760px] mx-auto py-10 px-6">
      <div className="mb-6">
        <Badge
          status={status === "Confirmed" ? "Confirmed" : "Pending Approval"}
          label={status}
        />
      </div>

      {showBanner && (
        <Transition keyProp="banner">
          <div className="mb-6">
            {/* The wireframe insists this is a visible status change rather
                than a silent redirect, so the customer understands why their
                confirmation did not complete. */}
            <InfoBanner tone={status === "Confirmed" ? "success" : "warn"}>
              {banner}
            </InfoBanner>
          </div>
        </Transition>
      )}

      {/* PS section 4 B8: the portal shows the quotation itself, not just a
          negotiation form. */}
      <Card className="mb-6">
        <div
          className="flex items-baseline justify-between mb-4"
          style={{ color: C.text }}
        >
          <span className="text-base font-semibold">
            {detail.number} — {detail.customer}
          </span>
          <span className="text-sm tabular-nums" style={{ color: C.muted }}>
            Total {money(detail.total)}
          </span>
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th right>Qty</Th>
              <Th right>Unit price</Th>
              <Th right>Discount</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {(detail.lines ?? []).map((l) => (
              <Tr key={l.id}>
                <Td>{l.product}</Td>
                <Td right>{l.qty}</Td>
                <Td right>{money(l.price)}</Td>
                <Td right>{l.discount_pct}%</Td>
                <Td right>{money(l.amount)}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
          Line Comments
        </div>
        <div className="flex flex-col gap-4">
          {(detail.comments ?? []).map((c, i) => (
            <div key={i}>
              <div
                className="text-sm font-medium mb-1.5"
                style={{ color: C.text }}
              >
                {c.author}
                <span className="font-normal ml-2" style={{ color: C.muted }}>
                  {c.created_at}
                </span>
              </div>
              <div
                className="rounded-lg px-4 py-3 text-sm"
                style={{
                  backgroundColor: C.bg,
                  color: C.text,
                  borderRadius: "12px 12px 12px 2px",
                }}
              >
                {c.body}
                {c.counter_discount_pct != null && (
                  <span className="font-medium">
                    {" "}
                    (requested {c.counter_discount_pct}%)
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Only offered when the quotation is actually the customer's to act on.
          It used to show in every state, so confirming an already-confirmed
          quotation returned success and changed nothing on screen - which
          reads exactly like a broken button. */}
      {detail.can_act ? (
        <Card className="mb-6">
          <div className="flex gap-4 mb-4">
            <div className="flex-1">
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Counter Discount %
              </label>
              <Input
                type="number"
                value={counterDiscount}
                onChange={(e) => setCounterDiscount(e.target.value)}
                placeholder="e.g. 12"
              />
            </div>
            <div className="flex-1">
              <label className="text-sm mb-1 block" style={{ color: C.text }}>
                Requested Delivery Date
              </label>
              <Input
                type="date"
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Negotiation notes
            </label>
            <textarea
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Business justification for the requested terms"
              className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150"
              style={{ border: `1px solid ${C.border}` }}
            />
          </div>

          <div className="text-sm mb-4 mt-4" style={{ color: C.muted }}>
            If final terms exceed approval thresholds, the quote automatically
            re-enters approval.
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={submitRequest}>
              Submit Request
            </Button>
            <Button variant="success" onClick={confirm}>
              Confirm Quotation
            </Button>
          </div>
        </Card>
      ) : (
        <Card className="mb-6">
          <div className="text-sm" style={{ color: C.text }}>
            {detail.blocked_reason}
          </div>
          {status === "Confirmed" && (
            <div className="mt-3">
              <Button
                variant="secondary"
                onClick={() => navigate("/portal/orders")}
              >
                Track this order
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
