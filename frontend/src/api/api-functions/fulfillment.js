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

// Expected: { id, number, customer, status, warehouses: [{warehouse_id, product_id,
//             warehouse, product, qty_fulfilled, est_shipments, cost}],
//             legs: [{warehouse_id, warehouse, region, units, product_lines, cost}],
//             backorder: [{product_id, product, qty, available_now, sources}],
//             ordered_units, fulfilled_units, total_shipments, total_cost,
//             backordered, complete, can_consolidate, can_ship, shipped_at,
//             nothing_to_ship }
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

// Expected: the split, with the outstanding rows now allocated.
//
// Only the backorder is re-planned. Rows already reserved stay where they are,
// because moving a committed allocation would release stock a warehouse holds.
export async function consolidateBackorder(id) {
  return apiSend(fulfillmentEndpoints.consolidate(id), "POST");
}

// Expected: the split, marked shipped. Refused while anything is outstanding.
export async function markShipped(id) {
  return apiSend(fulfillmentEndpoints.ship(id), "POST");
}

// Backs the Simulate Restock button. PS 4-B6 wants the consolidation prompt to
// appear when stock arrives, and a demo cannot wait for a real delivery. The
// warehouse and product are passed in - it used to send literal 1, 1.
export async function restock(warehouseId, productId, qty) {
  return apiSend(fulfillmentEndpoints.restock, "POST", {
    warehouse_id: warehouseId,
    product_id: productId,
    qty,
  });
}
