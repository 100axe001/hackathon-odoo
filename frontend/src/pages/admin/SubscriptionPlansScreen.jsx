import { useState, useEffect } from "react";
import { AdminTabs } from "@/components/admin/AdminTabs";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import {
  deleteSubscriptionPlan,
  loadSubscriptionPlans,
  saveSubscriptionPlans,
} from "@/api/api-functions/admin";

const CYCLES = ["Weekly", "Monthly", "Quarterly", "Yearly"];

export function SubscriptionPlansScreen() {
  const [rows, setRows] = useState([]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    loadSubscriptionPlans().then(setRows);
  }, []);

  const update = (i, field, value) => {
    setRows((list) =>
      list.map((r, idx) => (idx === i ? { ...r, [field]: value } : r)),
    );
  };

  // Unsaved rows just disappear. A saved plan is deleted on the server, which
  // refuses while anything is still subscribed to it.
  const remove = async (plan, index) => {
    if (!plan.id) {
      setRows((list) => list.filter((_, i) => i !== index));
      return;
    }
    try {
      setRows(await deleteSubscriptionPlan(plan.id));
      setToast(`${plan.name} removed`);
    } catch (err) {
      setToast(err.detail || "Could not remove that plan.");
    }
  };

  const addRow = () =>
    setRows((list) => [
      ...list,
      {
        id: null,
        name: "New Plan",
        cycle: "Monthly",
        price: 0,
        proration_enabled: true,
        refund_window_days: 365,
        cancellation_fee_pct: 0,
      },
    ]);

  return (
    <Transition keyProp="subscription-plans">
      <PageHeader
        title="Subscription Plans"
        subtitle="Recurring plans that can be attached to a product, with the proration rule applied on mid-cycle changes."
        action={
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={addRow}>
              + Add Plan
            </Button>
            <Button
              variant="primary"
              onClick={async () => {
                try {
                  const saved = await saveSubscriptionPlans(rows);
                  setRows(saved);
                  setToast("Plan configuration saved");
                } catch (err) {
                  setToast(
                    err.status === 403
                      ? "Only an admin may change this configuration."
                      : err.detail || "Could not save these plans.",
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
              <Th>Plan</Th>
              <Th>Billing Cycle</Th>
              <Th right>Price</Th>
              <Th>Proration</Th>
              <Th right>Refund window</Th>
              <Th right>Cancel fee</Th>
              <Th right>Remove</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <Tr key={p.id ?? `new-${i}`}>
                <Td>
                  <input
                    value={p.name}
                    onChange={(e) => update(i, "name", e.target.value)}
                    className="rounded-md px-2 py-1 text-sm outline-none transition-all duration-150 w-full"
                    style={{ border: `1px solid ${C.border}` }}
                  />
                </Td>
                <Td>
                  <div style={{ width: 150 }}>
                    <Select
                      value={p.cycle}
                      onChange={(e) => update(i, "cycle", e.target.value)}
                      options={CYCLES}
                    />
                  </div>
                </Td>
                <Td right>
                  <input
                    type="number"
                    value={p.price}
                    onChange={(e) => update(i, "price", Number(e.target.value))}
                    className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none transition-all duration-150"
                    style={{ border: `1px solid ${C.border}`, width: 90 }}
                  />
                </Td>
                <Td>
                  <button
                    onClick={() =>
                      update(i, "proration_enabled", !p.proration_enabled)
                    }
                  >
                    <Badge
                      status={p.proration_enabled ? "Active" : "Draft"}
                      label={p.proration_enabled ? "Prorated" : "Full period"}
                    />
                  </button>
                </Td>
                <Td right>
                  <div className="flex justify-end items-center gap-1">
                    <input
                      type="number"
                      min="0"
                      value={p.refund_window_days ?? 365}
                      onChange={(e) =>
                        update(
                          i,
                          "refund_window_days",
                          Math.max(0, Number(e.target.value) || 0),
                        )
                      }
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none"
                      style={{ border: `1px solid ${C.border}`, width: 70 }}
                    />
                    <span className="text-xs" style={{ color: C.muted }}>
                      days
                    </span>
                  </div>
                </Td>
                <Td right>
                  <div className="flex justify-end items-center gap-1">
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={p.cancellation_fee_pct ?? 0}
                      onChange={(e) =>
                        update(
                          i,
                          "cancellation_fee_pct",
                          Math.max(0, Number(e.target.value) || 0),
                        )
                      }
                      className="rounded-md px-2 py-1 text-sm text-right tabular-nums outline-none"
                      style={{ border: `1px solid ${C.border}`, width: 60 }}
                    />
                    <span className="text-xs" style={{ color: C.muted }}>
                      %
                    </span>
                  </div>
                </Td>
                <Td right>
                  <button
                    onClick={() => remove(p, i)}
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
        Prorated plans charge remaining_days / cycle_days of the price delta
        when quantity or plan changes mid-cycle. Cancelling inside the refund
        window raises a credit note for the unused remainder, less the
        cancellation fee; past the window, no credit is due.
      </p>

      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
