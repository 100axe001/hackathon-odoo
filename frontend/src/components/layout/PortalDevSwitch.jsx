import { C } from "@/constants/theme";

// Small fixed link so reviewers can reach the portal + login screens, which have no
// sidebar entry point per the route map (kept unobtrusive, bottom-left corner).
export function PortalDevSwitch({ setRoute }) {
  return (
    <div className="fixed bottom-4 left-4 flex gap-2 z-40">
      <button
        onClick={() => setRoute({ name: "portal-negotiation", id: "q3" })}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={{ border: `1px solid ${C.border}`, color: C.muted }}
      >
        View Customer Portal
      </button>
      <button
        onClick={() => setRoute({ name: "login", id: null })}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={{ border: `1px solid ${C.border}`, color: C.muted }}
      >
        Log Out
      </button>
    </div>
  );
}
