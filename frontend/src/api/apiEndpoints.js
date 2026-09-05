// Every API URL in one place, grouped by resource. Parameterised URLs are
// functions that encode their arguments.
//
// Paths are relative to API_BASE ("/api"), which Vite proxies to the FastAPI
// server with the prefix stripped — so "/quotations" here arrives as
// "/quotations" at the backend.

const enc = encodeURIComponent;

export const dashboardEndpoints = {
  summary: "/dashboard/summary",
};

export const quotationEndpoints = {
  list: "/quotations",
  detail: (id) => `/quotations/${enc(id)}`,
  upsellSuggestions: (id) => `/quotations/${enc(id)}/upsell-suggestions`,
  lines: (id) => `/quotations/${enc(id)}/lines`,
  line: (id, lineId) => `/quotations/${enc(id)}/lines/${enc(lineId)}`,
  submit: (id) => `/quotations/${enc(id)}/submit`,
};

export const approvalEndpoints = {
  list: (filter = "pending") => `/approvals?filter=${enc(filter)}`,
  detail: (id) => `/quotations/${enc(id)}/approval-detail`,
  decide: (id) => `/quotations/${enc(id)}/approve`,
};

export const fulfillmentEndpoints = {
  stock: "/fulfillment/stock",
  orders: (status = "pending") => `/fulfillment/orders?status=${enc(status)}`,
  split: (id) => `/quotations/${enc(id)}/fulfillment-split`,
  accept: (id) => `/quotations/${enc(id)}/fulfillment/accept`,
  override: (id) => `/quotations/${enc(id)}/fulfillment/override`,
};

export const subscriptionEndpoints = {
  list: "/subscriptions",
  billingDetail: (id) => `/subscriptions/${enc(id)}/billing-detail`,
  modify: (id) => `/subscriptions/${enc(id)}/modify`,
  cancel: (id) => `/subscriptions/${enc(id)}/cancel`,
};

export const invoiceEndpoints = {
  list: "/invoices",
  detail: (id) => `/invoices/${enc(id)}`,
  recordPayment: (id) => `/invoices/${enc(id)}/record-payment`,
};

export const dealHealthEndpoints = {
  list: "/deal-health",
  escalate: (id) => `/deal-health/${enc(id)}/escalate`,
  nudge: (id) => `/deal-health/${enc(id)}/nudge`,
};

export const productEndpoints = {
  list: "/products",
  detail: (id) => `/products/${enc(id)}`,
};

export const adminEndpoints = {
  discountConfig: "/admin/discount-config",
  warehouses: "/admin/warehouses",
  subscriptionPlans: "/admin/subscription-plans",
};

export const portalEndpoints = {
  quotation: (id) => `/portal/quotations/${enc(id)}`,
  negotiate: (id) => `/portal/quotations/${enc(id)}/negotiate`,
  confirm: (id) => `/portal/quotations/${enc(id)}/confirm`,
};

export const authEndpoints = {
  login: "/auth/login",
  logout: "/auth/logout",
  me: "/auth/me",
};
