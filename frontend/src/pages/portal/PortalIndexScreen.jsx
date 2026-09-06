import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { money } from "@/utils/money";
import { loadPortalQuotations } from "@/api/api-functions/portal";

// Where a customer lands. The portal used to redirect to a hardcoded quotation
// id, which only worked because the demo seed happened to contain it. This asks
// the server which quotations are actually theirs.
export function PortalIndexScreen() {
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    // No auto-redirect: the portal now has Orders, Billing and Profile
    // alongside this, so skipping the list would drop the customer into one
    // quotation with no sense of what else is here.
    loadPortalQuotations().then(setRows).catch(setLoadError);
  }, [navigate]);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (rows === null) return null;

  return (
    <div className="max-w-[760px] mx-auto py-10 px-6">
      <h1 className="text-xl font-semibold mb-1" style={{ color: C.text }}>
        My Quotations
      </h1>
      <p className="text-sm mb-6" style={{ color: C.muted }}>
        Open a quotation to review the terms, ask a question, or confirm.
      </p>

      {rows.length === 0 ? (
        <Card>
          <div className="text-sm py-6 text-center" style={{ color: C.muted }}>
            You have no quotations yet. Your account manager will send one when
            it is ready.
          </div>
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {rows.map((q) => (
            <Card
              key={q.id}
              onClick={() => navigate(`/portal/quotations/${q.id}`)}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div
                    className="text-sm font-medium"
                    style={{ color: C.text }}
                  >
                    {q.number}
                  </div>
                  <div
                    className="text-sm tabular-nums"
                    style={{ color: C.muted }}
                  >
                    {money(q.total)}
                  </div>
                </div>
                <Badge status={q.status} />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
