import { useNavigate, useParams } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { InfoBanner } from "@/components/ui/InfoBanner";
import { PageHeader } from "@/components/ui/PageHeader";
import { Stepper } from "@/components/ui/Stepper";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { DealJourney } from "@/components/quotations/DealJourney";
import { C } from "@/constants/theme";
import {
  decideApproval,
  loadApprovalDetail,
} from "@/api/api-functions/approvals";

// SALES_MANAGER reads as a database value, not as a person's job.
function roleName(role) {
  return String(role)
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function ApprovalDetailScreen() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [detail, setDetail] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState("");
  const [comment, setComment] = useState("");
  const [outcome, setOutcome] = useState(null);
  const [decided, setDecided] = useState(false);
  useEffect(() => {
    loadApprovalDetail(id).then(setDetail).catch(setLoadError);
  }, [id]);
  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!detail) return null;

  const worst = detail.lines.reduce(
    (a, b) => (b.over_by > a.over_by ? b : a),
    detail.lines[0],
  );
  // The API reports the stage as the role still owed an action, or "Complete".
  // Map that onto the four labels the wireframe shows.
  const STAGE_INDEX = {
    SALES_MANAGER: 1,
    FINANCE: 2,
    Complete: 3,
  };
  const stageIndex = STAGE_INDEX[detail.stage] ?? 0;

  // "approve" | "return" | "reject" - the values the API expects. The server
  // decides whether this caller may act: it rejects a rep approving their own
  // quotation, and a reviewer jumping ahead of the step before theirs.
  const decide = async (decision) => {
    try {
      const result = await decideApproval(id, decision, comment || null);

      // Reported in place, with the queue one click away. The old version put
      // this in a toast and navigated away from it after 1.2 seconds, so the
      // reviewer never learned what their own decision had done.
      setOutcome({
        tone: result.status === "Rejected" ? "danger" : "success",
        text: result.complete
          ? `Approved. Every reviewer has now signed off, so ${detail.quotation} moves to fulfillment.`
          : result.stage
            ? `Recorded. ${detail.quotation} now needs ${roleName(result.stage)} before it can proceed.`
            : `${detail.quotation} is now ${result.status}. It goes back to the rep to revise and resubmit.`,
      });
      setDecided(true);
      loadApprovalDetail(id)
        .then(setDetail)
        .catch(() => {});
    } catch (err) {
      setToast(err.detail || "You may not act on this step.");
    }
  };

  return (
    <Transition keyProp={`ad-${id}`}>
      <DealJourney quotationId={id} />
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
          {/* Prefer the server's wording. It is generated from the actual
              calculation (PS section 5) and, unlike anything the client can
              build from `worst`, it can describe the case where no single line
              is the culprit and the blended pattern is what escalated. */}
          {detail.explanation ||
            (worst.over_by > 0
              ? `The "${worst.line}" line was discounted ${worst.discount_given}%, which is ${worst.over_by} points above the ${worst.limit_allowed}% ceiling for this customer tier.`
              : "No individual line exceeds its discount ceiling.")}
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

      <div className="mb-4" hidden={decided}>
        <label className="text-sm mb-1 block" style={{ color: C.text }}>
          Reviewer comment
        </label>
        <textarea
          rows={2}
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Reason for this decision - stored on the audit trail"
          className="w-full rounded-md px-3 py-2 text-sm outline-none transition-all duration-150"
          style={{ border: `1px solid ${C.border}` }}
        />
      </div>

      {outcome ? (
        <InfoBanner
          tone={outcome.tone}
          action={
            <Button variant="secondary" onClick={() => navigate("/approvals")}>
              Back to queue
            </Button>
          }
        >
          {outcome.text}
        </InfoBanner>
      ) : (
        <div className="flex justify-end gap-3">
          <Button variant="destructive" onClick={() => decide("reject")}>
            Reject
          </Button>
          <Button variant="warning" onClick={() => decide("return")}>
            Return for Revision
          </Button>
          <Button variant="success" onClick={() => decide("approve")}>
            Approve
          </Button>
        </div>
      )}
      <Toast message={toast} onClose={() => setToast("")} />
    </Transition>
  );
}
