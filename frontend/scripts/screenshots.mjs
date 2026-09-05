// Screenshots every route into scripts/shots/ and reports any console error.
// A Vite build is not proof a screen renders - this is. Run it before a demo.
//
//   npm run dev            # in one terminal
//   npm run shots          # in another
import { chromium } from "playwright";
import fs from "node:fs";

const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const OUT = new URL("./shots/", import.meta.url).pathname;

const ROUTES = [
  ["login", "/login"],
  ["dashboard", "/dashboard"],
  ["quotations", "/quotations"],
  ["quotation-detail", "/quotations/q1"],
  ["approvals", "/approvals"],
  ["approval-detail", "/approvals/q1"],
  ["fulfillment", "/fulfillment"],
  ["fulfillment-detail", "/fulfillment/q5"],
  ["subscriptions", "/subscriptions"],
  ["billing-detail", "/subscriptions/s1"],
  ["invoices", "/invoices"],
  ["invoice-detail", "/invoices/i2"],
  ["deal-health", "/deal-health"],
  ["reports", "/reports"],
  ["products", "/products"],
  ["product-detail", "/products/p1"],
  ["admin-discount-config", "/admin/discount-config"],
  ["admin-warehouses", "/admin/warehouses"],
  ["admin-subscription-plans", "/admin/subscription-plans"],
  ["portal", "/portal/quotations/q3"],
];

fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });

const errors = [];
page.on("pageerror", (e) => errors.push(`${page.url()} :: ${e.message}`));
page.on("console", (m) => {
  if (m.type() === "error") errors.push(`${page.url()} :: ${m.text()}`);
});

for (const [name, path] of ROUTES) {
  await page.goto(BASE + path, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: true });
  const [h, rows] = await page.evaluate(() => [
    document.body.scrollHeight,
    document.querySelectorAll("tbody tr, article").length,
  ]);
  console.log(`  ${name.padEnd(26)} ${String(h).padStart(5)}px  ${rows} rows/cards`);
}

await browser.close();
console.log(
  errors.length
    ? `\n${errors.length} CONSOLE ERRORS:\n` + [...new Set(errors)].join("\n")
    : "\nno console errors",
);
