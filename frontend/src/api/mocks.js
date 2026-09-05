// Fallback data for every screen. Each api-function returns its MOCK_* constant
// when the request fails, so a not-yet-built endpoint leaves that screen on
// sample data instead of crashing.
//
// Seed data in backend/seed.py mirrors these values: screens then look identical
// before and after an endpoint goes live, which makes a regression obvious.

export const MOCK_DASHBOARD = {
  pending_approvals: 6,
  open_quotations: 14,
  at_risk_deals: 3,
  recent_activity: [
    {
      id: "a1",
      text: "Acme Corp quotation Q-1042 submitted for approval",
      timestamp: "2h ago",
    },
    {
      id: "a2",
      text: "Beta Industries invoice INV-3081 marked paid",
      timestamp: "4h ago",
    },
    {
      id: "a3",
      text: "Delta LLC subscription renewed for Q3",
      timestamp: "6h ago",
    },
    {
      id: "a4",
      text: "Cascade Roofing quotation Q-1039 returned for revision",
      timestamp: "1d ago",
    },
    {
      id: "a5",
      text: "Harbor Freight Supply order shipped from West Depot",
      timestamp: "1d ago",
    },
    {
      id: "a6",
      text: "Northwind Traders quote auto-approved under 5% ceiling",
      timestamp: "2d ago",
    },
  ],
};

export const MOCK_QUOTATIONS = [
  {
    id: "q1",
    customer_name: "Acme Corp",
    amount: 48250,
    status: "Pending Approval",
  },
  {
    id: "q2",
    customer_name: "Beta Industries",
    amount: 12800,
    status: "Draft",
  },
  {
    id: "q3",
    customer_name: "Delta LLC",
    amount: 93400,
    status: "Negotiation",
  },
  {
    id: "q4",
    customer_name: "Cascade Roofing",
    amount: 27650,
    status: "Approved",
  },
  {
    id: "q5",
    customer_name: "Harbor Freight Supply",
    amount: 61200,
    status: "Confirmed",
  },
  {
    id: "q6",
    customer_name: "Northwind Traders",
    amount: 8950,
    status: "Draft",
  },
  {
    id: "q7",
    customer_name: "Ironclad Manufacturing",
    amount: 154300,
    status: "Pending Approval",
  },
  {
    id: "q8",
    customer_name: "Summit Retail Group",
    amount: 33100,
    status: "Approved",
  },
];

export const MOCK_QUOTATION_DETAIL = {
  id: "q1",
  customer_name: "Acme Corp",
  price_list: "Standard Wholesale",
  lines: [
    {
      id: "l1",
      product: "Industrial Shelving Unit",
      qty: 40,
      price: 210,
      discount_pct: 8,
      limit_pct: 10,
      status: "OK",
    },
    {
      id: "l2",
      product: "Heavy-Duty Pallet Jack",
      qty: 6,
      price: 640,
      discount_pct: 18,
      limit_pct: 10,
      status: "OVER",
    },
    {
      id: "l3",
      product: "Warehouse LED Fixture",
      qty: 24,
      price: 95,
      discount_pct: 5,
      limit_pct: 10,
      status: "OK",
    },
    {
      id: "l4",
      product: "Safety Barrier Rail (10ft)",
      qty: 18,
      price: 130,
      discount_pct: 9,
      limit_pct: 10,
      status: "OK",
    },
  ],
};

export const MOCK_UPSELLS = [
  { product: "Extended Warranty — 3yr", margin_delta: 1240, promo_tag: null },
  {
    product: "Forklift Charging Station",
    margin_delta: 2890,
    promo_tag: "Promo",
  },
  { product: "Rack Protection Kit", margin_delta: 610, promo_tag: null },
];

export const MOCK_APPROVALS = [
  {
    id: "q1",
    quotation: "Q-1042",
    customer: "Acme Corp",
    blended_risk: "HIGH",
    stage: "Sales Manager",
    assigned_to: "R. Delgado",
  },
  {
    id: "q7",
    quotation: "Q-1049",
    customer: "Ironclad Manufacturing",
    blended_risk: "HIGH",
    stage: "Finance",
    assigned_to: "M. Osei",
  },
  {
    id: "q9",
    quotation: "Q-1038",
    customer: "Fairview Distributors",
    blended_risk: "MEDIUM",
    stage: "Sales Manager",
    assigned_to: "R. Delgado",
  },
  {
    id: "q10",
    quotation: "Q-1031",
    customer: "Union Hardware Co",
    blended_risk: "LOW",
    stage: "Finance",
    assigned_to: "M. Osei",
  },
  {
    id: "q11",
    quotation: "Q-1052",
    customer: "Palisade Foods",
    blended_risk: "MEDIUM",
    stage: "Sales Manager",
    assigned_to: "T. Kowalski",
  },
];

