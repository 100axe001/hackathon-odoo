import { apiGet } from "../client";
import { adminEndpoints } from "../apiEndpoints";
import {
  MOCK_DISCOUNT_CONFIG,
  MOCK_WAREHOUSES,
  MOCK_SUBSCRIPTION_PLANS,
} from "../mocks";

// Expected: { tier_ceilings, category_ceilings, routing_rules }
export async function loadDiscountConfig() {
  try {
    return await apiGet(adminEndpoints.discountConfig);
  } catch {
    return MOCK_DISCOUNT_CONFIG;
  }
}

// Expected: [{id, name, region, shipping_cost_weight, active}]
export async function loadWarehouses() {
  try {
    return await apiGet(adminEndpoints.warehouses);
  } catch {
    return MOCK_WAREHOUSES;
  }
}

// Expected: [{id, name, cycle, price, proration_enabled}]
export async function loadSubscriptionPlans() {
  try {
    return await apiGet(adminEndpoints.subscriptionPlans);
  } catch {
    return MOCK_SUBSCRIPTION_PLANS;
  }
}
