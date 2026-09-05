import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadBillingDetail } from "@/api/api-functions/subscriptions";

export function BillingDetailScreen({ id, setRoute }) {
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadBillingDetail(id).then(setDetail);
  }, [id]);
  if (!detail) return null;
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
      <div className="flex justify-end gap-3">
        <Button
          variant="destructive"
          onClick={() => setToast("Subscription cancelled")}
        >
          Cancel Subscription
        </Button>
        <Button
          variant="secondary"
          onClick={() => setToast("Modify flow opened")}
        >
          Modify Subscription
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
