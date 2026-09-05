import { apiGet, apiSend } from "../client";
import { approvalEndpoints } from "../apiEndpoints";
import { MOCK_APPROVALS, MOCK_APPROVAL_DETAIL } from "../mocks";

// Expected: [{id, quotation, customer, blended_risk, stage, assigned_to}]
export async function loadApprovals() {
  try {
    return await apiGet(approvalEndpoints.list("pending"));
  } catch {
    return MOCK_APPROVALS;
  }
}

// Expected: { id, quotation, customer, blended_risk, customer_tier, lines, stage, audit_trail }
export async function loadApprovalDetail(id) {
  try {
    return await apiGet(approvalEndpoints.detail(id));
  } catch {
    return MOCK_APPROVAL_DETAIL;
  }
}

// Expected: { status, stage, complete }
//
// decision is "approve" | "return" | "reject". Like submit, this throws on
// failure rather than falling back: a rejected decision (wrong role, or your
// own quotation) must be visible.
export async function decideApproval(id, decision, comment) {
  return apiSend(approvalEndpoints.decide(id), "POST", { decision, comment });
}
