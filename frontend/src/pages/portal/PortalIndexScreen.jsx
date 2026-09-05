import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { C } from "@/constants/theme";
import { loadPortalQuotations } from "@/api/api-functions/portal";

// Where a customer lands. The portal used to redirect to a hardcoded quotation
// id, which only worked because the demo seed happened to contain it. This asks
// the server which quotations are actually theirs.
export function PortalIndexScreen() {
  const navigate = useNavigate();
  const [rows, setRows] = useState(null);

  useEffect(() => {
    loadPortalQuotations().then((list) => {
      // One quotation is the common case, so go straight to it rather than
      // making the customer click through a list of one.
      if (list.length === 1) {
        navigate(`/portal/quotations/${list[0].id}`, { replace: true });
        return;
      }
      setRows(list);
    });
  }, [navigate]);

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
                    ${q.total.toLocaleString()}
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
