import { apiGet, apiSend } from "../client";
import { quotationEndpoints } from "../apiEndpoints";
import { MOCK_QUOTATIONS, MOCK_QUOTATION_DETAIL, MOCK_UPSELLS } from "../mocks";

// Expected: [{id, customer_name, amount, status}]
export async function loadQuotations() {
  try {
    return await apiGet(quotationEndpoints.list);
  } catch {
    return MOCK_QUOTATIONS;
  }
}

// Expected: { id, customer_name, price_list, lines: [{id, product, qty, price, discount_pct, limit_pct, status}] }
export async function loadQuotationDetail(id) {
  try {
    return await apiGet(quotationEndpoints.detail(id));
  } catch {
    return MOCK_QUOTATION_DETAIL;
  }
}

// Expected: [{product, margin_delta, promo_tag}]
export async function loadUpsells(id) {
  try {
    return await apiGet(quotationEndpoints.upsellSuggestions(id));
  } catch {
    return MOCK_UPSELLS;
  }
}

// Expected: { status: "OK"|"OVER", over_by_pct }
//
// limitPct is only used for the offline fallback. The backend is authoritative:
// it resolves the ceiling as min(tier, category) and the client never decides.
export async function patchDiscount(id, lineId, discountPct, limitPct) {
  try {
    return await apiSend(quotationEndpoints.line(id, lineId), "PATCH", {
      discount_pct: discountPct,
    });
  } catch {
    const over = discountPct - limitPct;
    return over > 0
      ? { status: "OVER", over_by_pct: over }
      : { status: "OK", over_by_pct: 0 };
  }
}

// Expected: { risk_level, decided_by, blended_score, required_approval, status, explanation }
//
// No mock fallback on purpose. Submitting is the moment the governance engine
// runs, so a failure has to surface rather than be papered over with a fake
// success - the caller shows the error.
export async function submitQuotation(id) {
  return apiSend(quotationEndpoints.submit(id), "POST");
}
