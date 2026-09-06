import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { FilterPill } from "@/components/ui/FilterPill";
import { Input } from "@/components/ui/Input";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import {
  createProduct,
  loadProductDetail,
  saveProduct,
} from "@/api/api-functions/products";

// The detail view renders tax as "8%" and prices under display names; the PUT
// takes the column names. One mapping, so the two cannot drift apart.
function toForm(detail) {
  return {
    name: detail.name,
    category: detail.category,
    unit_price: detail.price,
    cost_price: detail.cost_price ?? 0,
    unit: detail.unit,
    tax_pct: parseFloat(detail.tax) || 0,
    description: detail.description ?? "",
    is_subscription: detail.subscription,
    recurring_cycle: detail.cadence,
  };
}

// An empty product, in the shape the detail endpoint returns, so the form and
// every card below it render the same way whether creating or editing.
const BLANK = {
  id: "new",
  name: "",
  // Empty, not "Hardware": a prefilled category is a claim about a product
  // nobody has described yet, and it saves silently if left alone.
  category: "",
  price: 0,
  cost_price: 0,
  unit: "Each",
  tax: "0%",
  description: "",
  subscription: false,
  cadence: null,
  qty_on_hand: 0,
  variants: [],
  pricelists: [],
  stock: [],
  total_available: 0,
};

