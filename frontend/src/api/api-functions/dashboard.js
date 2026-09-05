import { apiGet } from "../client";
import { dashboardEndpoints } from "../apiEndpoints";
import { MOCK_DASHBOARD } from "../mocks";

// Expected: { pending_approvals, open_quotations, at_risk_deals, recent_activity: [{id,text,timestamp}] }
export async function loadDashboard() {
  try {
    return await apiGet(dashboardEndpoints.summary);
  } catch {
    return MOCK_DASHBOARD;
  }
}
