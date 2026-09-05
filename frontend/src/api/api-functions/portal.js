import { apiGet, apiSend } from "../client";
import { portalEndpoints } from "../apiEndpoints";
import { MOCK_PORTAL_QUOTATION } from "../mocks";

// Expected: { id, number, customer, status, total, lines: [...], comments: [...] }
export async function loadPortalQuotation(id) {
  try {
    return await apiGet(portalEndpoints.quotation(id));
  } catch {
    return MOCK_PORTAL_QUOTATION;
  }
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