export function ProductDetailScreen() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [form, setForm] = useState(null);
  const [toast, setToast] = useState("");

  // "new" is a product that does not exist yet. The form is the same either
  // way, because the fields a product has do not change between being created
  // and being corrected.
  const creating = id === "new";

  useEffect(() => {
    if (creating) {
      setDetail(BLANK);
      setForm(toForm(BLANK));
      return;
    }
    loadProductDetail(id)
      .then((data) => {
        setDetail(data);
        setForm(toForm(data));
      })
      .catch(setLoadError);
  }, [id, creating]);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!detail) return null;

  const update = (field, value) => setForm((f) => ({ ...f, [field]: value }));

  const save = async () => {
    if (!form.name.trim()) {
      setToast("Give the product a name first");
      return;
    }
    if (!form.category.trim()) {
      setToast("Give the product a category first");
      return;
    }
    try {
      const saved = creating
        ? await createProduct(form)
        : await saveProduct(id, form);
      setDetail(saved);
      setForm(toForm(saved));
      setToast(creating ? "Product added" : "Product saved");
      // Move onto the real record, so a second save edits rather than
      // creating the same product again.
      if (creating) navigate(`/products/${saved.id}`, { replace: true });
    } catch (e) {
      // The backend owns the rules — report its verdict rather than restating
      // which edits are allowed.
      setToast(
        e.status === 403
          ? "Only an admin may change the catalogue."
          : `Could not save this product (${e.message}).`,
      );
    }
  };

  return (
    <Transition keyProp={`pd-${id}`}>
      <PageHeader title={detail.name} />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-4" style={{ color: C.text }}>
          General Info
        </div>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Product Name
            </label>
            <Input
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Category
            </label>
            <Input
              value={form.category}
              onChange={(e) => update("category", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Price
            </label>
            <Input
              type="number"
              value={form.unit_price}
              onChange={(e) => update("unit_price", Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Cost Price
            </label>
            <Input
              type="number"
              value={form.cost_price}
              onChange={(e) => update("cost_price", Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Unit
            </label>
            <Input
              value={form.unit}
              onChange={(e) => update("unit", e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Tax %
            </label>
            <Input
              type="number"
              value={form.tax_pct}
              onChange={(e) => update("tax_pct", Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-sm mb-1 block" style={{ color: C.text }}>
              Quantity on Hand
            </label>
            {/* Stock moves through fulfillment, so it is shown, not edited. */}
            <Input type="number" value={detail.qty_on_hand} readOnly />
          </div>
        </div>
        <div className="mb-4">
          <label className="text-sm mb-1 block" style={{ color: C.text }}>
            Description
          </label>
          <textarea
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
            rows={3}
            className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150"
            style={{ border: `1px solid ${C.border}` }}
          />
        </div>
        <SubscriptionToggle
          isSub={form.is_subscription}
          cadence={form.recurring_cycle}
          onChange={update}
        />
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Product Variants
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Attribute</Th>
              <Th>Values</Th>
              <Th right>Extra Price</Th>
            </tr>
          </thead>
          <tbody>
            {detail.variants.map((v, i) => (
              <Tr key={i}>
                <Td>{v.attribute}</Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {v.values}
                </Td>
                <Td right>{v.extra_price ? `+$${v.extra_price}` : "—"}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* Where the stock actually sits. qty_on_hand alone is one number that
          cannot answer "can this ship from a single warehouse", which is the
          question the split logic exists to settle. */}
      <Card className="mb-6">
        <div className="flex items-baseline justify-between mb-3">
          <div className="text-base font-semibold" style={{ color: C.text }}>
            Stock by Warehouse
          </div>
          <div className="text-sm" style={{ color: C.muted }}>
            <span className="font-semibold" style={{ color: C.text }}>
              {detail.total_available}
            </span>{" "}
            available across active warehouses
          </div>
        </div>
        {(detail.stock ?? []).length === 0 ? (
          <div className="text-sm py-4" style={{ color: C.muted }}>
            Not stocked anywhere yet. Add stock against a warehouse in Back-end
            → Warehouses.
          </div>
        ) : (
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Warehouse</Th>
                <Th>Region</Th>
                <Th right>On hand</Th>
                <Th right>Reserved</Th>
                <Th right>Available</Th>
                <Th right>Reorder at</Th>
                <Th>Condition</Th>
              </tr>
            </thead>
            <tbody>
              {detail.stock.map((row, i) => (
                <Tr key={i}>
                  <Td>{row.warehouse}</Td>
                  <Td style={{ color: C.muted }}>{row.region || "—"}</Td>
                  <Td right>{row.on_hand}</Td>
                  <Td right style={{ color: C.muted }}>
                    {row.reserved}
                  </Td>
                  <Td
                    right
                    style={{
                      color: row.available === 0 ? C.dangerText : C.text,
                      fontWeight: row.available === 0 ? 600 : 400,
                    }}
                  >
                    {row.available}
                  </Td>
                  <Td right style={{ color: C.muted }}>
                    {row.reorder_point > 0 ? row.reorder_point : "—"}
                  </Td>
                  <Td>
                    {/* Inactive first: stock in a depot the split skips is not
                        available to promise, whatever the number says. */}
                    {!row.active ? (
                      <Badge status="Cancelled" label="Warehouse inactive" />
                    ) : row.needs_restock ? (
                      <Badge
                        status="Pending"
                        label={`Below reorder — order ${row.reorder_qty}`}
                      />
                    ) : (
                      <span className="text-xs" style={{ color: C.muted }}>
                        {row.reorder_point > 0 ? "In policy" : "No rule set"}
                      </span>
                    )}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Pricelists
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Tier</Th>
              <Th>Currency</Th>
              <Th>Price Rule</Th>
            </tr>
          </thead>
          <tbody>
            {detail.pricelists.map((p, i) => (
              <Tr key={i}>
                <Td>{p.tier}</Td>
                <Td>{p.currency}</Td>
                {/* The backend calls it `rule`; the sample data predates it. */}
                <Td>{p.rule}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <div className="flex justify-end">
        <Button variant="primary" onClick={save}>
          {creating ? "Add Product" : "Save Changes"}
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}

export function SubscriptionToggle({ isSub, cadence, onChange }) {
  return (
    <div>
      <label className="text-sm mb-1 block" style={{ color: C.text }}>
        Subscription Product
      </label>
      <div className="flex gap-2 mb-2">
        <FilterPill
          active={isSub}
          onClick={() => {
            onChange("is_subscription", true);
            // The Select below already shows Monthly when there is no cadence;
            // send that value too, so what is displayed is what gets saved.
            if (!cadence) onChange("recurring_cycle", "Monthly");
          }}
        >
          Yes
        </FilterPill>
        <FilterPill
          active={!isSub}
          onClick={() => onChange("is_subscription", false)}
        >
          No
        </FilterPill>
      </div>
      <div
        className="overflow-hidden transition-all duration-200"
        style={{ maxHeight: isSub ? 80 : 0, opacity: isSub ? 1 : 0 }}
      >
        <label className="text-sm mb-1 block" style={{ color: C.text }}>
          Billing Cadence
        </label>
        <div style={{ width: 200 }}>
          <Select
            value={cadence ?? "Monthly"}
            onChange={(e) => onChange("recurring_cycle", e.target.value)}
            /* The four cycles the billing engine prorates. Omitting Weekly
               meant a weekly product rendered with no matching option and was
               saved back as Monthly. */
            options={["Weekly", "Monthly", "Quarterly", "Yearly"]}
          />
        </div>
      </div>
    </div>
  );
}
