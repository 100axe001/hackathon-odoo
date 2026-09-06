import { NavLink, useNavigate } from "react-router-dom";
import { NAV_ITEMS } from "@/constants/nav";
import { useSession } from "@/hooks/useSession";
import { C } from "@/constants/theme";

// Horizontal module bar, per the wireframe: brand on the left, one tab per
// module, the active tab picked out in white. Active state comes from the URL,
// so a detail screen keeps its section highlighted.
// "Sam Okafor" -> "SO". Two letters is enough to tell four demo accounts apart.
function initials(name) {
  return String(name || "?")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

function roleLabel(role) {
  return String(role || "")
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export function TopNav({ onReload, reloading }) {
  const navigate = useNavigate();
  const { user, signOut } = useSession();

  const closeWorkspace = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

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

        {/* Who you are signed in as. Four roles see four different views of
            the same deal, so demonstrating this without saying whose screen it
            is leaves the audience guessing. */}
        <div className="flex items-center gap-2 ml-auto shrink-0">
          {user && (
            <div
              className="flex items-center gap-2 pr-3 mr-1"
              style={{ borderRight: "1px solid rgba(255,255,255,0.2)" }}
            >
              <span
                className="rounded-full flex items-center justify-center text-xs font-semibold shrink-0"
                style={{
                  width: 26,
                  height: 26,
                  backgroundColor: "rgba(255,255,255,0.16)",
                  color: "#fff",
                }}
              >
                {initials(user.name)}
              </span>
              <span className="leading-tight">
                <span
                  className="block text-xs font-medium"
                  style={{ color: "#fff" }}
                >
                  {user.name}
                </span>
                <span
                  className="block text-[10px] tracking-wide uppercase"
                  style={{ color: "rgba(255,255,255,0.6)" }}
                >
                  {roleLabel(user.role)}
                </span>
              </span>
            </div>
          )}
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
          {/* Ends the session on the server, not just in the browser.
              Navigating to /login left the cookie valid, so typing any URL put
              you straight back in. */}
          <button
            onClick={closeWorkspace}
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
