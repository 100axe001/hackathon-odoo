import { apiGet } from "../client";
import { productEndpoints } from "../apiEndpoints";
import { MOCK_PRODUCTS, MOCK_PRODUCT_DETAIL } from "../mocks";

// Expected: [{id, name, category, variants, price, unit, tax, status}]
export async function loadProducts() {
  try {
    return await apiGet(productEndpoints.list);
  } catch {
    return MOCK_PRODUCTS;
  }
}

// Expected: { id, name, category, price, unit, tax, description, subscription, cadence, qty_on_hand, variants, pricelists }
export async function loadProductDetail(id) {
  try {
    return await apiGet(productEndpoints.detail(id));
  } catch {
    return MOCK_PRODUCT_DETAIL;
  }
}
