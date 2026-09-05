import { apiGet } from "../client";
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
