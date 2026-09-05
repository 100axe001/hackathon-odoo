import { apiGet } from "../client";
import { fulfillmentEndpoints } from "../apiEndpoints";
import { MOCK_STOCK, MOCK_ORDERS, MOCK_FULFILLMENT_SPLIT } from "../mocks";

// Expected: [{warehouse, product, in_stock, reserved, available}]
export async function loadStock() {
  try {
    return await apiGet(fulfillmentEndpoints.stock);
  } catch {
    return MOCK_STOCK;
  }
}

// Expected: [{id, order, customer, status, warehouses}]
export async function loadOrders() {
  try {
    return await apiGet(fulfillmentEndpoints.orders("pending"));
  } catch {
    return MOCK_ORDERS;
  }
}

// Expected: { id, customer, warehouses: [{warehouse, qty_fulfilled, est_shipments, cost}] }
export async function loadFulfillmentSplit(id) {
  try {
    return await apiGet(fulfillmentEndpoints.split(id));
  } catch {
    return MOCK_FULFILLMENT_SPLIT;
  }
}
