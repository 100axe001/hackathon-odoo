import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { FilterPill } from "@/components/ui/FilterPill";
import { C } from "@/constants/theme";
import { loadCustomers } from "@/api/api-functions/quotations";

// A quotation belongs to a customer before it has anything else, so "+ New
// Quotation" has to ask for one. Modelled on ProductPicker so the two modals in
// the quoting flow read the same.
export function CustomerPicker({ open, onClose, onPick }) {
  const [customers, setCustomers] = useState([]);
  const [error, setError] = useState("");
  const [tier, setTier] = useState("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!open) return;
    setError("");
    loadCustomers().then(setCustomers, () =>
      // Deliberately not a mock list: picking an invented customer would fail
      // at create time, which is a worse place to discover the problem.
      setError("Could not load the customer list."),
    );
  }, [open]);

  if (!open) return null;

  const tiers = ["All", ...new Set(customers.map((c) => c.tier))];
  const visible = customers
    .filter((c) => tier === "All" || c.tier === tier)
    .filter((c) => c.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24"
      style={{ backgroundColor: "rgba(43,36,29,0.35)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg w-full max-w-lg flex flex-col"
        style={{ border: `1px solid ${C.border}`, maxHeight: "70vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="p-5 pb-3"
          style={{ borderBottom: `1px solid ${C.border}` }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold" style={{ color: C.text }}>
              New Quotation
            </h2>
            <button
              onClick={onClose}
              className="text-sm"
              style={{ color: C.muted }}
            >
              Close
            </button>
          </div>

          <input
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search customers…"
            className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150 mb-3"
            style={{ border: `1px solid ${C.border}` }}
          />

          <div className="flex items-center gap-1 flex-wrap">
            {tiers.map((t) => (
              <FilterPill
                key={t}
                active={tier === t}
                onClick={() => setTier(t)}
              >
                {t}
              </FilterPill>
            ))}
          </div>
        </div>

        <div className="overflow-y-auto p-3">
          {visible.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between px-2 py-2.5 rounded-md"
            >
              <div>
                <div className="text-sm font-medium" style={{ color: C.text }}>
                  {c.name}
                </div>
                <div className="text-xs" style={{ color: C.muted }}>
                  {c.tier} pricing
                </div>
              </div>
              <Button variant="secondary" onClick={() => onPick(c)}>
                Start
              </Button>
            </div>
          ))}

          {error && (
            <div
              className="text-sm text-center py-8"
              style={{ color: C.dangerText }}
            >
              {error}
            </div>
          )}

          {!error && visible.length === 0 && (
            <div
              className="text-sm text-center py-8"
              style={{ color: C.muted }}
            >
              No customers match.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
