import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FilterPill } from "@/components/ui/FilterPill";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { ViewToggle } from "@/components/ui/ViewToggle";
import { QuotationBoard } from "@/components/quotations/QuotationBoard";
import { loadQuotations } from "@/api/api-functions/quotations";

const STAGES = [
  "Draft",
  "Pending Approval",
  "Approved",
  "Negotiation",
  "Confirmed",
];

export function QuotationsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [filter, setFilter] = useState("All");
  // Board first: the wireframe's control reads "Switch to Table View", and PS
  // section 4 B1 lists Pipeline as a top-level view.
  const [view, setView] = useState("board");

  useEffect(() => {
    loadQuotations().then(setData);
  }, []);

  const open = (id) => navigate(`/quotations/${id}`);

  // Dragging a card to another column moves the deal's stage. Optimistic here;
  // the backend will own the transition once the endpoint exists.
  const move = (id, status) =>
    setData((list) => list.map((q) => (q.id === id ? { ...q, status } : q)));
  const filtered =
    filter === "All" ? data : data.filter((q) => q.status === filter);

  return (
    <Transition keyProp="quotations">
      <PageHeader
        title="Quotations"
        subtitle="Every quotation in the system. Open one to add products, apply discounts, and review upsells."
        action={
          <div className="flex items-center gap-3">
            <ViewToggle
              value={view}
              onChange={setView}
              options={[
                { value: "board", label: "Pipeline" },
                { value: "table", label: "Table" },
              ]}
            />
            <Button variant="primary" onClick={() => open("q1")}>
              + New Quotation
            </Button>
          </div>
        }
      />

      <div className="flex items-center gap-1 mb-4">
        {["All", ...STAGES].map((f) => (
          <FilterPill
            key={f}
            active={filter === f}
            onClick={() => setFilter(f)}
          >
            {f}
          </FilterPill>
        ))}
      </div>

      {view === "board" ? (
        <QuotationBoard
          stages={filter === "All" ? STAGES : [filter]}
          quotations={filtered}
          onOpen={open}
          onMove={move}
        />
      ) : (
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
                <Tr key={q.id} onClick={() => open(q.id)}>
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
      )}
    </Transition>
  );
}
