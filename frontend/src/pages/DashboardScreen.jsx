import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadDashboard } from "@/api/api-functions/dashboard";

export function DashboardScreen({ setRoute }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    loadDashboard().then(setData);
  }, []);
  if (!data) return null;
  return (
    <Transition keyProp="dashboard">
      <PageHeader
        title="Dashboard"
        action={
          <Button
            variant="primary"
            onClick={() => setRoute({ name: "quotation-detail", id: "q1" })}
          >
            + New Quotation
          </Button>
        }
      />
      <div className="grid grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Pending Approvals"
          value={data.pending_approvals}
          onClick={() => setRoute({ name: "approvals", id: null })}
        />
        <StatCard
          label="Open Quotations"
          value={data.open_quotations}
          onClick={() => setRoute({ name: "quotations", id: null })}
        />
        <StatCard
          label="At-Risk Deals"
          value={data.at_risk_deals}
          valueColor={C.dangerText}
          onClick={() => setRoute({ name: "deal-health", id: null })}
        />
      </div>
      <Card>
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Recent Activity
        </div>
        <div className="flex flex-col">
          {data.recent_activity.map((a) => (
            <div
              key={a.id}
              className="flex items-center justify-between py-2.5 border-b last:border-0"
              style={{ borderColor: C.border }}
            >
              <div className="flex items-center gap-3">
                <span
                  className="rounded-full"
                  style={{
                    width: 6,
                    height: 6,
                    backgroundColor: C.accent,
                    display: "inline-block",
                  }}
                />
                <span className="text-sm" style={{ color: C.text }}>
                  {a.text}
                </span>
              </div>
              <span className="text-xs" style={{ color: C.muted }}>
                {a.timestamp}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </Transition>
  );
}
