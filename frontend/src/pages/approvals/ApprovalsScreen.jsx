import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatPill } from "@/components/ui/StatPill";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { loadApprovals } from "@/api/api-functions/approvals";

export function ApprovalsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [loadError, setLoadError] = useState(null);
  useEffect(() => {
    loadApprovals().then(setData).catch(setLoadError);
  }, []);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );

  // Counted from the queue itself. The old Returned and Approved pills showed
  // 2 and 11 whatever the data said, and the endpoint returns the pending set
  // only, so there was nothing behind either number.
  const atRisk = (level) => data.filter((a) => a.blended_risk === level).length;

  return (
    <Transition keyProp="approvals">
      <PageHeader title="Approvals" />
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-3">
          <StatPill label="Pending" count={data.length} tone="warn" />
          <StatPill label="High risk" count={atRisk("HIGH")} tone="danger" />
          <StatPill
            label="Medium risk"
            count={atRisk("MEDIUM")}
            tone="neutral"
          />
        </div>
        {/* The queue is everything awaiting a reviewer - there is no other
            filter to offer, and the checkbox that claimed one never had a
            second set of rows to switch to. */}
        <span className="text-sm" style={{ color: C.muted }}>
          Everything currently awaiting a reviewer
        </span>
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Quotation</Th>
              <Th>Customer</Th>
              <Th>Blended Risk</Th>
              <Th>Stage</Th>
              <Th>Assigned To</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((a) => (
              <Tr key={a.id} onClick={() => navigate(`/approvals/${a.id}`)}>
                <Td>{a.quotation}</Td>
                <Td>{a.customer}</Td>
                <Td>
                  <Badge status={a.blended_risk} />
                </Td>
                <Td>{a.stage}</Td>
                <Td>
                  {a.assigned_to}
                  {/* Yours is here to be watched, not acted on - the decision
                      endpoint refuses a reviewer their own quotation. */}
                  {a.own && (
                    <span className="ml-2">
                      <Badge status="Pending" label="Yours" />
                    </span>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
