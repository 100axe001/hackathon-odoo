import { Outlet } from "react-router-dom";
import { PortalNav } from "@/components/layout/PortalNav";
import { C } from "@/constants/theme";

// Customer shell. Deliberately shares nothing with AppLayout - no sidebar, no
// internal nav - because the brief (section 7) requires the portal to be a real
// separate view rather than an internal screen with a different label.
export function PortalLayout() {
  return (
    <div style={{ backgroundColor: C.bg, minHeight: "100vh" }}>
      <PortalNav />
      <div className="p-8 pt-8">
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
