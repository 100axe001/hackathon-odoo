import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import { TopNav } from "@/components/layout/TopNav";
import { PortalDevSwitch } from "@/components/layout/PortalDevSwitch";
import { C } from "@/constants/theme";

// Internal shell: horizontal module bar, then the centred work area.
export function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [reloading, setReloading] = useState(false);

  // Remount the current route so every loader runs again. Cheaper than threading
  // a refetch callback through eighteen screens, and it is what "Reload Data"
  // means to a rep: pull fresh pricing, stock and approval state.
  const reload = () => {
    setReloading(true);
    navigate(location.pathname, { replace: true });
    setTimeout(() => setReloading(false), 400);
  };

  return (
    <div style={{ backgroundColor: C.bg, minHeight: "100vh" }}>
      <TopNav onReload={reload} reloading={reloading} />
      <main className="pt-14">
        <div className="px-8 py-6" style={{ maxWidth: 1340, margin: "0 auto" }}>
          <Outlet key={reloading ? "reloading" : location.pathname} />
        </div>
      </main>
      <PortalDevSwitch />
    </div>
  );
}
