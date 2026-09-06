import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { loadDashboard } from "@/api/api-functions/dashboard";

export function DashboardScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  useEffect(() => {
    loadDashboard().then(setData).catch(setLoadError);
  }, []);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!data) return null;
  return (
    <Transition keyProp="dashboard">
      <div className="flex flex-col min-h-[calc(100vh-160px)]">
        <PageHeader
          title="Dashboard"
          subtitle="Central hub. Every stat card links through to the module behind it."
          action={
            <div className="flex items-center gap-3">
              <Button
                variant="secondary"
                onClick={() => navigate("/approvals")}
              >
                View Approvals
              </Button>
              {/* The quotations screen owns creation, because a quotation
                  needs a customer before it exists. This used to open a
                  hardcoded "q1", which was somebody else's deal. */}
              <Button
                variant="primary"
                onClick={() =>
                  navigate("/quotations", { state: { newQuotation: true } })
                }
              >
                + New Quotation
              </Button>
            </div>
          }
        />
        <div className="grid grid-cols-3 gap-4 mb-6">
          <StatCard
            label="Pending Approvals"
            value={data.pending_approvals}
            detail={`${data.pending_approvals} quotations waiting on a reviewer`}
            onClick={() => navigate("/approvals")}
          />
          <StatCard
            label="Open Quotations"
            value={data.open_quotations}
            detail={`${data.open_quotations} active deals in the pipeline`}
            onClick={() => navigate("/quotations")}
          />
          <StatCard
            label="At-Risk Deals"
            value={data.at_risk_deals}
            detail={`${data.at_risk_deals} flagged by Deal Health`}
            valueColor={C.dangerText}
            onClick={() => navigate("/deal-health")}
          />
        </div>
        <Card className="flex-1">
          <div
            className="text-base font-semibold mb-3"
            style={{ color: C.text }}
          >
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
      </div>
    </Transition>
  );
}
