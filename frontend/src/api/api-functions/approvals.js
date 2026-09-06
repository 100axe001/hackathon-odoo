import { apiGet, apiSend } from "../client";
import { approvalEndpoints } from "../apiEndpoints";

// Expected: [{id, quotation, customer, blended_risk, stage, assigned_to}]
export async function loadApprovals() {
  return apiGet(approvalEndpoints.list("pending"));
}

// Expected: { id, quotation, customer, blended_risk, customer_tier, lines, stage, audit_trail }
export async function loadApprovalDetail(id) {
  return apiGet(approvalEndpoints.detail(id));
}

// Expected: { status, stage, complete }
//
// decision is "approve" | "return" | "reject". Like submit, this throws on
// failure rather than falling back: a rejected decision (wrong role, or your
// own quotation) must be visible.
export async function decideApproval(id, decision, comment) {
  return apiSend(approvalEndpoints.decide(id), "POST", { decision, comment });
}
