import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { nextSort, SortableTh, sortRows } from "@/components/ui/SortableTh";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadOrders, loadStock } from "@/api/api-functions/fulfillment";

const ALL = "All companies";

export function FulfillmentScreen() {
  const navigate = useNavigate();
  const [stock, setStock] = useState([]);
  const [orders, setOrders] = useState([]);
  const [customer, setCustomer] = useState(ALL);
  const [stockSort, setStockSort] = useState({
    key: "warehouse",
    direction: "asc",
  });
  const [orderSort, setOrderSort] = useState({
    key: "order",
    direction: "asc",
  });

  const sortStock = (key) => setStockSort((c) => nextSort(c, key));
  const sortOrders = (key) => setOrderSort((c) => nextSort(c, key));
  useEffect(() => {
    loadStock().then(setStock);
    loadOrders().then(setOrders);
  }, []);
  // Every company with a claim on stock or an order waiting to ship. Built
  // from the rows, so the filter can never offer a company with nothing on it.
  const companies = Array.from(
    new Set([
      ...stock.flatMap((s) => s.reserved_for.map((r) => r.customer)),
      ...orders.map((o) => o.customer),
    ]),
  ).sort();

  const forCustomer = (row) =>
    customer === ALL || row.reserved_for.some((r) => r.customer === customer);

  const stockRows = sortRows(
    stock.filter(forCustomer),
    stockSort,
    (row, key) =>
      key === "reserved_for"
        ? row.reserved_for.map((r) => r.customer).join(", ")
        : row[key],
  );

  const orderRows = sortRows(
    orders.filter((o) => customer === ALL || o.customer === customer),
    orderSort,
    (row, key) => row[key],
  );

  return (
    <Transition keyProp="fulfillment">
      <PageHeader
        title="Fulfillment"
        subtitle="Which company each reserved unit belongs to, and what is still waiting to ship."
        action={
          <Select
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            options={[ALL, ...companies]}
          />
        }
      />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Stock Overview
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <SortableTh
                column="warehouse"
                sort={stockSort}
                onSort={sortStock}
              >
                Warehouse
              </SortableTh>
              <SortableTh column="product" sort={stockSort} onSort={sortStock}>
                Product
              </SortableTh>
              <SortableTh
                column="reserved_for"
                sort={stockSort}
                onSort={sortStock}
              >
                Reserved for
              </SortableTh>
              <Th right>In Stock</Th>
              <SortableTh
                column="reserved"
                sort={stockSort}
                onSort={sortStock}
                right
              >
                Reserved
              </SortableTh>
              <SortableTh
                column="available"
                sort={stockSort}
                onSort={sortStock}
                right
              >
                Available
              </SortableTh>
              <Th right>Reorder at</Th>
              <Th>Replenishment</Th>
            </tr>
          </thead>
          <tbody>
            {stockRows.map((s, i) => (
              <Tr key={i}>
                <Td>{s.warehouse}</Td>
                <Td>{s.product}</Td>
                <Td>
                  {/* The reserved figure alone says stock is spoken for but
                      not by whom, which is the question on a shipping desk. */}
                  {s.reserved_for.length === 0 ? (
                    <span className="text-xs" style={{ color: C.muted }}>
                      Unreserved
                    </span>
                  ) : (
                    <div className="flex flex-col gap-0.5">
                      {s.reserved_for.map((r) => (
                        <span key={r.quotation} className="text-xs">
                          <span style={{ color: C.text }}>{r.customer}</span>
                          <span style={{ color: C.muted }}>
                            {" "}
                            {r.quotation} · {r.qty}
                          </span>
                        </span>
                      ))}
                    </div>
                  )}
                </Td>
                <Td right>{s.in_stock}</Td>
                <Td right>{s.reserved}</Td>
                <Td
                  right
                  className={s.available === 0 ? "font-semibold" : ""}
                  style={s.available === 0 ? { color: C.dangerText } : {}}
                >
                  {s.available}
                </Td>
                <Td right style={{ color: C.muted }}>
                  {s.reorder_point > 0 ? s.reorder_point : "—"}
                </Td>
                <Td>
                  {/* PS 4-A4: the replenishment rule, not just the count. A row
                      at or below its reorder point is due for restock. */}
                  {s.needs_restock ? (
                    <Badge
                      status="Pending"
                      label={`Reorder ${s.reorder_qty}`}
                    />
                  ) : (
                    <span className="text-xs" style={{ color: C.muted }}>
                      {s.reorder_point > 0 ? "In policy" : "No rule set"}
                    </span>
                  )}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card>
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Orders Awaiting Fulfillment
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <SortableTh column="order" sort={orderSort} onSort={sortOrders}>
                Order
              </SortableTh>
              <SortableTh
                column="customer"
                sort={orderSort}
                onSort={sortOrders}
              >
                Customer
              </SortableTh>
              <SortableTh
                column="handled_by"
                sort={orderSort}
                onSort={sortOrders}
              >
                Handled by
              </SortableTh>
              <SortableTh column="status" sort={orderSort} onSort={sortOrders}>
                Status
              </SortableTh>
              <Th>Warehouses</Th>
            </tr>
          </thead>
          <tbody>
            {orderRows.map((o) => (
              <Tr key={o.id} onClick={() => navigate(`/fulfillment/${o.id}`)}>
                <Td>{o.order}</Td>
                <Td>{o.customer}</Td>
                {/* Fulfillment is gated to the deal's own rep, so the queue has
                    to say whose order it is before anyone opens one. */}
                <Td>{o.handled_by}</Td>
                <Td>
                  <Badge status={o.status} />
                </Td>
                <Td className="text-xs" style={{ color: C.muted }}>
                  {o.warehouses}
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
