import { apiGet } from "../client";
import { invoiceEndpoints } from "../apiEndpoints";
import { MOCK_INVOICES, MOCK_INVOICE_DETAIL } from "../mocks";

// Expected: [{id, customer, amount, status, due_date}]
export async function loadInvoices() {
  try {
    return await apiGet(invoiceEndpoints.list);
  } catch {
    return MOCK_INVOICES;
  }
}

// Expected: { id, invoice_no, customer, stage, lines }
export async function loadInvoiceDetail(id) {
  try {
    return await apiGet(invoiceEndpoints.detail(id));
  } catch {
    return MOCK_INVOICE_DETAIL;
  }
}
