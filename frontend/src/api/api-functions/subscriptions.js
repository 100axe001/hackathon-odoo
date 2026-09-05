import { apiGet } from "../client";
import { subscriptionEndpoints } from "../apiEndpoints";
import { MOCK_SUBSCRIPTIONS, MOCK_BILLING_DETAIL } from "../mocks";

// Expected: [{id, customer, plan, cycle, next_bill, status}]
export async function loadSubscriptions() {
  try {
    return await apiGet(subscriptionEndpoints.list);
  } catch {
    return MOCK_SUBSCRIPTIONS;
  }
}

// Expected: { id, customer, one_time_lines, recurring_lines }
export async function loadBillingDetail(id) {
  try {
    return await apiGet(subscriptionEndpoints.billingDetail(id));
  } catch {
    return MOCK_BILLING_DETAIL;
  }
}
