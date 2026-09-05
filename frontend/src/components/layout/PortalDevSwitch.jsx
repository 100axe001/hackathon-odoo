import { useNavigate } from "react-router-dom";
import { useSession } from "@/hooks/useSession";
import { C } from "@/constants/theme";

// Reviewer convenience only: the portal and login screens have no sidebar entry.
// This is NOT how a customer reaches the portal - that is role-gated routing in
// src/routes. Remove before any real deployment.
export function PortalDevSwitch() {
  const navigate = useNavigate();
  const { signOut } = useSession();

  const style = { border: `1px solid ${C.border}`, color: C.muted };

  // Signing out has to clear the cookie on the server. Navigating to /login
  // left the session alive, so the next URL typed put you back in.
  const handleSignOut = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

  return (
    <div className="fixed bottom-4 left-4 flex gap-2 z-40">
      <button
        onClick={() => navigate("/portal")}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={style}
      >
        View Customer Portal
      </button>
      <button
        onClick={handleSignOut}
        className="text-xs rounded-md px-2.5 py-1.5 bg-white transition-colors duration-150"
        style={style}
      >
        Log Out
      </button>
    </div>
  );
}
