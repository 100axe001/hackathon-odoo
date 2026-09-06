import { apiGet, apiSend } from "../client";
import { dealHealthEndpoints } from "../apiEndpoints";

// Expected: { stalled: [], anomalies: [], slippage: [] }
export async function loadDealHealth() {
  return apiGet(dealHealthEndpoints.list);
}

// Expected: { id, action }
//
// No mock fallback: an escalation that silently did nothing would be worse
// than an error the manager can see.
export async function escalateFlag(id) {
  return apiSend(dealHealthEndpoints.escalate(id), "POST");
}

export async function nudgeFlag(id) {
  return apiSend(dealHealthEndpoints.nudge(id), "POST");
}
