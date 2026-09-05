import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatPill } from "@/components/ui/StatPill";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { loadInvoices } from "@/api/api-functions/invoices";

export function InvoicesScreen({ setRoute }) {
  const [data, setData] = useState([]);
  useEffect(() => {
    loadInvoices().then(setData);
  }, []);
  const unpaid = data.filter((i) => i.status === "Unpaid").length;
  const paid = data.filter((i) => i.status === "Paid").length;
  return (
    <Transition keyProp="invoices">
      <PageHeader title="Invoices" />
      <div className="flex gap-3 mb-4">
        <StatPill label="Unpaid" count={unpaid} tone="danger" />
        <StatPill label="Paid" count={paid} tone="success" />
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Invoice #</Th>
              <Th>Customer</Th>
              <Th right>Amount</Th>
              <Th>Status</Th>
              <Th>Due Date</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((inv) => (
              <Tr
                key={inv.id}
                onClick={() => setRoute({ name: "invoice-detail", id: inv.id })}
              >
                <Td>{inv.invoice_no}</Td>
                <Td>{inv.customer}</Td>
                <Td right>${inv.amount.toLocaleString()}</Td>
                <Td>
                  <Badge status={inv.status} />
                </Td>
                <Td>{inv.due_date}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
