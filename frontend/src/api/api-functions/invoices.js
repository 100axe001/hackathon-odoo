import { apiGet, apiSend } from "../client";
import { invoiceEndpoints } from "../apiEndpoints";

// Expected: [{id, customer, amount, status, due_date}]
export async function loadInvoices() {
  return apiGet(invoiceEndpoints.list);
}

// Expected: { id, invoice_no, customer, stage, lines }
export async function loadInvoiceDetail(id) {
  return apiGet(invoiceEndpoints.detail(id));
}

// Expected: the invoice detail, with status recomputed from what is now paid.
export async function recordPayment(id, amount, method = "BANK_TRANSFER") {
  return apiSend(invoiceEndpoints.recordPayment(id), "POST", {
    amount,
    method,
  });
}
