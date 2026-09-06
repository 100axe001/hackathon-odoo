import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FilterPill } from "@/components/ui/FilterPill";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Transition } from "@/components/ui/Transition";
import { ViewToggle } from "@/components/ui/ViewToggle";
import { CustomerPicker } from "@/components/quotations/CustomerPicker";
import { QuotationBoard } from "@/components/quotations/QuotationBoard";
import {
  changeQuotationStage,
  createQuotation,
  loadQuotations,
} from "@/api/api-functions/quotations";

// Every status a quotation can hold, so nothing is invisible: the board used
// to omit Rejected, and a rejected deal then belonged to no column at all.
const STAGES = [
  "Draft",
  "Pending Approval",
  "Approved",
  "Negotiation",
  "Confirmed",
  "Rejected",
];

export function QuotationsScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState([]);
  const [loadError, setLoadError] = useState(null);
  const [filter, setFilter] = useState("All");
  // Board first: the wireframe's control reads "Switch to Table View", and PS
  // section 4 B1 lists Pipeline as a top-level view.
  const [view, setView] = useState("board");
  // The dashboard's "+ New Quotation" lands here asking for the picker, since
  // creation needs a customer and that list lives on this screen.
  const [picking, setPicking] = useState(Boolean(location.state?.newQuotation));
  const [starting, setStarting] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    loadQuotations().then(setData).catch(setLoadError);
  }, []);

  // Consume the request once. Router state survives a reload, so leaving it in
  // place reopened the picker on every later visit to this screen - and its
  // full-screen overlay swallowed clicks on everything beneath.
  useEffect(() => {
    if (location.state?.newQuotation) {
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.pathname, location.state, navigate]);

  const open = (id) => navigate(`/quotations/${id}`);

  const start = async (customer) => {
    setPicking(false);
    setStarting(true);
    try {
      const quotation = await createQuotation(customer.id);
      open(quotation.id);
    } catch {
      setToast(`Could not start a quotation for ${customer.name}.`);
    } finally {
      setStarting(false);
    }
  };

  // Dragging a card moves the deal's stage. Optimistic so the board stays
  // responsive, but the backend decides which moves are legal - submitting,
  // approving and confirming own the rest - so a refusal puts the card back.
  const move = (id, status) => {
    // Revert only this card, not a whole-list snapshot: with two drags in
    // flight, restoring the snapshot would discard the other one's reconciled row.
    const previous = data.find((q) => q.id === id)?.status;
    setData((list) => list.map((q) => (q.id === id ? { ...q, status } : q)));

    changeQuotationStage(id, status)
      .then((row) =>
        setData((list) =>
          list.map((q) => (q.id === row.id ? { ...q, ...row } : q)),
        ),
      )
      .catch((err) => {
        setData((list) =>
          list.map((q) => (q.id === id ? { ...q, status: previous } : q)),
        );
        // The server explains which endpoint owns the transition it refused.
        setToast(err.detail || "Could not move that deal.");
      });
  };
  const filtered =
    filter === "All" ? data : data.filter((q) => q.status === filter);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );

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
            <Button variant="primary" onClick={() => setPicking(true)}>
              {starting ? "Opening…" : "+ New Quotation"}
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

      <CustomerPicker
        open={picking}
        onClose={() => setPicking(false)}
        onPick={start}
      />
      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
