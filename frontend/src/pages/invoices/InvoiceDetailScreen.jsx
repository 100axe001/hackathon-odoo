import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Stepper } from "@/components/ui/Stepper";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadInvoiceDetail } from "@/api/api-functions/invoices";

export function InvoiceDetailScreen({ id }) {
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadInvoiceDetail(id).then(setDetail);
  }, [id]);
  if (!detail) return null;
  const stageIndex = ["Order Confirmed", "Shipped", "Invoiced", "Paid"].indexOf(
    detail.stage,
  );
  return (
    <Transition keyProp={`invd-${id}`}>
      <PageHeader title={`${detail.invoice_no} — ${detail.customer}`} />
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
      <div className="flex justify-end gap-3">
        <Button
          variant="secondary"
          onClick={() => setToast("Summary downloaded")}
        >
          Download Summary
        </Button>
        <Button variant="primary" onClick={() => setToast("Payment recorded")}>
          Record Payment
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
