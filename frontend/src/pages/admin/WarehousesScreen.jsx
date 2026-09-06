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
import {
  deleteWarehouse,
  loadWarehouses,
  saveWarehouses,
} from "@/api/api-functions/admin";

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

  // A row the server has never seen just disappears. A saved one is deleted
  // there, and the server decides whether it may go - a warehouse that has
  // shipped stays, and says so.
  const remove = async (warehouse, index) => {
    if (!warehouse.id) {
      setRows((list) => list.filter((_, i) => i !== index));
      return;
    }
    try {
      setRows(await deleteWarehouse(warehouse.id));
      setToast(`${warehouse.name} removed`);
    } catch (err) {
      setToast(err.detail || "Could not remove that warehouse.");
    }
  };

  const addRow = () =>
    setRows((list) => [
      ...list,
      {
        // No id: this row does not exist yet, and inventing "w6" made the
        // whole save fail validation - which the screen then blamed on the
        // user's role.
        id: null,
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
        subtitle="Stock locations, what each is holding, and the shipping cost weighting the auto-split logic uses to minimise shipments."
        action={
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={addRow}>
              + Add Warehouse
            </Button>
            <Button
              variant="primary"
              onClick={async () => {
                try {
                  const saved = await saveWarehouses(rows);
                  setRows(saved);
                  setToast("Warehouse configuration saved");
                } catch (err) {
                  setToast(
                    err.status === 403
                      ? "Only an admin may change this configuration."
                      : err.detail || "Could not save these warehouses.",
                  );
                }
              }}
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
              <Th right>Products</Th>
              <Th right>On hand</Th>
              <Th right>Available</Th>
              <Th>Stock health</Th>
              <Th right>Lines shipped</Th>
              <Th>Status</Th>
              <Th right>Remove</Th>
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
                <Td right>{w.product_lines}</Td>
                <Td right style={{ color: C.muted }}>
                  {w.units_on_hand.toLocaleString()}
                </Td>
                <Td right>{w.units_available.toLocaleString()}</Td>
                <Td>
                  {/* Reserved stock is spoken for, so a depot can look full and
                      still have nothing to promise. */}
                  {w.product_lines === 0 ? (
                    <span className="text-xs" style={{ color: C.muted }}>
                      Nothing stocked
                    </span>
                  ) : w.below_reorder > 0 ? (
                    <Badge
                      status="Pending"
                      label={`${w.below_reorder} below reorder`}
                    />
                  ) : (
                    <span className="text-xs" style={{ color: C.muted }}>
                      {w.units_reserved.toLocaleString()} reserved
                    </span>
                  )}
                </Td>
                <Td right style={{ color: C.muted }}>
                  {w.fulfilled_lines}
                </Td>
                <Td>
                  <button onClick={() => update(i, "active", !w.active)}>
                    <Badge
                      status={w.active ? "Active" : "Paused"}
                      label={w.active ? "Active" : "Inactive"}
                    />
                  </button>
                </Td>
                <Td right>
                  <button
                    onClick={() => remove(w, i)}
                    className="text-xs rounded-md px-2 py-1 transition-colors duration-150"
                    style={{
                      color: C.dangerText,
                      border: `1px solid ${C.border}`,
                    }}
                  >
                    Remove
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
