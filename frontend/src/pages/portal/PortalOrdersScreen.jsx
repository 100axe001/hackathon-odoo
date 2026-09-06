import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { Td, Th, Tr } from "@/components/ui/Table";
import { C } from "@/constants/theme";
import { money } from "@/utils/money";
import { loadPortalOrders } from "@/api/api-functions/portal";

// What happens after the customer confirms. The brief's portal stops at the
// quotation, but once terms are agreed the question changes to "where is it",
// and having no answer is what made the portal feel like a dead end.
export function PortalOrdersScreen() {
  const [orders, setOrders] = useState(null);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    loadPortalOrders().then(setOrders).catch(setLoadError);
  }, []);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!orders) return null;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-1" style={{ color: C.text }}>
        Orders
      </h1>
      <p className="text-sm mb-6" style={{ color: C.muted }}>
        Everything you have agreed to, and where each part is shipping from.
      </p>

      {orders.length === 0 ? (
        <Card>
          <div className="text-sm py-6 text-center" style={{ color: C.muted }}>
            No confirmed orders yet. Once you confirm a quotation it appears
            here.
          </div>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {orders.map((order) => (
            <Card key={order.id}>
              <div className="flex items-baseline justify-between mb-3">
                <div>
                  <span
                    className="text-base font-semibold"
                    style={{ color: C.text }}
                  >
                    {order.number}
                  </span>
                  <span className="ml-3 text-sm" style={{ color: C.muted }}>
                    {money(order.total)}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge status={order.status} />
                  <span className="text-sm" style={{ color: C.muted }}>
                    {order.fulfillment}
                  </span>
                </div>
              </div>

              {/* The status raises a question - "partly on backorder", says
                  who? - and the person handling the order is the answer. A
                  mailto rather than a name alone, so acting on it is one
                  click and not a search through old email. */}
              <div className="text-sm mb-3" style={{ color: C.muted }}>
                Handled by{" "}
                <a
                  href={`mailto:${order.rep_email}?subject=${encodeURIComponent(order.number)}`}
                  className="font-medium underline"
                  style={{ color: C.text }}
                >
                  {order.rep}
                </a>
              </div>

              {order.shipments.length > 0 && (
                <table className="w-full border-collapse">
                  <thead>
                    <tr>
                      <Th>Item</Th>
                      <Th right>Qty</Th>
                      <Th>Shipping from</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {order.shipments.map((s, i) => (
                      <Tr key={i}>
                        <Td>{s.product}</Td>
                        <Td right>{s.qty}</Td>
                        <Td>
                          {/* A row with no warehouse is a backorder. Saying so
                              plainly beats leaving the cell empty. */}
                          {s.warehouse ?? (
                            <Badge status="Pending" label="On backorder" />
                          )}
                        </Td>
                      </Tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
