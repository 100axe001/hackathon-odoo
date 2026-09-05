import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadOrders, loadStock } from "@/api/api-functions/fulfillment";

export function FulfillmentScreen({ setRoute }) {
  const [stock, setStock] = useState([]);
  const [orders, setOrders] = useState([]);
  useEffect(() => {
    loadStock().then(setStock);
    loadOrders().then(setOrders);
  }, []);
  return (
    <Transition keyProp="fulfillment">
      <PageHeader title="Fulfillment" />
      <Card className="mb-6">
        <div className="text-base font-semibold mb-3" style={{ color: C.text }}>
          Stock Overview
        </div>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Warehouse</Th>
              <Th>Product</Th>
              <Th right>In Stock</Th>
              <Th right>Reserved</Th>
              <Th right>Available</Th>
            </tr>
          </thead>
          <tbody>
            {stock.map((s, i) => (
              <Tr key={i}>
                <Td>{s.warehouse}</Td>
                <Td>{s.product}</Td>
                <Td right>{s.in_stock}</Td>
                <Td right>{s.reserved}</Td>
                <Td
                  right
                  className={s.available === 0 ? "font-semibold" : ""}
                  style={s.available === 0 ? { color: C.dangerText } : {}}
                >
                  {s.available}
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
              <Th>Order</Th>
              <Th>Customer</Th>
              <Th>Status</Th>
              <Th>Warehouses</Th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <Tr
                key={o.id}
                onClick={() =>
                  setRoute({ name: "fulfillment-detail", id: o.id })
                }
              >
                <Td>{o.order}</Td>
                <Td>{o.customer}</Td>
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
