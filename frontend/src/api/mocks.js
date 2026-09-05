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
    {
      id: "a7",
      text: "Zenith Co quotation Q-1039 escalated to Finance",
      timestamp: "2d ago",
    },
    {
      id: "a8",
      text: "Orion Ltd split across West Depot and East Depot",
      timestamp: "3d ago",
    },
    {
      id: "a9",
      text: "Sterling Foods counter-offer received via portal",
      timestamp: "3d ago",
    },
    {
      id: "a10",
      text: "Fairview Distributors flagged - idle 9 days",
      timestamp: "4d ago",
    },
  ],
};

export const MOCK_QUOTATIONS = [
  {
    id: "q1",
    customer_name: "Acme Corp",
    amount: 45100,
    status: "Pending Approval",
  },
  {
    id: "q2",
    customer_name: "Beta Industries",
    amount: 54000,
    status: "Approved",
  },
  {
    id: "q3",
    customer_name: "Delta LLC",
    amount: 13400,
    status: "Negotiation",
  },
  {
    id: "q4",
    customer_name: "Harbor Freight Supply",
    amount: 16250,
    status: "Confirmed",
  },
  { id: "q5", customer_name: "Nova Retail", amount: 78000, status: "Draft" },
  {
    id: "q6",
    customer_name: "Zenith Co",
    amount: 68150,
    status: "Pending Approval",
  },
  { id: "q7", customer_name: "Orion Ltd", amount: 8050, status: "Approved" },
  {
    id: "q8",
    customer_name: "Fairview Distributors",
    amount: 59300,
    status: "Negotiation",
  },
  {
    id: "q9",
    customer_name: "Redwood Logistics",
    amount: 12150,
    status: "Confirmed",
  },
  {
    id: "q10",
    customer_name: "Sterling Foods",
    amount: 15400,
    status: "Draft",
  },
  {
    id: "q11",
    customer_name: "Pinnacle Manufacturing",
    amount: 58000,
    status: "Pending Approval",
  },
  {
    id: "q12",
    customer_name: "Grayson Wholesale",
    amount: 76050,
    status: "Approved",
  },
  {
    id: "q13",
    customer_name: "Meridian Tools",
    amount: 32000,
    status: "Negotiation",
  },
  {
    id: "q14",
    customer_name: "Copperline Supply",
    amount: 77300,
    status: "Confirmed",
  },
  {
    id: "q15",
    customer_name: "Vantage Industrial",
    amount: 10150,
    status: "Draft",
  },
  {
    id: "q16",
    customer_name: "Ashford Retail",
    amount: 9400,
    status: "Pending Approval",
  },
  {
    id: "q17",
    customer_name: "Northgate Traders",
    amount: 21200,
    status: "Approved",
  },
  {
    id: "q18",
    customer_name: "Lakeside Equipment",
    amount: 57100,
    status: "Negotiation",
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
  { product: "Installation Service", margin_delta: 860, promo_tag: "12% off" },
  {
    product: "Quarterly Safety Audit",
    margin_delta: 2100,
    promo_tag: "Bundle",
  },
];

export const MOCK_APPROVALS = [
  {
    id: "q1",
    quotation: "Q-1041",
    customer: "Acme Corp",
    blended_risk: "MEDIUM",
    stage: "Finance",
    assigned_to: "M. Shah",
  },
  {
    id: "q2",
    quotation: "Q-1042",
    customer: "Beta Industries",
    blended_risk: "LOW",
    stage: "Auto-Approved",
    assigned_to: "J. Rao",
  },
  {
    id: "q3",
    quotation: "Q-1043",
    customer: "Delta LLC",
    blended_risk: "HIGH",
    stage: "Sales Manager",
    assigned_to: "A. Turner",
  },
  {
    id: "q4",
    quotation: "Q-1044",
    customer: "Harbor Freight Supply",
    blended_risk: "MEDIUM",
    stage: "Finance",
    assigned_to: "L. Okafor",
  },
  {
    id: "q5",
    quotation: "Q-1045",
    customer: "Nova Retail",
    blended_risk: "LOW",
    stage: "Auto-Approved",
    assigned_to: "K. Bennett",
  },
  {
    id: "q6",
    quotation: "Q-1046",
    customer: "Zenith Co",
    blended_risk: "HIGH",
    stage: "Sales Manager",
    assigned_to: "R. Delgado",
  },
  {
    id: "q7",
    quotation: "Q-1047",
    customer: "Orion Ltd",
    blended_risk: "MEDIUM",
    stage: "Finance",
    assigned_to: "M. Shah",
  },
  {
    id: "q8",
    quotation: "Q-1048",
    customer: "Fairview Distributors",
    blended_risk: "LOW",
    stage: "Auto-Approved",
    assigned_to: "J. Rao",
  },
  {
    id: "q9",
    quotation: "Q-1049",
    customer: "Redwood Logistics",
    blended_risk: "HIGH",
    stage: "Sales Manager",
    assigned_to: "A. Turner",
  },
  {
    id: "q10",
    quotation: "Q-1050",
    customer: "Sterling Foods",
    blended_risk: "MEDIUM",
    stage: "Finance",
    assigned_to: "L. Okafor",
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
    in_stock: 100,
    reserved: 73,
    available: 27,
  },
  {
    warehouse: "West Depot",
    product: "Heavy-Duty Pallet Jack",
    in_stock: 197,
    reserved: 143,
    available: 54,
  },
  {
    warehouse: "West Depot",
    product: "Warehouse LED Fixture",
    in_stock: 132,
    reserved: 26,
    available: 106,
  },
  {
    warehouse: "West Depot",
    product: "Safety Barrier Rail (10ft)",
    in_stock: 136,
    reserved: 95,
    available: 41,
  },
  {
    warehouse: "West Depot",
    product: "Forklift Battery Pack",
    in_stock: 89,
    reserved: 70,
    available: 19,
  },
  {
    warehouse: "East Depot",
    product: "Industrial Shelving Unit",
    in_stock: 72,
    reserved: 7,
    available: 65,
  },
  {
    warehouse: "East Depot",
    product: "Heavy-Duty Pallet Jack",
    in_stock: 145,
    reserved: 127,
    available: 18,
  },
  {
    warehouse: "East Depot",
    product: "Warehouse LED Fixture",
    in_stock: 258,
    reserved: 160,
    available: 98,
  },
  {
    warehouse: "East Depot",
    product: "Safety Barrier Rail (10ft)",
    in_stock: 278,
    reserved: 232,
    available: 46,
  },
  {
    warehouse: "East Depot",
    product: "Forklift Battery Pack",
    in_stock: 225,
    reserved: 76,
    available: 149,
  },
  {
    warehouse: "Central Hub",
    product: "Industrial Shelving Unit",
    in_stock: 167,
    reserved: 46,
    available: 121,
  },
  {
    warehouse: "Central Hub",
    product: "Heavy-Duty Pallet Jack",
    in_stock: 164,
    reserved: 20,
    available: 144,
  },
  {
    warehouse: "Central Hub",
    product: "Warehouse LED Fixture",
    in_stock: 193,
    reserved: 134,
    available: 59,
  },
  {
    warehouse: "Central Hub",
    product: "Safety Barrier Rail (10ft)",
    in_stock: 293,
    reserved: 175,
    available: 118,
  },
  {
    warehouse: "Central Hub",
    product: "Forklift Battery Pack",
    in_stock: 269,
    reserved: 147,
    available: 122,
  },
];

export const MOCK_ORDERS = [
  {
    id: "q1",
    order: "ORD-2091",
    customer: "Acme Corp",
    status: "Split Pending",
    warehouses: "West + East Depot",
  },
  {
    id: "q2",
    order: "ORD-2092",
    customer: "Beta Industries",
    status: "Backorder",
    warehouses: "East Depot",
  },
  {
    id: "q3",
    order: "ORD-2093",
    customer: "Delta LLC",
    status: "Pending",
    warehouses: "Central Hub",
  },
  {
    id: "q4",
    order: "ORD-2094",
    customer: "Harbor Freight Supply",
    status: "Split Pending",
    warehouses: "West Depot",
  },
  {
    id: "q5",
    order: "ORD-2095",
    customer: "Nova Retail",
    status: "Backorder",
    warehouses: "West + East Depot",
  },
  {
    id: "q6",
    order: "ORD-2096",
    customer: "Zenith Co",
    status: "Pending",
    warehouses: "East Depot",
  },
  {
    id: "q7",
    order: "ORD-2097",
    customer: "Orion Ltd",
    status: "Split Pending",
    warehouses: "Central Hub",
  },
  {
    id: "q8",
    order: "ORD-2098",
    customer: "Fairview Distributors",
    status: "Backorder",
    warehouses: "West Depot",
  },
  {
    id: "q9",
    order: "ORD-2099",
    customer: "Redwood Logistics",
    status: "Pending",
    warehouses: "West + East Depot",
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
    customer: "Acme Corp",
    plan: "Care Plan 2yr",
    cycle: "Quarterly",
    next_bill: "Oct 15, 2026",
    status: "Active",
  },
  {
    id: "s2",
    customer: "Beta Industries",
    plan: "Support SLA",
    cycle: "Yearly",
    next_bill: "Nov 1, 2026",
    status: "Active",
  },
  {
    id: "s3",
    customer: "Delta LLC",
    plan: "Care Plan 1yr",
    cycle: "Monthly",
    next_bill: "Nov 12, 2026",
    status: "Paused",
  },
  {
    id: "s4",
    customer: "Harbor Freight Supply",
    plan: "Managed Supply — Pro",
    cycle: "Quarterly",
    next_bill: "Oct 1, 2026",
    status: "Cancelled",
  },
  {
    id: "s5",
    customer: "Nova Retail",
    plan: "Care Plan 2yr",
    cycle: "Yearly",
    next_bill: "Oct 15, 2026",
    status: "Active",
  },
  {
    id: "s6",
    customer: "Zenith Co",
    plan: "Support SLA",
    cycle: "Monthly",
    next_bill: "Nov 1, 2026",
    status: "Active",
  },
  {
    id: "s7",
    customer: "Orion Ltd",
    plan: "Care Plan 1yr",
    cycle: "Quarterly",
    next_bill: "Nov 12, 2026",
    status: "Active",
  },
  {
    id: "s8",
    customer: "Fairview Distributors",
    plan: "Managed Supply — Pro",
    cycle: "Yearly",
    next_bill: "Oct 1, 2026",
    status: "Paused",
  },
  {
    id: "s9",
    customer: "Redwood Logistics",
    plan: "Care Plan 2yr",
    cycle: "Monthly",
    next_bill: "Oct 15, 2026",
    status: "Cancelled",
  },
  {
    id: "s10",
    customer: "Sterling Foods",
    plan: "Support SLA",
    cycle: "Quarterly",
    next_bill: "Nov 1, 2026",
    status: "Active",
  },
  {
    id: "s11",
    customer: "Pinnacle Manufacturing",
    plan: "Care Plan 1yr",
    cycle: "Yearly",
    next_bill: "Nov 12, 2026",
    status: "Active",
  },
  {
    id: "s12",
    customer: "Grayson Wholesale",
    plan: "Managed Supply — Pro",
    cycle: "Monthly",
    next_bill: "Oct 1, 2026",
    status: "Active",
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
    customer: "Acme Corp",
    amount: 12000,
    status: "Unpaid",
    due_date: "Sep 10, 2026",
  },
  {
    id: "i2",
    invoice_no: "INV-3082",
    customer: "Beta Industries",
    amount: 18000,
    status: "Paid",
    due_date: "Sep 22, 2026",
  },
  {
    id: "i3",
    invoice_no: "INV-3083",
    customer: "Delta LLC",
    amount: 68000,
    status: "Partial",
    due_date: "Oct 4, 2026",
  },
  {
    id: "i4",
    invoice_no: "INV-3084",
    customer: "Harbor Freight Supply",
    amount: 56000,
    status: "Paid",
    due_date: "Aug 28, 2026",
  },
  {
    id: "i5",
    invoice_no: "INV-3085",
    customer: "Nova Retail",
    amount: 24000,
    status: "Unpaid",
    due_date: "Sep 10, 2026",
  },
  {
    id: "i6",
    invoice_no: "INV-3086",
    customer: "Zenith Co",
    amount: 46000,
    status: "Paid",
    due_date: "Sep 22, 2026",
  },
  {
    id: "i7",
    invoice_no: "INV-3087",
    customer: "Orion Ltd",
    amount: 22000,
    status: "Partial",
    due_date: "Oct 4, 2026",
  },
  {
    id: "i8",
    invoice_no: "INV-3088",
    customer: "Fairview Distributors",
    amount: 65000,
    status: "Paid",
    due_date: "Aug 28, 2026",
  },
  {
    id: "i9",
    invoice_no: "INV-3089",
    customer: "Redwood Logistics",
    amount: 56000,
    status: "Unpaid",
    due_date: "Sep 10, 2026",
  },
  {
    id: "i10",
    invoice_no: "INV-3090",
    customer: "Sterling Foods",
    amount: 8000,
    status: "Paid",
    due_date: "Sep 22, 2026",
  },
  {
    id: "i11",
    invoice_no: "INV-3091",
    customer: "Pinnacle Manufacturing",
    amount: 12000,
    status: "Partial",
    due_date: "Oct 4, 2026",
  },
  {
    id: "i12",
    invoice_no: "INV-3092",
    customer: "Grayson Wholesale",
    amount: 43000,
    status: "Paid",
    due_date: "Aug 28, 2026",
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

// Seeded internal user, so the shell renders before /auth/me exists.
export const MOCK_SESSION = {
  id: "u1",
  name: "Alex Turner",
  email: "alex.turner@dealflow.corp",
  role: "SALES_REP",
};

// PS section 4 A4: warehouses carry the shipping cost weight the auto-split
// logic uses to minimise shipment count.
export const MOCK_WAREHOUSES = [
  {
    id: "w1",
    name: "Main Warehouse",
    region: "US-West",
    shipping_cost_weight: 1.0,
    active: true,
  },
  {
    id: "w2",
    name: "East Depot",
    region: "US-East",
    shipping_cost_weight: 1.4,
    active: true,
  },
  {
    id: "w3",
    name: "EU Transit Hub",
    region: "EU-Central",
    shipping_cost_weight: 2.1,
    active: false,
  },
];

// PS section 4 A5: recurring plans, proration rules, cancellation policy.
export const MOCK_SUBSCRIPTION_PLANS = [
  {
    id: "p1",
    name: "Care Plan 2yr",
    cycle: "Monthly",
    price: 46,
    proration_enabled: true,
  },
  {
    id: "p2",
    name: "Support SLA",
    cycle: "Quarterly",
    price: 300,
    proration_enabled: true,
  },
  {
    id: "p3",
    name: "Care Plan 1yr",
    cycle: "Monthly",
    price: 28,
    proration_enabled: false,
  },
];

export const MOCK_REPORTS = {
  quotes_created: 18,
  avg_approval_hours: 6.4,
  top_product: "Extended Warranty",
  pipeline_value: 611200,
  by_status: [
    { status: "Draft", count: 3, value: 103550 },
    { status: "Pending Approval", count: 4, value: 180650 },
    { status: "Approved", count: 4, value: 159300 },
    { status: "Negotiation", count: 4, value: 161800 },
    { status: "Confirmed", count: 3, value: 105700 },
  ],
  by_rep: [
    { rep: "Alex Turner", quotations: 11, value: 402300, flagged_lines: 7 },
    { rep: "Jordan Rao", quotations: 7, value: 208900, flagged_lines: 2 },
  ],
};
