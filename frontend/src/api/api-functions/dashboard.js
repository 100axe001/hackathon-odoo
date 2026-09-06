import { apiGet } from "../client";
import { dashboardEndpoints } from "../apiEndpoints";

// Expected: { pending_approvals, open_quotations, at_risk_deals, recent_activity: [{id,text,timestamp}] }
export async function loadDashboard() {
  return apiGet(dashboardEndpoints.summary);
}
