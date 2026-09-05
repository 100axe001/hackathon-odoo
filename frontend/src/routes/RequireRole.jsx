import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/hooks/useSession";
import { C } from "@/constants/theme";

// Route guard. This is the UI half only - it stops a customer seeing an internal
// screen in the nav. The server half is what actually protects the data: every
// internal endpoint rejects a customer token, and /portal/* rejects an internal
// one. Never rely on this alone.
export function RequireRole({ allow }) {
  const { user, loading } = useSession();
  const location = useLocation();

  // Render nothing until the session resolves. Redirecting while loading would
  // bounce a signed-in user to /login on every refresh.
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center text-sm"
        style={{ backgroundColor: C.bg, color: C.muted }}
      >
        Loading…
      </div>
    );
  }

  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;

  if (!allow.includes(user.role)) {
    // Send each role somewhere it is allowed to be, rather than looping on /login.
    return (
      <Navigate
        to={user.role === "CUSTOMER" ? "/portal" : "/dashboard"}
        replace
      />
    );
  }

  return <Outlet />;
}
