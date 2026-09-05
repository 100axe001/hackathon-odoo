import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { loadFulfillmentSplit } from "@/api/api-functions/fulfillment";

export function FulfillmentDetailScreen({ id }) {
  const [detail, setDetail] = useState(null);
  const [restocked, setRestocked] = useState(false);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadFulfillmentSplit(id).then(setDetail);
  }, [id]);
  if (!detail) return null;
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
                <Td right>{w.qty_fulfilled}</Td>
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
          Manual Override
        </Button>
        <Button variant="primary" onClick={() => setToast("Split accepted")}>
          Accept Suggested Split
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
