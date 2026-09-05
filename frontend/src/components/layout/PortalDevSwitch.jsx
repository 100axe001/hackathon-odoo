import { useNavigate } from "react-router-dom";
import { C } from "@/constants/theme";

// Reviewer convenience only: the portal and login screens have no sidebar entry.
// This is NOT how a customer reaches the portal - that is role-gated routing in
// src/routes. Remove this before any real deployment.
export function PortalDevSwitch() {
  const navigate = useNavigate();

  const style = {
    border: `1px solid ${C.border}`,
    color: C.muted,
  };

  return (
    <div className="fixed bottom-4 left-4 flex gap-2 z-40">
      <button
        onClick={() => navigate("/portal/quotations/q3")}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={style}
      >
        View Customer Portal
      </button>
      <button
        onClick={() => navigate("/login")}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={style}
      >
        Log Out
      </button>
    </div>
  );
}
