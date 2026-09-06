import { apiGet, apiSend } from "../client";
import { productEndpoints } from "../apiEndpoints";

// Expected: [{id, name, category, variants, price, unit, tax, status}]
export async function loadProducts() {
  return apiGet(productEndpoints.list);
}

// Expected: { id, name, category, price, cost_price, unit, tax, description,
//             subscription, cadence, qty_on_hand, variants, total_available,
//             stock: [{warehouse, region, active, on_hand, reserved, available,
//                      reorder_point, reorder_qty, needs_restock}],
//             pricelists: [{tier, currency, rule}] }
export async function loadProductDetail(id) {
  return apiGet(productEndpoints.detail(id));
}

// Body: { name, category, unit_price, cost_price, unit, tax_pct, description,
//         is_subscription, recurring_cycle }
// Expected: the saved product, in the same shape loadProductDetail returns.
//
// No mock fallback, unlike the reads above: a write that quietly "succeeds"
// against sample data is worse than the error, so this one throws and the
// screen shows what went wrong.
export async function saveProduct(id, product) {
  return apiSend(productEndpoints.detail(id), "PUT", product);
}

// Expected: the created product, in the same shape the detail returns.
export async function createProduct(fields) {
  return apiSend(productEndpoints.create, "POST", fields);
}
