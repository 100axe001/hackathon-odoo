import { useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadFulfillmentSplit } from "@/api/api-functions/fulfillment";

export function FulfillmentDetailScreen() {
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [restocked, setRestocked] = useState(false);
  const [toast, setToast] = useState("");
  // PS section 4 B6 pairs "Accept Suggested Split" with "Manual Override".
  // Override turns the same table editable rather than opening a second screen,
  // so the rep edits the numbers they were just looking at.
  const [override, setOverride] = useState(false);
  useEffect(() => {
    loadFulfillmentSplit(id).then(setDetail);
  }, [id]);
  if (!detail) return null;

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
      <PageHeader title={`Fulfillment — ${detail.customer}`} />
      <Card className="mb-6">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Warehouse</Th>
              <Th right>Qty Fulfilled</Th>
              <Th right>Est. Shipments</Th>
              <Th right>Cost</Th>
            </tr>
          </thead>
          <tbody>
            {detail.warehouses.map((w, i) => (
              <Tr key={i}>
                <Td>{w.warehouse}</Td>
                <Td right>
                  {override ? (
                    <input
                      type="number"
                      value={w.qty_fulfilled}
                      onChange={(e) => updateQty(i, e.target.value)}
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                      style={{ border: `1px solid ${C.border}`, width: 70 }}
                    />
                  ) : (
                    w.qty_fulfilled
                  )}
                </Td>
                <Td right>{w.est_shipments}</Td>
                <Td right>${w.cost}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="mb-6">
        <InfoBanner
          tone="neutral"
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setRestocked(true);
                setToast("East Depot restocked — split updated");
              }}
            >
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
        <Button
          variant="secondary"
          onClick={() => setToast("Manual override opened")}
        >
          {override ? "Cancel Override" : "Manual Override"}
        </Button>
        <Button
          variant="primary"
          onClick={() => {
            setToast(override ? "Manual split saved" : "Split accepted");
            setOverride(false);
          }}
        >
          {override ? "Save Manual Split" : "Accept Suggested Split"}
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
