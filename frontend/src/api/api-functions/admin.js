import { apiGet } from "../client";
import { adminEndpoints } from "../apiEndpoints";
import { MOCK_DISCOUNT_CONFIG } from "../mocks";

// Expected: { tier_ceilings, category_ceilings, routing_rules }
export async function loadDiscountConfig() {
  try {
    return await apiGet(adminEndpoints.discountConfig);
  } catch {
    return MOCK_DISCOUNT_CONFIG;
  }
}
