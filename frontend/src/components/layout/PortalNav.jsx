import { NavLink, useNavigate } from "react-router-dom";
import { LogoMarkLight } from "@/components/layout/LogoMark";
import { useSession } from "@/hooks/useSession";
import { C } from "@/constants/theme";

const TABS = [
  { label: "Quotations", to: "/portal", end: true },
  { label: "Orders", to: "/portal/orders" },
  { label: "Billing", to: "/portal/billing" },
  { label: "Profile", to: "/portal/profile" },
];

export function PortalNav() {
  const { user, signOut } = useSession();
  const navigate = useNavigate();

  const leave = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };
  return (
    <div
      className="bg-white border-b sticky top-0 z-10"
      style={{ borderColor: C.border }}
    >
      <div className="max-w-[1000px] mx-auto flex items-center justify-between px-8 py-4">
        <LogoMarkLight />
        <div className="flex items-center gap-8">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className="text-sm pb-1 transition-colors duration-150"
              style={({ isActive }) => ({
                color: isActive ? C.accent : C.muted,
                borderBottom: isActive
                  ? `2px solid ${C.accent}`
                  : "2px solid transparent",
                fontWeight: isActive ? 500 : 400,
              })}
            >
              {tab.label}
            </NavLink>
          ))}
        </div>
        {/* A customer needs to see whose account they are looking at as much as
            an internal user does - more so, since the portal has no sidebar. */}
        <div className="flex items-center gap-4">
          <div className="text-right leading-tight">
            <div className="text-sm font-medium" style={{ color: C.text }}>
              {user?.name ?? ""}
            </div>
            <div className="text-xs" style={{ color: C.muted }}>
              Customer account
            </div>
          </div>
          {/* The portal has no other chrome, so without this there was no way
              out of it except clearing the cookie by hand. */}
          <button
            onClick={leave}
            className="text-xs rounded-md px-2.5 py-1.5 transition-colors duration-150"
            style={{ border: `1px solid ${C.border}`, color: C.muted }}
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