export const MOCK_APPROVAL_DETAIL = {
  id: "q1",
  quotation: "Q-1042",
  customer: "Acme Corp",
  blended_risk: "HIGH",
  customer_tier: "Gold",
  lines: [
    {
      line: "Industrial Shelving Unit",
      discount_given: 8,
      limit_allowed: 10,
      over_by: 0,
    },
    {
      line: "Heavy-Duty Pallet Jack",
      discount_given: 18,
      limit_allowed: 10,
      over_by: 8,
    },
    {
      line: "Warehouse LED Fixture",
      discount_given: 5,
      limit_allowed: 10,
      over_by: 0,
    },
  ],
  stage: "Sales Manager",
  audit_trail: [
    {
      user: "J. Alvarez",
      action: "Submitted quotation",
      date: "Sep 3, 2026",
      note: "Initial submission",
    },
    {
      user: "System",
      action: "Flagged for review",
      date: "Sep 3, 2026",
      note: "Line over discount ceiling",
    },
    {
      user: "R. Delgado",
      action: "Opened for review",
      date: "Sep 4, 2026",
      note: "—",
    },
  ],
};

export const MOCK_STOCK = [
  {
    warehouse: "West Depot",
    product: "Industrial Shelving Unit",
    in_stock: 220,
    reserved: 140,
    available: 80,
  },
  {
    warehouse: "West Depot",
    product: "Heavy-Duty Pallet Jack",
    in_stock: 18,
    reserved: 12,
    available: 6,
  },
  {
    warehouse: "East Depot",
    product: "Warehouse LED Fixture",
    in_stock: 340,
    reserved: 90,
    available: 250,
  },
  {
    warehouse: "East Depot",
    product: "Safety Barrier Rail (10ft)",
    in_stock: 60,
    reserved: 60,
    available: 0,
  },
];

export const MOCK_ORDERS = [
  {
    id: "q5",
    order: "ORD-2091",
    customer: "Harbor Freight Supply",
    status: "Pending",
    warehouses: "West Depot",
  },
  {
    id: "q4",
    order: "ORD-2088",
    customer: "Cascade Roofing",
    status: "Partial",
    warehouses: "East Depot, West Depot",
  },
  {
    id: "q8",
    order: "ORD-2079",
    customer: "Summit Retail Group",
    status: "Pending",
    warehouses: "East Depot",
  },
];

export const MOCK_FULFILLMENT_SPLIT = {
  id: "q5",
  customer: "Harbor Freight Supply",
  warehouses: [
    { warehouse: "West Depot", qty_fulfilled: 34, est_shipments: 1, cost: 410 },
    { warehouse: "East Depot", qty_fulfilled: 6, est_shipments: 1, cost: 95 },
  ],
};

export const MOCK_SUBSCRIPTIONS = [
  {
    id: "s1",
    customer: "Delta LLC",
    plan: "Managed Supply — Pro",
    cycle: "Monthly",
    next_bill: "Oct 1, 2026",
    status: "Active",
  },
  {
    id: "s2",
    customer: "Northwind Traders",
    plan: "Managed Supply — Basic",
    cycle: "Quarterly",
    next_bill: "Nov 15, 2026",
    status: "Active",
  },
  {
    id: "s3",
    customer: "Union Hardware Co",
    plan: "Managed Supply — Pro",
    cycle: "Monthly",
    next_bill: "—",
    status: "Paused",
  },
  {
    id: "s4",
    customer: "Fairview Distributors",
    plan: "Managed Supply — Basic",
    cycle: "Yearly",
    next_bill: "—",
    status: "Cancelled",
  },
];

export const MOCK_BILLING_DETAIL = {
  id: "s1",
  customer: "Delta LLC",
  one_time_lines: [
    { product: "Onboarding Kit", qty: 1, amount: 450 },
    { product: "Custom Rack Labeling", qty: 3, amount: 210 },
  ],
  recurring_lines: [
    {
      plan: "Managed Supply — Pro",
      cycle: "Monthly",
      next_bill: "Oct 1, 2026",
      amount: 2400,
    },
  ],
};

export const MOCK_PORTAL_QUOTATION = {
  id: "q3",
  customer: "Delta LLC",
  status: "Under Negotiation",
  lines: [
    {
      product: "Industrial Shelving Unit",
      comment: "Can we get 12% off this line given the order size?",
    },
    {
      product: "Heavy-Duty Pallet Jack",
      comment: "Delivery timeline needs to move up two weeks.",
    },
  ],
};

