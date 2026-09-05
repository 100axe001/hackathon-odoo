import { NavLink } from "react-router-dom";
import { C } from "@/constants/theme";

// The three backend configuration surfaces PS section 4 A3/A4/A5 asks for.
// Grouped behind one sub-nav so "Go to Back-end" lands somewhere coherent.
const TABS = [
  { to: "/admin/discount-config", label: "Discount Tiers" },
  { to: "/admin/warehouses", label: "Warehouses" },
  { to: "/admin/subscription-plans", label: "Subscription Plans" },
];

export function AdminTabs() {
  return (
    <div
      className="flex items-center gap-1 mb-6 pb-3"
      style={{ borderBottom: `1px solid ${C.border}` }}
    >
      {TABS.map((t) => (
        <NavLink
          key={t.to}
          to={t.to}
          className="rounded-md px-3 py-1.5 text-sm transition-colors duration-150"
          style={({ isActive }) =>
            isActive
              ? { backgroundColor: "#FDF0E7", color: C.accent, fontWeight: 500 }
              : { color: C.muted }
          }
        >
          {t.label}
        </NavLink>
      ))}
    </div>
  );
}
