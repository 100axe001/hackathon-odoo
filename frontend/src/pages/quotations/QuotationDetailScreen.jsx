import { useState, useEffect, useRef } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Select } from "@/components/ui/Select";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import {
  loadQuotationDetail,
  loadUpsells,
  patchDiscount,
} from "@/api/api-functions/quotations";

export function QuotationDetailScreen({ id, setRoute }) {
  const [detail, setDetail] = useState(null);
  const [upsells, setUpsells] = useState([]);
  const [toast, setToast] = useState("");
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

  const submit = () => {
    const hasHighRisk = detail.lines.some((l) => l.status === "OVER");
    if (hasHighRisk) {
      setRoute({ name: "approval-detail", id });
    } else {
      setToast("Auto-approved");
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
            <Button
              variant="secondary"
              onClick={() => addUpsellLine(u)}
              className="mt-1 self-start"
            >
              + Add
            </Button>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm" style={{ color: C.muted }}>
          Estimated margin:{" "}
          <span
            className="font-semibold tabular-nums"
            style={{ color: C.text }}
          >
            ${margin.toFixed(0)}
          </span>
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
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
