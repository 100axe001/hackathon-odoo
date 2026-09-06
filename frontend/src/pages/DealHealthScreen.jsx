import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import {
  escalateFlag,
  loadDealHealth,
  nudgeFlag,
} from "@/api/api-functions/dealHealth";

export function DealHealthScreen() {
  const navigate = useNavigate();

  // PS section 4 B9: "Clicking an alert opens the related quotation directly".
  // The API carries quotation_id, so this no longer parses it back out of the
  // display label - which broke the moment a customer name contained a dash.
  const openDeal = (row) => navigate(`/quotations/${row.quotation_id}`);
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadDealHealth().then(setData).catch(setLoadError);
  }, []);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!data) return null;
  const refresh = () => loadDealHealth().then(setData);

  const act = async (row, kind) => {
    try {
      await (kind === "escalate" ? escalateFlag(row.id) : nudgeFlag(row.id));
      setToast(
        kind === "escalate"
          ? `Escalated: ${row.deal}`
          : `Nudged the rep on ${row.deal}`,
      );
      refresh();
    } catch {
      setToast("Could not record that action.");
    }
  };

  const rows = [
    ...data.stalled.map((d) => ({ ...d, category: "Stalled" })),
    ...data.anomalies.map((d) => ({ ...d, category: "Anomaly" })),
    ...data.slippage.map((d) => ({ ...d, category: "Slippage" })),
  ];
  return (
    <Transition keyProp="deal-health">
      <PageHeader title="Deal Health" />
      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard
          label="Stalled Deals"
          value={data.stalled.length}
          valueColor={C.warnText}
        />
        <StatCard
          label="Discount Anomalies"
          value={data.anomalies.length}
          valueColor={C.dangerText}
        />
        <StatCard
          label="Delivery Slippage"
          value={data.slippage.length}
          valueColor={C.warnText}
        />
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Deal</Th>
              <Th>Issue</Th>
              <Th>Flagged</Th>
              <Th right>Action</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <Tr key={i} onClick={() => openDeal(r)}>
                <Td>{r.deal}</Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {r.issue}
                </Td>
                <Td>{r.flagged}</Td>
                <Td right>
                  <div className="flex justify-end gap-2">
                    {/* Escalate is the louder of the two, per the wireframe. */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        act(r, "escalate");
                      }}
                      className="text-xs rounded-md px-2.5 py-1 transition-colors duration-150"
                      style={{
                        backgroundColor: C.dangerText,
                        color: "#fff",
                      }}
                    >
                      Escalate
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        act(r, "nudge");
                      }}
                      className="text-xs rounded-md px-2.5 py-1 transition-colors duration-150"
                      style={{ backgroundColor: C.accent, color: "#fff" }}
                    >
                      Nudge Rep
                    </button>
                  </div>
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
