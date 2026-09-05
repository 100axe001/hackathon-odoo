import { Outlet } from "react-router-dom";
import { useState } from "react";
import { PortalNav } from "@/components/layout/PortalNav";
import { PortalDevSwitch } from "@/components/layout/PortalDevSwitch";
import { C } from "@/constants/theme";

// Customer shell. Deliberately shares nothing with AppLayout - no sidebar, no
// internal nav - because the brief (section 7) requires the portal to be a real
// separate view rather than an internal screen with a different label.
export function PortalLayout() {
  const [portalTab, setPortalTab] = useState("My Quotation");

  return (
    <div style={{ backgroundColor: C.bg, minHeight: "100vh" }}>
      <PortalNav portalTab={portalTab} setPortalTab={setPortalTab} />
      <div className="p-8 pt-8">
        <div style={{ maxWidth: 900, margin: "0 auto" }}>
          <Outlet />
        </div>
      </div>
      <PortalDevSwitch />
    </div>
  );
}
