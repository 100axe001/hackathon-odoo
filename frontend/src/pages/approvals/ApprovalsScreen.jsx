import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatPill } from "@/components/ui/StatPill";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadApprovals } from "@/api/api-functions/approvals";

export function ApprovalsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  const [pendingOnly, setPendingOnly] = useState(true);
  useEffect(() => {
    loadApprovals().then(setData);
  }, []);
  return (
    <Transition keyProp="approvals">
      <PageHeader title="Approvals" />
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-3">
          <StatPill label="Pending" count={data.length} tone="warn" />
          <StatPill label="Returned" count={2} tone="neutral" />
          <StatPill label="Approved" count={11} tone="success" />
        </div>
        <label
          className="flex items-center gap-2 text-sm"
          style={{ color: C.text }}
        >
          <input
            type="checkbox"
            checked={pendingOnly}
            onChange={(e) => setPendingOnly(e.target.checked)}
          />
          Pending Only
        </label>
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
                <Td>{a.assigned_to}</Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
