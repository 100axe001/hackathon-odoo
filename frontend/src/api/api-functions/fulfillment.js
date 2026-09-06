import { apiGet, apiSend } from "../client";
import { fulfillmentEndpoints } from "../apiEndpoints";

// Expected: [{warehouse, product, in_stock, reserved, available, reorder_point,
//             reorder_qty, needs_restock,
//             reserved_for: [{customer, quotation, qty}]}]
export async function loadStock() {
  return apiGet(fulfillmentEndpoints.stock);
}

// Expected: [{id, order, customer, status, warehouses}]
export async function loadOrders() {
  return apiGet(fulfillmentEndpoints.orders("pending"));
}

// Expected: { id, customer, warehouses: [{warehouse, qty_fulfilled, est_shipments, cost}] }
export async function loadFulfillmentSplit(id) {
  return apiGet(fulfillmentEndpoints.split(id));
}

// Expected: { id, customer, status, warehouses, total_shipments, total_cost,
//             backordered, complete }
//
// No mock fallback on any of these: a split that silently did nothing would
// leave stock unreserved while the screen claimed otherwise.
export async function acceptSplit(id) {
  return apiSend(fulfillmentEndpoints.accept(id), "POST");
}

export async function overrideSplit(id, allocations) {
  return apiSend(fulfillmentEndpoints.override(id), "POST", { allocations });
}

// Backs the Simulate Restock button. PS 4-B6 wants the consolidation prompt to
// appear when stock arrives, and a demo cannot wait for a real delivery.
export async function restock(warehouseId, productId, qty = 100) {
  return apiSend(fulfillmentEndpoints.restock, "POST", {
    warehouse_id: warehouseId,
    product_id: productId,
    qty,
  });
}
