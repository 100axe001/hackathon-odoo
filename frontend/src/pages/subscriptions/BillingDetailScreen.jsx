import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadBillingDetail } from "@/api/api-functions/subscriptions";

export function BillingDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  const [showProration, setShowProration] = useState(false);
  const [newQty, setNewQty] = useState(2);
  useEffect(() => {
    loadBillingDetail(id).then(setDetail);
  }, [id]);
  if (!detail) return null;

  // PS section 4 B7: mid-cycle proration. The rule is
  // price_delta x (remaining_days / cycle_days). Days are illustrative here -
  // the backend recomputes from real dates and is authoritative.
  const CYCLE_DAYS = 30;
  const DAYS_REMAINING = 15;
  const line = detail.recurring_lines[0] || { amount: 0 };
  const currentQty = 1;
  const unitPrice = line.amount || 0;
  const deltaQty = newQty - currentQty;

  const proration = {
    cycle_days: CYCLE_DAYS,
    days_remaining: DAYS_REMAINING,
    unit_price: unitPrice,
    delta_qty: deltaQty,
    amount: deltaQty * unitPrice * (DAYS_REMAINING / CYCLE_DAYS),
  };

  // Cancelling mid-cycle refunds the unused remainder as a credit note.
  const cancellationCredit = -unitPrice * (DAYS_REMAINING / CYCLE_DAYS);
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
              <Th>Next Bill Date</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {detail.recurring_lines.map((l, i) => (
              <Tr key={i}>
                <Td>{l.plan}</Td>
                <Td>{l.cycle}</Td>
                <Td>{l.next_bill}</Td>
                <Td right>${l.amount.toLocaleString()}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
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
            remaining days of the period only.
          </p>

          <div className="flex items-end gap-6 flex-wrap">
            <div>
              <label className="block text-xs mb-1" style={{ color: C.muted }}>
                New quantity
              </label>
              <input
                type="number"
                min="0"
                value={newQty}
                onChange={(e) =>
                  setNewQty(Math.max(0, Number(e.target.value) || 0))
                }
                className="rounded-md px-2 py-1.5 text-sm text-right tabular-nums outline-none transition-all duration-150"
                style={{ border: `1px solid ${C.border}`, width: 80 }}
              />
            </div>

            <div className="text-sm" style={{ color: C.muted }}>
              <div className="tabular-nums">
                {proration.days_remaining} of {proration.cycle_days} days
                remaining
              </div>
              <div className="tabular-nums">
                {proration.delta_qty >= 0 ? "+" : ""}
                {proration.delta_qty} x ${proration.unit_price} x{" "}
                {proration.days_remaining}/{proration.cycle_days}
              </div>
            </div>

            <div>
              <div className="text-xs mb-0.5" style={{ color: C.muted }}>
                {proration.amount >= 0 ? "Charge now" : "Credit note"}
              </div>
              <div
                className="text-lg font-semibold tabular-nums"
                style={{
                  color: proration.amount >= 0 ? C.text : C.successText,
                }}
              >
                ${Math.abs(proration.amount).toFixed(2)}
              </div>
            </div>

            <div className="flex gap-2 ml-auto">
              <Button
                variant="secondary"
                onClick={() => setShowProration(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  setShowProration(false);
                  setToast(
                    proration.amount >= 0
                      ? `Subscription modified - $${proration.amount.toFixed(2)} charged`
                      : `Subscription modified - credit note for $${Math.abs(proration.amount).toFixed(2)}`,
                  );
                }}
              >
                Apply Change
              </Button>
            </div>
          </div>
        </Card>
      )}

      <div className="flex justify-end gap-3">
        <Button
          variant="destructive"
          onClick={() =>
            setToast(
              `Subscription cancelled - credit note for $${Math.abs(cancellationCredit).toFixed(2)}`,
            )
          }
        >
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
