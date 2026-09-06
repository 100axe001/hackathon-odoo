import { apiGet, apiSend } from "../client";
import { approvalEndpoints } from "../apiEndpoints";

// Expected: [{id, quotation, customer, blended_risk, stage, assigned_to, own}]
export async function loadApprovals() {
  return apiGet(approvalEndpoints.list("pending"));
}

// Expected: { id, quotation, customer, blended_risk, customer_tier, explanation,
//             lines, stage, rep, own, steps: [{role, status, acted_by}],
//             audit_trail }
//
// own means the caller wrote this quotation. Nobody signs off their own
// discount, so the screen reads it rather than offering buttons the decision
// endpoint will refuse.
export async function loadApprovalDetail(id) {
  return apiGet(approvalEndpoints.detail(id));
}

// Expected: { status, stage, direction, complete }
//
// direction is "forward" | "back" | "stopped". Read it rather than inferring
// from an empty stage: returning a quotation ends the chain too, and the screen
// used to report that as the last reviewer approving.
//
// decision is "approve" | "return" | "reject". Like submit, this throws on
// failure rather than falling back: a rejected decision (wrong role, or your
// own quotation) must be visible.
export async function decideApproval(id, decision, comment) {
  return apiSend(approvalEndpoints.decide(id), "POST", { decision, comment });
}
