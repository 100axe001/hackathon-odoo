import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Stepper } from "@/components/ui/Stepper";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { loadInvoiceDetail, recordPayment } from "@/api/api-functions/invoices";

export function InvoiceDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState("");
  const [payOpen, setPayOpen] = useState(false);
  const [payAmount, setPayAmount] = useState("");
  useEffect(() => {
    loadInvoiceDetail(id).then(setDetail).catch(setLoadError);
  }, [id]);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!detail) return null;
  const stageIndex = ["Order Confirmed", "Shipped", "Invoiced", "Paid"].indexOf(
    detail.stage,
  );
  // The server computes what is owed; the screen shows it. Defaults the
  // payment box, since paying in full is the common case.
  const outstanding = detail.balance_due ?? 0;
  const money = (n) =>
    `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const settled = detail.amount
    ? (detail.paid_amount / detail.amount) * 100
    : 0;

  const submitPayment = async () => {
    try {
      const updated = await recordPayment(id, Number(payAmount));
      setDetail(updated);
      setPayOpen(false);
      setToast(`Payment recorded — invoice is now ${updated.status}`);
    } catch (err) {
      setToast(
        err.status === 403
          ? "Only finance may record a payment."
          : err.detail || "Could not record that payment.",
      );
    }
  };

  return (
    <Transition keyProp={`invd-${id}`}>
      <PageHeader
        title={`${detail.invoice_no} — ${detail.customer}`}
        subtitle={`${detail.doc_type === "CREDIT_NOTE" ? "Credit note" : "Invoice"} issued ${detail.issue_date} · due ${detail.due_date}`}
        action={
          <Button variant="secondary" onClick={() => window.print()}>
            Print Invoice
          </Button>
        }
      />

      {/* Total, settled and outstanding side by side. A part-paid invoice used
          to look like an unpaid one apart from a badge. */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-8">
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Invoice total
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{ color: C.text }}
            >
              {money(detail.amount)}
            </div>
          </div>
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Paid to date
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{
                color: detail.paid_amount > 0 ? C.successText : C.muted,
              }}
            >
              {money(detail.paid_amount)}
            </div>
          </div>
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Outstanding
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{ color: outstanding > 0 ? C.dangerText : C.successText }}
            >
              {money(outstanding)}
            </div>
          </div>
          <div className="ml-auto text-right">
            <Badge status={detail.status} />
            <div className="text-xs mt-1" style={{ color: C.muted }}>
              {detail.recorded_by
                ? `Recorded by ${detail.recorded_by}${detail.paid_at ? ` on ${detail.paid_at}` : ""}${detail.paid_method ? ` · ${detail.paid_method.replace("_", " ").toLowerCase()}` : ""}`
                : "No payment recorded yet"}
            </div>
          </div>
        </div>

        {/* A bar reads faster than two numbers when the question is "how much
            of this is still open?". */}
        <div
          className="mt-4 rounded-full overflow-hidden"
          style={{ height: 6, backgroundColor: C.neutralBg }}
        >
          <div
            style={{
              width: `${Math.min(100, Math.max(0, settled))}%`,
              height: "100%",
              backgroundColor:
                settled >= 100
                  ? C.successText
                  : settled > 0
                    ? C.warnText
                    : "transparent",
              transition: "width 200ms",
            }}
          />
        </div>
      </Card>

      <Card className="mb-6">
        <Stepper
          steps={["Order Confirmed", "Shipped", "Invoiced", "Paid"]}
          currentIndex={stageIndex}
        />
      </Card>
      <Card className="mb-6">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th right>Qty</Th>
              <Th right>Amount</Th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((l, i) => (
              <Tr key={i}>
                <Td>
                  {l.product}
                  {l.recurring && (
                    <span className="ml-2 text-xs" style={{ color: C.muted }}>
                      (Recurring)
                    </span>
                  )}
                </Td>
                <Td right>{l.qty}</Td>
                <Td right>${l.amount.toLocaleString()}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="flex justify-end gap-3 no-print">
        {outstanding > 0 && detail.doc_type !== "CREDIT_NOTE" ? (
          <Button
            variant="success"
            onClick={() => {
              setPayAmount(String(outstanding));
              setPayOpen(true);
            }}
          >
            Record Payment
          </Button>
        ) : (
          <span className="text-sm self-center" style={{ color: C.muted }}>
            {detail.doc_type === "CREDIT_NOTE"
              ? "A credit note is money owed to the customer, so it takes no payment."
              : "Settled in full — nothing left to collect."}
          </span>
        )}
      </div>
      {payOpen && (
        <Card className="mt-6 no-print">
          <div
            className="text-base font-semibold mb-1"
            style={{ color: C.text }}
          >
            Record Payment
          </div>
          <p className="text-sm mb-4" style={{ color: C.muted }}>
            ${(detail.paid_amount ?? 0).toLocaleString()} of $
            {(detail.amount ?? 0).toLocaleString()} received. A payment below
            the balance leaves the invoice Partial.
          </p>
          <div className="flex items-end gap-4">
            <div>
              <label className="block text-xs mb-1" style={{ color: C.muted }}>
                Amount
              </label>
              <input
                type="number"
                value={payAmount}
                onChange={(e) => setPayAmount(e.target.value)}
                className="rounded-md px-2 py-1.5 text-sm text-right tabular-nums outline-none transition-all duration-150"
                style={{ border: `1px solid ${C.border}`, width: 120 }}
              />
            </div>
            <div className="flex gap-2 ml-auto">
              <Button variant="secondary" onClick={() => setPayOpen(false)}>
                Cancel
              </Button>
              <Button variant="success" onClick={submitPayment}>
                Confirm Payment
              </Button>
            </div>
          </div>
        </Card>
      )}

      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
