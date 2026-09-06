import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Td, Th, Tr } from "@/components/ui/Table";
import { C } from "@/constants/theme";
import { money } from "@/utils/money";
import { loadPortalBilling } from "@/api/api-functions/portal";

export function PortalBillingScreen() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    loadPortalBilling().then(setData).catch(setLoadError);
  }, []);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!data) return null;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-1" style={{ color: C.text }}>
        Billing
      </h1>
      <p className="text-sm mb-6" style={{ color: C.muted }}>
        Invoices, credit notes, and anything that bills again.
      </p>

      <Card className="mb-6">
        <div
          className="text-xs uppercase tracking-wide"
          style={{ color: C.muted }}
        >
          Total outstanding
        </div>
        <div
          className="text-2xl font-semibold tabular-nums"
          style={{
            color: data.total_outstanding > 0 ? C.text : C.successText,
          }}
        >
          {money(data.total_outstanding)}
        </div>
        <div className="text-xs mt-1" style={{ color: C.muted }}>
          {/* Credit notes are money owed back, so they reduce this rather than
              sitting in the list as another thing to pay. */}
          Net of any credit notes already raised.
        </div>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Documents
        </div>
        {data.invoices.length === 0 ? (
          <div className="text-sm py-4" style={{ color: C.muted }}>
            Nothing invoiced yet.
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Document</Th>
                <Th>Order</Th>
                <Th>Issued</Th>
                <Th>Due</Th>
                <Th right>Amount</Th>
                <Th right>Paid</Th>
                <Th right>Still owed</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {data.invoices.map((inv) => (
                <Tr key={inv.id}>
                  <Td>
                    {inv.number}
                    <span className="ml-2 text-xs" style={{ color: C.muted }}>
                      {inv.document}
                    </span>
                  </Td>
                  <Td>{inv.order}</Td>
                  <Td>{inv.issue_date}</Td>
                  <Td>{inv.due_date}</Td>
                  <Td right>{money(inv.amount)}</Td>
                  <Td right>{money(inv.paid)}</Td>
                  <Td
                    right
                    style={{
                      color: inv.balance_due > 0 ? C.dangerText : C.successText,
                    }}
                  >
                    {money(inv.balance_due)}
                  </Td>
                  <Td>
                    <Badge status={inv.status} />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card>
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Recurring
        </div>
        {data.subscriptions.length === 0 ? (
          <div className="text-sm py-4" style={{ color: C.muted }}>
            Nothing on a recurring plan.
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Plan</Th>
                <Th>Billed</Th>
                <Th right>Qty</Th>
                <Th right>Amount</Th>
                <Th>Next charge</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {data.subscriptions.map((s, i) => (
                <Tr key={i}>
                  <Td>{s.plan}</Td>
                  <Td>{s.cycle}</Td>
                  <Td right>{s.qty}</Td>
                  <Td right>{money(s.amount)}</Td>
                  <Td>{s.next_bill}</Td>
                  <Td>
                    <Badge status={s.status} />
                  </Td>
                </Tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
