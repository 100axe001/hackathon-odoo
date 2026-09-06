import { apiGet, apiSend } from "../client";
import { adminEndpoints } from "../apiEndpoints";

// Expected: { tier_ceilings, category_ceilings, routing_rules }
export async function loadDiscountConfig() {
  return apiGet(adminEndpoints.discountConfig);
}

// Expected: [{id, name, region, shipping_cost_weight, active, product_lines,
//             units_on_hand, units_reserved, units_available, below_reorder,
//             fulfilled_lines}]
export async function loadWarehouses() {
  return apiGet(adminEndpoints.warehouses);
}

// Expected: [{id, name, cycle, price, proration_enabled, refund_window_days,
//             cancellation_fee_pct}]
export async function loadSubscriptionPlans() {
  return apiGet(adminEndpoints.subscriptionPlans);
}

// Expected: the saved configuration, echoed back.
//
// These feed the risk engine directly, so a saved change alters routing on the
// next submit - which is the point of Screen 18.
export async function saveDiscountConfig(tierCeilings, categoryCeilings) {
  return apiSend(adminEndpoints.discountConfig, "PUT", {
    tier_ceilings: tierCeilings,
    category_ceilings: categoryCeilings,
  });
}

export async function saveWarehouses(warehouses) {
  return apiSend(adminEndpoints.warehouses, "PUT", { warehouses });
}

export async function saveSubscriptionPlans(plans) {
  return apiSend(adminEndpoints.subscriptionPlans, "PUT", { plans });
}

// Expected: the discount configuration, echoed back with the new chain.
//
// The whole chain is sent, not a delta: a level that loses a step has to
// actually lose it, and merging by position would leave an orphan behind.
export async function saveApprovalRules(rules) {
  return apiSend(adminEndpoints.approvalRules, "PUT", { rules });
}

// Expected: { min_margin_pct, max_suggestions }
export async function loadUpsellRule() {
  return apiGet(adminEndpoints.upsellRule);
}

export async function saveUpsellRule(minMarginPct, maxSuggestions) {
  return apiSend(adminEndpoints.upsellRule, "PUT", {
    min_margin_pct: minMarginPct,
    max_suggestions: maxSuggestions,
  });
}

// Expected: the remaining rows, echoed back.
//
// Each refuses with 409 and an explanation when something still points at the
// row - a warehouse that has shipped, a plan with subscribers, a tier with
// customers on it. The caller shows that sentence rather than a generic error.
export async function deleteWarehouse(id) {
  return apiSend(adminEndpoints.warehouse(id), "DELETE");
}

export async function deleteSubscriptionPlan(id) {
  return apiSend(adminEndpoints.subscriptionPlan(id), "DELETE");
}

export async function deleteDiscountTier(name) {
  return apiSend(adminEndpoints.discountTier(name), "DELETE");
}

export async function deleteCategoryCeiling(category) {
  return apiSend(adminEndpoints.categoryCeiling(category), "DELETE");
}
