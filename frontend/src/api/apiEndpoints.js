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
  create: "/quotations",
  stage: (id) => `/quotations/${enc(id)}/stage`,
  journey: (id) => `/quotations/${enc(id)}/journey`,
  messages: (id) => `/quotations/${enc(id)}/messages`,
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
  restock: "/fulfillment/restock",
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
  create: "/products",
  detail: (id) => `/products/${enc(id)}`,
};

export const adminEndpoints = {
  discountConfig: "/admin/discount-config",
  warehouses: "/admin/warehouses",
  subscriptionPlans: "/admin/subscription-plans",
  customers: "/admin/customers",
  approvalRules: "/admin/approval-rules",
  upsellRule: "/admin/upsell-rule",
  warehouse: (id) => `/admin/warehouses/${enc(id)}`,
  subscriptionPlan: (id) => `/admin/subscription-plans/${enc(id)}`,
  discountTier: (name) => `/admin/discount-tiers/${enc(name)}`,
  categoryCeiling: (category) => `/admin/category-ceilings/${enc(category)}`,
};

export const portalEndpoints = {
  list: "/portal/quotations",
  quotation: (id) => `/portal/quotations/${enc(id)}`,
  negotiate: (id) => `/portal/quotations/${enc(id)}/negotiate`,
  confirm: (id) => `/portal/quotations/${enc(id)}/confirm`,
  orders: "/portal/orders",
  billing: "/portal/billing",
  profile: "/portal/profile",
};

export const authEndpoints = {
  login: "/auth/login",
  signup: "/auth/signup",
  logout: "/auth/logout",
  me: "/auth/me",
};

export const reportEndpoints = {
  // Filters go to the server so the headline figures and the tables below them
  // always describe the same slice of data.
  summary: (params = {}) => {
    const q = new URLSearchParams();
    if (params.days) q.set("days", params.days);
    if (params.rep) q.set("rep", params.rep);
    if (params.category) q.set("category", params.category);
    const qs = q.toString();
    return qs ? `/reports?${qs}` : "/reports";
  },
};
