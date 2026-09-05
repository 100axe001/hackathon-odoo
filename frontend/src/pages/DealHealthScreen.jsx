import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadDealHealth } from "@/api/api-functions/dealHealth";

export function DealHealthScreen() {
  const navigate = useNavigate();

  // PS section 4 B9: "Clicking an alert opens the related quotation directly".
  // The deal label carries the reference, e.g. "Acme Corp - Q-1042".
  const openDeal = (deal) => {
    const ref = String(deal).split("—").pop().trim().toLowerCase();
    navigate(`/quotations/${ref || "q1"}`);
  };
  const [data, setData] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadDealHealth().then(setData);
  }, []);
  if (!data) return null;
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
              <Tr key={i} onClick={() => openDeal(r.deal)}>
                <Td>{r.deal}</Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {r.issue}
                </Td>
                <Td>{r.flagged}</Td>
                <Td right>
                  <div className="flex justify-end gap-2">
                    {/* Escalate is the louder of the two, per the wireframe. */}
                    <button
                      onClick={() => setToast(`Escalated: ${r.deal}`)}
                      className="text-xs rounded-md px-2.5 py-1 transition-colors duration-150"
                      style={{
                        backgroundColor: C.dangerText,
                        color: "#fff",
                      }}
                    >
                      Escalate
                    </button>
                    <button
                      onClick={() => setToast(`Nudged rep on: ${r.deal}`)}
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
