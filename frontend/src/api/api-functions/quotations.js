import { apiGet, apiSend } from "../client";
import { adminEndpoints, quotationEndpoints } from "../apiEndpoints";

// Expected: [{id, customer_name, amount, status}]
export async function loadQuotations() {
  return apiGet(quotationEndpoints.list);
}

// Expected: { id, number, customer_name, price_list, status, risk_level,
//             margin, margin_pct, net_total, returned_by, returned_note,
//             lines: [{id, product, qty, price, discount_pct, limit_pct, status}] }
//
// returned_by/returned_note are set only while a Draft is back with the rep
// because a reviewer sent it there.
export async function loadQuotationDetail(id) {
  return apiGet(quotationEndpoints.detail(id));
}

// Expected: [{product_id, product, margin_delta, promo_tag}]
export async function loadUpsells(id) {
  return apiGet(quotationEndpoints.upsellSuggestions(id));
}

// Expected: { status: "OK"|"OVER", over_by_pct, allowed_discount_pct, qty,
//             line_total, margin, margin_pct }
//
// The backend is authoritative and there is no fallback: it resolves the
// ceiling as min(tier, category) per line, and the client never decides a
// limit. An edit that failed must surface, not quietly show a guess.
export async function patchDiscount(id, lineId, discountPct) {
  return apiSend(quotationEndpoints.line(id, lineId), "PATCH", {
    discount_pct: discountPct,
  });
}

// Expected: the same line status shape as patchDiscount.
//
// No fallback: quantity drives the line total and the blended weighting, so a
// change that silently failed would leave the screen showing a price the
// server does not agree with.
export async function patchLineQty(id, lineId, qty) {
  return apiSend(quotationEndpoints.line(id, lineId), "PATCH", { qty });
}

// Expected: { risk_level, decided_by, blended_score, required_approval, status, explanation }
//
// No mock fallback on purpose. Submitting is the moment the governance engine
// runs, so a failure has to surface rather than be papered over with a fake
// success - the caller shows the error.
export async function submitQuotation(id) {
  return apiSend(quotationEndpoints.submit(id), "POST");
}

// Expected: the full quotation detail, re-scored, including updated margin.
// PS section 9 step 4 checks the total and margin move right away.
export async function addQuotationLine(id, productId, qty = 1) {
  return apiSend(quotationEndpoints.lines(id), "POST", {
    product_id: productId,
    qty,
  });
}

// Expected: [{id, name, tier}]
//
// Reuses GET /admin/customers rather than adding a second read of the same
// table. No mock fallback on purpose: creating against an invented customer id
// would 404, so the picker has to show the failure instead of a fake list.
export async function loadCustomers() {
  return apiGet(adminEndpoints.customers);
}

// Expected: { id, customer_name, price_list, lines, margin, margin_pct, net_total }
//
// The same shape loadQuotationDetail returns, so the caller navigates straight
// into the new quotation. rep_id is not sent - the backend takes the owner from
// the session, and a body that named someone else would be ignored.
export async function createQuotation(customerId) {
  return apiSend(quotationEndpoints.create, "POST", {
    customer_id: customerId,
  });
}

// Expected: { id, customer_name, amount, status } - the board row, restated by
// the server.
//
// No mock fallback. The backend decides which moves the board may make, because
// submitting, approving and confirming own the rest; a faked success would let a
// drag appear to skip the approval chain.
export async function changeQuotationStage(id, status) {
  return apiSend(quotationEndpoints.stage(id), "POST", { status });
}

// Expected: { number, customer, stages: [{key,label,state,detail}],
//             next_action: {label, path, role} | null }
export async function loadJourney(id) {
  return apiGet(quotationEndpoints.journey(id));
}

// Expected: [{author, role: "Customer"|"Us", body, counter_discount_pct, created_at}]
export async function loadThread(id) {
  return apiGet(quotationEndpoints.messages(id));
}

// Expected: the thread, with the reply appended.
export async function replyToCustomer(id, body) {
  return apiSend(quotationEndpoints.messages(id), "POST", { body });
}
