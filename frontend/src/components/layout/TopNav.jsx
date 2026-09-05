import { NavLink, useNavigate } from "react-router-dom";
import { NAV_ITEMS } from "@/constants/nav";
import { C } from "@/constants/theme";

// Horizontal module bar, per the wireframe: brand on the left, one tab per
// module, the active tab picked out in white. Active state comes from the URL,
// so a detail screen keeps its section highlighted.
export function TopNav({ onReload, reloading }) {
  const navigate = useNavigate();

  const action = {
    color: "rgba(255,255,255,0.7)",
    border: "1px solid rgba(255,255,255,0.25)",
  };

  return (
    <header
      className="fixed top-0 left-0 right-0 z-40"
      style={{ backgroundColor: C.sidebar }}
    >
      <div className="flex items-center gap-6 px-6 h-14">
        <span className="text-sm font-semibold tracking-tight text-white shrink-0">
          DealFlow<span style={{ color: C.accent }}>360</span>
        </span>

        <nav className="flex items-center gap-1 overflow-x-auto">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.key}
              to={item.path}
              className="rounded-md px-3 py-1.5 text-sm whitespace-nowrap transition-colors duration-150"
              style={({ isActive }) => ({
                backgroundColor: isActive ? "#fff" : "transparent",
                color: isActive ? C.text : "rgba(255,255,255,0.7)",
                fontWeight: isActive ? 500 : 400,
              })}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* PS section 4 B1: the three workspace actions. */}
        <div className="flex items-center gap-2 ml-auto shrink-0">
          <button
            onClick={onReload}
            disabled={reloading}
            className="text-xs rounded-md px-2.5 py-1.5 transition-colors duration-150"
            style={{ ...action, opacity: reloading ? 0.5 : 1 }}
          >
            {reloading ? "Reloading…" : "Reload Data"}
          </button>
          <button
            onClick={() => navigate("/admin/discount-config")}
            className="text-xs rounded-md px-2.5 py-1.5 transition-colors duration-150"
            style={action}
          >
            Go to Back-end
          </button>
          <button
            onClick={() => navigate("/login")}
            className="text-xs rounded-md px-2.5 py-1.5 transition-colors duration-150"
            style={action}
          >
            Close Workspace
          </button>
        </div>
      </div>
    </header>
  );
}
