import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { FilterPill } from "@/components/ui/FilterPill";
import { C } from "@/constants/theme";
import { loadProducts } from "@/api/api-functions/products";

// PS section 4 B3: "Pick products across categories (Hardware, Services,
// Subscriptions)". Without this a rep can only add lines from the upsell panel,
// which is a suggestion feed rather than the catalogue.
export function ProductPicker({ open, onClose, onAdd }) {
  const [products, setProducts] = useState([]);
  const [category, setCategory] = useState("All");
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (open) loadProducts().then(setProducts);
  }, [open]);

  if (!open) return null;

  const categories = ["All", ...new Set(products.map((p) => p.category))];
  const visible = products
    .filter((p) => p.status !== "Discontinued")
    .filter((p) => category === "All" || p.category === category)
    .filter((p) => p.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-24"
      style={{ backgroundColor: "rgba(43,36,29,0.35)" }}
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg w-full max-w-2xl flex flex-col"
        style={{ border: `1px solid ${C.border}`, maxHeight: "70vh" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="p-5 pb-3"
          style={{ borderBottom: `1px solid ${C.border}` }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold" style={{ color: C.text }}>
              Add Product
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
            placeholder="Search the catalogue…"
            className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150 mb-3"
            style={{ border: `1px solid ${C.border}` }}
          />

          <div className="flex items-center gap-1 flex-wrap">
            {categories.map((c) => (
              <FilterPill
                key={c}
                active={category === c}
                onClick={() => setCategory(c)}
              >
                {c}
              </FilterPill>
            ))}
          </div>
        </div>

        <div className="overflow-y-auto p-3">
          {visible.map((p) => (
            <div
              key={p.id}
              className="flex items-center justify-between px-2 py-2.5 rounded-md"
            >
              <div>
                <div className="text-sm font-medium" style={{ color: C.text }}>
                  {p.name}
                </div>
                <div className="text-xs" style={{ color: C.muted }}>
                  {p.category} · ${p.price.toLocaleString()} / {p.unit}
                </div>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  onAdd(p);
                  onClose();
                }}
              >
                Add
              </Button>
            </div>
          ))}

          {visible.length === 0 && (
            <div
              className="text-sm text-center py-8"
              style={{ color: C.muted }}
            >
              No products match.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
