import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { ProductPicker } from "@/components/quotations/ProductPicker";
import { C } from "@/constants/theme";
import {
  loadQuotationDetail,
  loadUpsells,
  patchDiscount,
  submitQuotation,
} from "@/api/api-functions/quotations";

export function QuotationDetailScreen() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [upsells, setUpsells] = useState([]);
  const [toast, setToast] = useState("");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [orderDiscount, setOrderDiscount] = useState(0);
  const timers = useRef({});

  useEffect(() => {
    loadQuotationDetail(id).then(setDetail);
    loadUpsells(id).then(setUpsells);
  }, [id]);

  if (!detail) return null;

  const updateQty = (lineId, delta) => {
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) =>
        l.id === lineId ? { ...l, qty: Math.max(1, l.qty + delta) } : l,
      ),
    }));
  };

  const updateDiscount = (lineId, value) => {
    const pct = Math.max(0, Number(value) || 0);
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) =>
        l.id === lineId ? { ...l, discount_pct: pct } : l,
      ),
    }));
    clearTimeout(timers.current[lineId]);
    timers.current[lineId] = setTimeout(async () => {
      const line = detail.lines.find((l) => l.id === lineId);
      const res = await patchDiscount(id, lineId, pct, line.limit_pct);
      setDetail((d) => ({
        ...d,
        lines: d.lines.map((l) =>
          l.id === lineId ? { ...l, status: res.status } : l,
        ),
      }));
    }, 400);
  };

  // PS section 4 B5 pairs "Add to Quote" with "Dismiss" - a rep needs to clear a
  // suggestion that is wrong for this customer without adding it.
  const dismissUpsell = (index) => {
    setUpsells((list) => list.filter((_, i) => i !== index));
  };

  const addCatalogueLine = (product) => {
    setDetail((d) => ({
      ...d,
      lines: [
        ...d.lines,
        {
          id: `l${d.lines.length + 1}-${product.id}`,
          product: product.name,
          qty: 1,
          price: product.price,
          discount_pct: 0,
          limit_pct: product.category === "Services" ? 10 : 15,
          status: "OK",
        },
      ],
    }));
    setToast(`${product.name} added`);
  };

  // PS section 4 B3 allows an order-level discount. It is pushed down onto every
  // line rather than held separately, so each line is still checked against its
  // own ceiling - otherwise an order-level figure would bypass governance.
  const applyOrderDiscount = (value) => {
    const pct = Math.max(0, Number(value) || 0);
    setOrderDiscount(pct);
    setDetail((d) => ({
      ...d,
      lines: d.lines.map((l) => ({
        ...l,
        discount_pct: pct,
        status: pct > l.limit_pct ? "OVER" : "OK",
      })),
    }));
  };

  const addUpsellLine = (product) => {
    const newLine = {
      id: `l${Date.now()}`,
      product: product.product,
      qty: 1,
      price: Math.round(product.margin_delta / 2),
      discount_pct: 0,
      limit_pct: 10,
      status: "OK",
    };
    setDetail((d) => ({ ...d, lines: [...d.lines, newLine] }));
  };

  const margin = detail.lines.reduce(
    (sum, l) => sum + l.qty * l.price * (1 - l.discount_pct / 100) * 0.22,
    0,
  );

  // The backend decides. The client no longer guesses from the line badges -
  // a quote can be routed for approval by the blended path even when no single
  // line looks bad, which the old check could never have caught.
  const submit = async () => {
    try {
      const result = await submitQuotation(id);
      if (result.required_approval.length > 0) {
        setToast(
          `${result.risk_level} risk - routed to ${result.required_approval.join(" then ")}`,
        );
        setTimeout(() => navigate(`/approvals/${id}`), 1200);
      } else {
        setToast("Auto-approved - no approval required");
      }
    } catch {
      setToast("Could not submit. Is the API running?");
    }
  };

  return (
    <Transition keyProp={`qd-${id}`}>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold" style={{ color: C.text }}>
            {detail.customer_name}
          </h1>
          <div className="mt-2" style={{ width: 220 }}>
            <Select
              value={detail.price_list}
              onChange={() => {}}
              options={[detail.price_list, "Standard Retail", "VIP Contract"]}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between mb-3">
        <div className="text-base font-semibold" style={{ color: C.text }}>
          Order Lines
        </div>
        <Button variant="secondary" onClick={() => setPickerOpen(true)}>
          + Add Product
        </Button>
      </div>

      <Card className="mb-6">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th right>Qty</Th>
              <Th right>Price</Th>
              <Th right>Discount</Th>
              <Th right>Limit</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((line) => (
              <Tr key={line.id}>
                <Td>{line.product}</Td>
                <Td right>
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => updateQty(line.id, -1)}
                      className="rounded-md w-6 h-6 text-sm transition-colors duration-150"
                      style={{ border: `1px solid ${C.border}`, color: C.text }}
                    >
                      −
                    </button>
                    <span
                      className="tabular-nums"
                      style={{ minWidth: 24, textAlign: "center" }}
                    >
                      {line.qty}
                    </span>
                    <button
                      onClick={() => updateQty(line.id, 1)}
                      className="rounded-md w-6 h-6 text-sm transition-colors duration-150"
                      style={{ border: `1px solid ${C.border}`, color: C.text }}
                    >
                      +
                    </button>
                  </div>
                </Td>
                <Td right>${line.price.toLocaleString()}</Td>
                <Td right>
                  <div className="flex items-center justify-end gap-1">
                    <input
                      type="number"
                      value={line.discount_pct}
                      onChange={(e) => updateDiscount(line.id, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 56 }}
                    />
                    <span className="text-sm" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
                <Td right className="text-xs" style={{ color: C.muted }}>
                  {line.limit_pct}%
                </Td>
                <Td>
                  <Badge
                    status={line.status}
                    label={
                      line.status === "OVER"
                        ? `OVER (+${(line.discount_pct - line.limit_pct).toFixed(0)}pt)`
                        : "OK"
                    }
                  />
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mb-3 text-base font-semibold" style={{ color: C.text }}>
        Suggested Upsells
      </div>
      <div className="grid grid-cols-3 gap-4 mb-6">
        {upsells.map((u, i) => (
          <div
            key={i}
            className="rounded-lg p-4 bg-white flex flex-col gap-2"
            style={{ border: `1px dashed ${C.border}` }}
          >
            <div className="text-sm font-medium" style={{ color: C.text }}>
              {u.product}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                status="OK"
                label={`Margin +$${u.margin_delta.toLocaleString()}`}
              />
              {u.promo_tag && <Badge status="Pending" label={u.promo_tag} />}
            </div>
            <div className="flex items-center gap-2 mt-1">
              <Button variant="secondary" onClick={() => addUpsellLine(u)}>
                Add to Quote
              </Button>
              <button
                onClick={() => dismissUpsell(i)}
                className="text-xs px-2 py-1 transition-colors duration-150"
                style={{ color: C.muted }}
              >
                Dismiss
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="text-sm" style={{ color: C.muted }}>
              Order discount
            </span>
            <input
              type="number"
              value={orderDiscount}
              onChange={(e) => applyOrderDiscount(e.target.value)}
              className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
              style={{ border: `1px solid ${C.border}`, width: 60 }}
            />
            <span className="text-sm" style={{ color: C.muted }}>
              %
            </span>
          </div>
          <div className="text-sm" style={{ color: C.muted }}>
            Estimated margin:{" "}
            <span
              className="font-semibold tabular-nums"
              style={{ color: C.text }}
            >
              ${margin.toFixed(0)}
            </span>
          </div>
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={() => setToast("Draft saved")}>
            Save Draft
          </Button>
          <Button variant="primary" onClick={submit}>
            Submit for Approval
          </Button>
        </div>
      </div>
      <ProductPicker
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onAdd={addCatalogueLine}
      />
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
