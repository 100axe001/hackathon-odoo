import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import {
  cancelSubscription,
  loadBillingDetail,
  modifySubscription,
} from "@/api/api-functions/subscriptions";

export function BillingDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const [showProration, setShowProration] = useState(false);
  // Starts at what is subscribed today. It used to start at 2, so applying
  // without touching the box prorated a change to a quantity nobody chose.
  const [newQty, setNewQty] = useState(null);
  const [proration, setProration] = useState(null);
  useEffect(() => {
    loadBillingDetail(id).then((d) => {
      setDetail(d);
      setNewQty(d.recurring_lines?.[0]?.qty ?? 1);
    });
  }, [id]);
  if (!detail) return null;

  // The server prorates. The client used to assume a flat 30-day cycle with 15
  // days left, which happened to look plausible and was never right: the period
  // boundary and its real calendar length live on the subscription.
  const applyChange = async () => {
    try {
      const result = await modifySubscription(id, newQty);
      setProration(result);
      setToast(
        result.is_credit
          ? `Credit note raised for $${Math.abs(result.amount).toFixed(2)}`
          : `$${result.amount.toFixed(2)} charged for the remaining days`,
      );
      loadBillingDetail(id).then(setDetail);
      setShowProration(false);
    } catch {
      setToast("Could not modify this subscription.");
    }
  };

  const cancel = async () => {
    try {
      const result = await cancelSubscription(id);
      setToast(
        result.credit_amount
          ? `Cancelled. ${result.explanation} Credit note ${result.credit_note}.`
          : "Subscription cancelled",
      );
      loadBillingDetail(id).then(setDetail);
    } catch {
      setToast("Could not cancel. It may already be cancelled.");
    }
  };
  return (
    <Transition keyProp={`bd-${id}`}>
      <PageHeader title={`Billing — ${detail.customer}`} />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          One-Time Lines
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th right>Qty</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {detail.one_time_lines.map((l, i) => (
              <Tr key={i}>
                <Td>{l.product}</Td>
                <Td right>{l.qty}</Td>
                <Td right>${l.amount.toLocaleString()}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Recurring Lines
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Plan</Th>
              <Th>Cycle</Th>
              <Th right>Qty</Th>
              <Th>Next Bill Date</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {detail.recurring_lines.map((l, i) => (
              <Tr key={i}>
                <Td>{l.plan}</Td>
                <Td>{l.cycle}</Td>
                <Td right>{l.qty}</Td>
                <Td>{l.next_bill}</Td>
                <Td right>${l.amount.toLocaleString()}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      {/* PS 4-B7 asks for the upcoming billing schedule, not just the next
          date: a customer approving a subscription wants to see what they are
          committing to across the term. */}
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Upcoming Billing Schedule
        </div>
        {(detail.schedule ?? []).length === 0 ? (
          <div className="text-sm py-4" style={{ color: C.muted }}>
            Nothing scheduled — this order has no recurring lines yet.
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Due date</Th>
                <Th>Note</Th>
                <Th right>Amount</Th>
              </tr>
            </thead>
            <tbody>
              {detail.schedule.map((row, i) => (
                <Tr key={i}>
                  <Td>{row.due_date}</Td>
                  <Td>
                    {row.is_prorated ? (
                      <Badge status="Partial" label="Prorated" />
                    ) : (
                      <span style={{ color: C.muted }}>{row.note || "—"}</span>
                    )}
                  </Td>
                  <Td right>${row.amount.toLocaleString()}</Td>
                </Tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {showProration && (
        <Card className="mb-6">
          <div
            className="text-base font-semibold mb-1"
            style={{ color: C.text }}
          >
            Modify Subscription
          </div>
          <p className="text-sm mb-4" style={{ color: C.muted }}>
            Changing quantity mid-cycle is prorated: you are charged for the
            remaining days of the period only. The exact figure is calculated
            server-side against this subscription's real billing period.
          </p>

          <div className="flex items-end gap-6 flex-wrap">
            <div>
              <label className="block text-xs mb-1" style={{ color: C.muted }}>
                New quantity
              </label>
              <input
                type="number"
                min="0"
                value={newQty ?? ""}
                onChange={(e) =>
                  setNewQty(Math.max(0, Number(e.target.value) || 0))
                }
                className="rounded-md px-2 py-1.5 text-sm text-right tabular-nums outline-none transition-all duration-150"
                style={{ border: `1px solid ${C.border}`, width: 80 }}
              />
            </div>

            <div className="flex gap-2 ml-auto">
              <Button
                variant="secondary"
                onClick={() => setShowProration(false)}
              >
                Cancel
              </Button>
              <Button variant="primary" onClick={applyChange}>
                Apply Change
              </Button>
            </div>
          </div>

          {proration && (
            <div
              className="mt-4 pt-4 text-sm"
              style={{ borderTop: `1px solid ${C.border}`, color: C.muted }}
            >
              {proration.explanation}{" "}
              <span
                className="font-semibold tabular-nums"
                style={{
                  color: proration.is_credit ? C.successText : C.text,
                }}
              >
                {proration.is_credit ? "Credit" : "Charge"} $
                {Math.abs(proration.amount).toFixed(2)}
              </span>
            </div>
          )}
        </Card>
      )}

      <div className="flex justify-end gap-3">
        <Button variant="destructive" onClick={cancel}>
          Cancel Subscription
        </Button>
        <Button variant="secondary" onClick={() => setShowProration(true)}>
          Modify Subscription
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
