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
import { loadSubscriptionPlans } from "@/api/api-functions/admin";

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

  const addRow = () =>
    setRows((list) => [
      ...list,
      {
        id: `p${list.length + 1}`,
        name: "New Plan",
        cycle: "Monthly",
        price: 0,
        proration_enabled: true,
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
              onClick={() => setToast("Plan configuration saved")}
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
            </tr>
          </thead>
          <tbody>
            {rows.map((p, i) => (
              <Tr key={p.id}>
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
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <p className="text-xs mt-4" style={{ color: C.muted }}>
        Prorated plans charge remaining_days / cycle_days of the price delta
        when quantity or plan changes mid-cycle. Cancellation raises a credit
        note for the unused remainder.
      </p>

      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
