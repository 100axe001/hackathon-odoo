import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FilterPill } from "@/components/ui/FilterPill";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { loadQuotations } from "@/api/api-functions/quotations";

export function QuotationsScreen({ setRoute }) {
  const [data, setData] = useState([]);
  const [filter, setFilter] = useState("All");
  useEffect(() => {
    loadQuotations().then(setData);
  }, []);
  const filters = [
    "All",
    "Draft",
    "Pending Approval",
    "Approved",
    "Negotiation",
    "Confirmed",
  ];
  const filtered =
    filter === "All" ? data : data.filter((q) => q.status === filter);
  return (
    <Transition keyProp="quotations">
      <PageHeader
        title="Quotations"
        action={
          <Button
            variant="primary"
            onClick={() => setRoute({ name: "quotation-detail", id: "q1" })}
          >
            + New Quotation
          </Button>
        }
      />
      <div className="flex items-center gap-1 mb-4">
        {filters.map((f) => (
          <FilterPill
            key={f}
            active={filter === f}
            onClick={() => setFilter(f)}
          >
            {f}
          </FilterPill>
        ))}
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Customer</Th>
              <Th right>Amount</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((q) => (
              <Tr
                key={q.id}
                onClick={() => setRoute({ name: "quotation-detail", id: q.id })}
              >
                <Td>{q.customer_name}</Td>
                <Td right>${q.amount.toLocaleString()}</Td>
                <Td>
                  <Badge status={q.status} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