export const MOCK_INVOICES = [
  {
    id: "i1",
    invoice_no: "INV-3081",
    customer: "Beta Industries",
    amount: 12800,
    status: "Paid",
    due_date: "Aug 28, 2026",
  },
  {
    id: "i2",
    invoice_no: "INV-3092",
    customer: "Cascade Roofing",
    amount: 27650,
    status: "Unpaid",
    due_date: "Sep 20, 2026",
  },
  {
    id: "i3",
    invoice_no: "INV-3095",
    customer: "Harbor Freight Supply",
    amount: 61200,
    status: "Unpaid",
    due_date: "Sep 25, 2026",
  },
  {
    id: "i4",
    invoice_no: "INV-3070",
    customer: "Summit Retail Group",
    amount: 33100,
    status: "Paid",
    due_date: "Aug 15, 2026",
  },
];

export const MOCK_INVOICE_DETAIL = {
  id: "i2",
  invoice_no: "INV-3092",
  customer: "Cascade Roofing",
  stage: "Invoiced",
  lines: [
    {
      product: "Industrial Shelving Unit",
      qty: 40,
      amount: 7728,
      recurring: false,
    },
    {
      product: "Safety Barrier Rail (10ft)",
      qty: 18,
      amount: 2129,
      recurring: false,
    },
    { product: "Managed Supply — Basic", qty: 1, amount: 900, recurring: true },
  ],
};

export const MOCK_DEAL_HEALTH = {
  stalled: [
    {
      deal: "Fairview Distributors — Q-1038",
      issue: "No activity in 9 days",
      flagged: "Sep 2, 2026",
    },
  ],
  anomalies: [
    {
      deal: "Acme Corp — Q-1042",
      issue: "Discount 8pt over ceiling on pallet jacks",
      flagged: "Sep 3, 2026",
    },
  ],
  slippage: [
    {
      deal: "Harbor Freight Supply — ORD-2091",
      issue: "Shipment delayed 4 days",
      flagged: "Sep 4, 2026",
    },
  ],
};

export const MOCK_PRODUCTS = [
  {
    id: "p1",
    name: "Industrial Shelving Unit",
    category: "Hardware",
    variants: 3,
    price: 210,
    unit: "unit",
    tax: "8%",
    status: "Active",
  },
  {
    id: "p2",
    name: "Heavy-Duty Pallet Jack",
    category: "Hardware",
    variants: 2,
    price: 640,
    unit: "unit",
    tax: "8%",
    status: "Active",
  },
  {
    id: "p3",
    name: "Warehouse LED Fixture",
    category: "Hardware",
    variants: 4,
    price: 95,
    unit: "unit",
    tax: "8%",
    status: "Active",
  },
  {
    id: "p4",
    name: "Managed Supply — Pro",
    category: "Services",
    variants: 1,
    price: 2400,
    unit: "month",
    tax: "0%",
    status: "Active",
  },
  {
    id: "p5",
    name: "Safety Barrier Rail (10ft)",
    category: "Hardware",
    variants: 2,
    price: 130,
    unit: "unit",
    tax: "8%",
    status: "Discontinued",
  },
];

export const MOCK_PRODUCT_DETAIL = {
  id: "p1",
  name: "Industrial Shelving Unit",
  category: "Hardware",
  price: 210,
  unit: "unit",
  tax: 8,
  description:
    "Modular steel shelving unit rated for 1,200 lb per shelf, designed for warehouse and light industrial storage.",
  subscription: false,
  cadence: "Monthly",
  qty_on_hand: 340,
  variants: [
    {
      attribute: "Finish",
      values: "Galvanized, Powder-Coated Black",
      extra_price: 0,
    },
    { attribute: "Height", values: "72in, 84in, 96in", extra_price: 35 },
  ],
  pricelists: [
    { tier: "Bronze", currency: "USD", price_rule: "List price" },
    { tier: "Silver", currency: "USD", price_rule: "List − 5%" },
    { tier: "Gold", currency: "USD", price_rule: "List − 10%" },
  ],
};

export const MOCK_DISCOUNT_CONFIG = {
  tier_ceilings: [
    { tier: "Bronze", max_discount: 5 },
    { tier: "Silver", max_discount: 10 },
    { tier: "Gold", max_discount: 15 },
  ],
  category_ceilings: [
    { category: "Hardware", max_discount: 15 },
    { category: "Services", max_discount: 10 },
  ],
  routing_rules: [
    { range: "0% – 5%", approval: "Auto-approved" },
    { range: "5% – 12%", approval: "Sales Manager" },
    { range: "12%+", approval: "Sales Manager + Finance" },
  ],
};
