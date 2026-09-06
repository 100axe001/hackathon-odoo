import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { DealJourney } from "@/components/quotations/DealJourney";
import { C } from "@/constants/theme";
import {
  acceptSplit,
  loadFulfillmentSplit,
  overrideSplit,
  restock,
} from "@/api/api-functions/fulfillment";

export function FulfillmentDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [restocked, setRestocked] = useState(false);
  const [toast, setToast] = useState("");
  // PS section 4 B6 pairs "Accept Suggested Split" with "Manual Override".
  // Override turns the same table editable rather than opening a second screen,
  // so the rep edits the numbers they were just looking at.
  const [override, setOverride] = useState(false);
  useEffect(() => {
    loadFulfillmentSplit(id).then(setDetail).catch(setLoadError);
  }, [id]);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!detail) return null;

  const commit = async () => {
    try {
      if (override) {
        // Only rows the server can attribute to a warehouse are sent; a
        // backorder row has none, and is what the split could not cover.
        const allocations = detail.warehouses
          .filter((w) => w.warehouse_id && w.qty_fulfilled > 0)
          .map((w) => ({
            warehouse_id: w.warehouse_id,
            product_id: w.product_id,
            qty: w.qty_fulfilled,
          }));
        const updated = await overrideSplit(id, allocations);
        setDetail(updated);
        setToast("Manual split saved and stock reserved");
      } else {
        const updated = await acceptSplit(id);
        setDetail(updated);
        setToast(
          updated.complete
            ? "Split accepted and stock reserved"
            : `Split accepted — ${updated.backordered} units on backorder`,
        );
      }
      setOverride(false);
    } catch {
      setToast("Could not save that split.");
    }
  };

  const simulateRestock = async () => {
    try {
      await restock(1, 1, 100);
      const updated = await loadFulfillmentSplit(id);
      setDetail(updated);
      setRestocked(true);
      setToast("Stock arrived — the backorder can now be consolidated");
    } catch {
      setToast("Could not restock.");
    }
  };

  const updateQty = (i, value) => {
    const qty = Math.max(0, Number(value) || 0);
    setDetail((d) => ({
      ...d,
      warehouses: d.warehouses.map((w, idx) =>
        idx === i ? { ...w, qty_fulfilled: qty } : w,
      ),
    }));
  };
  return (
    <Transition keyProp={`fd-${id}`}>
      <DealJourney quotationId={id} />
      <PageHeader
        title={`Fulfillment — ${detail.customer}`}
        subtitle="Which warehouse covers each line, and what is left over."
      />

      {/* The summary the API was already returning and the screen was throwing
          away. Without it the table was a list of quantities with no way to
          tell whether the order was actually covered. */}
      <Card className="mb-6">
        <div className="flex flex-wrap items-end gap-8">
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Shipments
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{ color: C.text }}
            >
              {detail.total_shipments}
            </div>
          </div>
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Shipping cost
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{ color: C.text }}
            >
              ${detail.total_cost}
            </div>
          </div>
          <div>
            <div
              className="text-xs uppercase tracking-wide"
              style={{ color: C.muted }}
            >
              Backordered
            </div>
            <div
              className="text-xl font-semibold tabular-nums"
              style={{
                color: detail.backordered > 0 ? C.dangerText : C.successText,
              }}
            >
              {detail.backordered}
            </div>
          </div>
          <div className="ml-auto text-right">
            <Badge status={detail.status} />
            <div className="text-xs mt-1" style={{ color: C.muted }}>
              {detail.complete
                ? "Every line is covered from stock"
                : `${detail.backordered} unit(s) could not be covered`}
            </div>
          </div>
        </div>
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Suggested Split
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Product</Th>
              <Th>Ships from</Th>
              <Th right>Qty</Th>
              <Th right>Est. shipments</Th>
              <Th right>Cost</Th>
            </tr>
          </thead>
          <tbody>
            {detail.warehouses.map((w, i) => (
              <Tr key={i}>
                <Td>{w.product}</Td>
                <Td>
                  {/* A row with no warehouse is the shortfall - the part of the
                      order nothing could cover. Naming it beats a blank cell. */}
                  {w.warehouse_id === null || !w.warehouse ? (
                    <Badge status="Pending" label="Backorder" />
                  ) : (
                    w.warehouse
                  )}
                </Td>
                <Td right>
                  {override && w.warehouse_id !== null ? (
                    <input
                      type="number"
                      min="0"
                      value={w.qty_fulfilled}
                      onChange={(e) => updateQty(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 70 }}
                    />
                  ) : (
                    w.qty_fulfilled
                  )}
                </Td>
                <Td right style={{ color: C.muted }}>
                  {w.est_shipments}
                </Td>
                <Td right style={{ color: C.muted }}>
                  ${w.cost}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
        {detail.warehouses.length === 0 && (
          <div className="text-sm py-6 text-center" style={{ color: C.muted }}>
            Nothing to split — this quotation has no lines that need shipping.
          </div>
        )}
      </Card>

      <div className="mb-6">
        <InfoBanner
          tone="neutral"
          action={
            <Button variant="secondary" onClick={simulateRestock}>
              Simulate Restock
            </Button>
          }
        >
          {restocked
            ? "East Depot has restocked — a consolidated shipment is now available."
            : "Consolidate Remaining Backorder prompt will appear automatically once East Depot restocks."}
        </InfoBanner>
      </div>

      <div className="flex justify-end gap-3">
        <Button variant="secondary" onClick={() => setOverride((v) => !v)}>
          {override ? "Cancel Override" : "Manual Override"}
        </Button>
        <Button variant="primary" onClick={commit}>
          {override ? "Save Manual Split" : "Accept Suggested Split"}
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
