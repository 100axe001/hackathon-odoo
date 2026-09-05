import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useSession } from "@/hooks/useSession";

// Route guard. This is the UI half only - it stops a customer seeing an internal
// screen in the nav. The server half is what actually protects the data: every
// internal endpoint must reject a customer token, and /portal/* must reject an
// internal one. Never rely on this alone.
export function RequireRole({ allow }) {
  const { user, loading } = useSession();
  const location = useLocation();

  if (loading) return null;
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
