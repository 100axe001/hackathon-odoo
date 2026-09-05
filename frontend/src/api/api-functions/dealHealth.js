import { apiGet } from "../client";
import { dealHealthEndpoints } from "../apiEndpoints";
import { MOCK_DEAL_HEALTH } from "../mocks";

// Expected: { stalled: [], anomalies: [], slippage: [] }
export async function loadDealHealth() {
  try {
    return await apiGet(dealHealthEndpoints.list);
  } catch {
    return MOCK_DEAL_HEALTH;
  }
}
