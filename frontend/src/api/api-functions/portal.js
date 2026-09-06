import { apiGet, apiSend } from "../client";
import { portalEndpoints } from "../apiEndpoints";

// Expected: [{id, number, status, total}]
export async function loadPortalQuotations() {
  return apiGet(portalEndpoints.list);
}

// Expected: { id, number, customer, status, total, can_act, blocked_reason,
//             lines: [...], comments: [...] }
export async function loadPortalQuotation(id) {
  return apiGet(portalEndpoints.quotation(id));
}

// Expected: { status, counter_discount_pct, message }
//
// No mock fallback: a counter-offer that silently did nothing would be worse
// than an error the customer can see.
export async function negotiate(id, counterDiscountPct, deliveryDate, note) {
  return apiSend(portalEndpoints.negotiate(id), "POST", {
    counter_discount_pct: counterDiscountPct,
    requested_delivery_date: deliveryDate || null,
    note: note || null,
  });
}

// Expected: { status, risk_level, reentered_approval, required_approval, explanation }
//
// reentered_approval is the governance moment: the server re-scored the
// negotiated terms and decided they need review again.
export async function confirmQuotation(id) {
  return apiSend(portalEndpoints.confirm(id), "POST");
}

// Expected: [{id, number, status, total, fulfillment,
//             shipments: [{warehouse, product, qty}]}]
export async function loadPortalOrders() {
  return apiGet(portalEndpoints.orders);
}

// Expected: { invoices: [{id, number, document, order, amount, paid,
//                         balance_due, status, issue_date, due_date}],
//             subscriptions: [{plan, cycle, qty, amount, next_bill, status}],
//             total_outstanding }
export async function loadPortalBilling() {
  return apiGet(portalEndpoints.billing);
}

// Expected: { company, tier, contact_name, contact_email, open_quotations,
//             orders, outstanding }
export async function loadPortalProfile() {
  return apiGet(portalEndpoints.profile);
}
