import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Stepper } from "@/components/ui/Stepper";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadApprovalDetail } from "@/api/api-functions/approvals";

export function ApprovalDetailScreen() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [toast, setToast] = useState("");
  useEffect(() => {
    loadApprovalDetail(id).then(setDetail);
  }, [id]);
  if (!detail) return null;

  const worst = detail.lines.reduce(
    (a, b) => (b.over_by > a.over_by ? b : a),
    detail.lines[0],
  );
  const stageIndex = [
    "Submitted",
    "Sales Manager",
    "Finance",
    "Confirmed",
  ].indexOf(detail.stage);

  const decide = (decision) => {
    setToast(`Decision recorded: ${decision}`);
    setTimeout(() => navigate("/approvals"), 900);
  };

  return (
    <Transition keyProp={`ad-${id}`}>
      <PageHeader title={`${detail.quotation} — ${detail.customer}`} />
      <div className="flex gap-2 mb-6">
        <Badge
          status={detail.blended_risk}
          label={`Blended Risk: ${detail.blended_risk}`}
        />
        <Badge status="OK" label={`Customer Tier: ${detail.customer_tier}`} />
      </div>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Why This Quote Was Flagged
        </div>
        <table className="w-full border-collapse mb-3">
          <thead>
            <tr>
              <Th>Line</Th>
              <Th right>Discount Given</Th>
              <Th right>Limit Allowed</Th>
              <Th right>Over By</Th>
            </tr>
          </thead>
          <tbody>
            {detail.lines.map((l, i) => (
              <Tr key={i}>
                <Td>{l.line}</Td>
                <Td right>{l.discount_given}%</Td>
                <Td right>{l.limit_allowed}%</Td>
                <Td right>
                  {l.over_by > 0 ? (
                    <Badge status="OVER" label={`+${l.over_by}pt`} />
                  ) : (
                    <Badge status="OK" label="—" />
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
        <div className="text-sm" style={{ color: C.muted }}>
          {worst.over_by > 0
            ? `The "${worst.line}" line was discounted ${worst.discount_given}%, which is ${worst.over_by} points above the ${worst.limit_allowed}% ceiling for this customer tier — this is the primary driver of the ${detail.blended_risk} risk rating.`
            : "No individual line exceeds its discount ceiling."}
        </div>
      </Card>

      <Card className="mb-6">
        <Stepper
          steps={["Submitted", "Sales Manager", "Finance", "Confirmed"]}
          currentIndex={stageIndex}
        />
      </Card>

      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Audit Trail
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>User</Th>
              <Th>Action</Th>
              <Th>Date</Th>
              <Th>Note</Th>
            </tr>
          </thead>
          <tbody>
            {detail.audit_trail.map((a, i) => (
              <Tr key={i}>
                <Td>{a.user}</Td>
                <Td>{a.action}</Td>
                <Td>{a.date}</Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {a.note}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="flex justify-end gap-3">
        <Button variant="destructive" onClick={() => decide("Rejected")}>
          Reject
        </Button>
        <Button
          variant="warning"
          onClick={() => decide("Returned for Revision")}
        >
          Return for Revision
        </Button>
        <Button variant="success" onClick={() => decide("Approved")}>
          Approve
        </Button>
      </div>
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
