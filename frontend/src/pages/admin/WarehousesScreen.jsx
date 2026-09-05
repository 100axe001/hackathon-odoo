import { useState, useEffect } from "react";
import { AdminTabs } from "@/components/admin/AdminTabs";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadWarehouses } from "@/api/api-functions/admin";

export function WarehousesScreen() {
  const [rows, setRows] = useState([]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    loadWarehouses().then(setRows);
  }, []);

  const update = (i, field, value) => {
    setRows((list) =>
      list.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)),
    );
  };

  const addRow = () =>
    setRows((list) => [
      ...list,
      {
        id: `w${list.length + 1}`,
        name: "New Warehouse",
        region: "",
        shipping_cost_weight: 1.0,
        active: true,
      },
    ]);

  return (
    <Transition keyProp="warehouses">
      <PageHeader
        title="Warehouses"
        subtitle="Stock locations and the shipping cost weighting the auto-split logic uses to minimise shipments."
        action={
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={addRow}>
              + Add Warehouse
            </Button>
            <Button
              variant="primary"
              onClick={() => setToast("Warehouse configuration saved")}
            >
              Save Configuration
            </Button>
          </div>
        }
      />
      <AdminTabs />

      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Warehouse</Th>
              <Th>Region</Th>
              <Th right>Shipping Cost Weight</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((w, i) => (
              <Tr key={w.id}>
                <Td>
                  <input
                    value={w.name}
                    onChange={(e) => update(i, "name", e.target.value)}
                    className="rounded-md px-2 py-1 text-sm outline-none transition-all duration-150 w-full"
                    style={{ border: `1px solid ${C.border}` }}
                  />
                </Td>
                <Td>
                  <input
                    value={w.region}
                    onChange={(e) => update(i, "region", e.target.value)}
                    className="rounded-md px-2 py-1 text-sm outline-none transition-all duration-150 w-full"
                    style={{ border: `1px solid ${C.border}` }}
                  />
                </Td>
                <Td right>
                  <input
                    type="number"
                    step="0.1"
                    value={w.shipping_cost_weight}
                    onChange={(e) =>
                      update(i, "shipping_cost_weight", Number(e.target.value))
                    }
                    className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                    style={{ border: `1px solid ${C.border}`, width: 80 }}
                  />
                </Td>
                <Td>
                  <button onClick={() => update(i, "active", !w.active)}>
                    <Badge
                      status={w.active ? "Active" : "Paused"}
                      label={w.active ? "Active" : "Inactive"}
                    />
                  </button>
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <p className="text-xs mt-4" style={{ color: C.muted }}>
        A lower weight makes a warehouse cheaper to ship from. The split
        algorithm minimises shipment count first, then total weighted cost.
      </p>

      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
