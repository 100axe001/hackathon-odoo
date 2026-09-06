import { apiGet, apiSend } from "../client";
import { subscriptionEndpoints } from "../apiEndpoints";

// Expected: [{id, customer, plan, cycle, next_bill, status}]
export async function loadSubscriptions() {
  return apiGet(subscriptionEndpoints.list);
}

// Expected: { id, customer, one_time_lines, recurring_lines,
//             schedule: [{due_date, amount, is_prorated, note}] }
export async function loadBillingDetail(id) {
  return apiGet(subscriptionEndpoints.billingDetail(id));
}

// Expected: { amount, is_credit, remaining_days, cycle_days, price_delta, new_qty, explanation }
//
// The server prorates. The client cannot: the period boundary and its real
// calendar length live on the subscription, not on the screen.
export async function modifySubscription(id, qty) {
  return apiSend(subscriptionEndpoints.modify(id), "POST", { qty });
}

// Expected: { status, credit_amount, credit_note, explanation }
export async function cancelSubscription(id) {
  return apiSend(subscriptionEndpoints.cancel(id), "POST");
}
