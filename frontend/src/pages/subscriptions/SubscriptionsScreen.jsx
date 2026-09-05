import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { StatPill } from "@/components/ui/StatPill";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Transition } from "@/components/ui/Transition";
import { loadSubscriptions } from "@/api/api-functions/subscriptions";

export function SubscriptionsScreen() {
  const navigate = useNavigate();
  const [data, setData] = useState([]);
  useEffect(() => {
    loadSubscriptions().then(setData);
  }, []);
  const active = data.filter((s) => s.status === "Active").length;
  const paused = data.filter((s) => s.status === "Paused").length;
  const cancelled = data.filter((s) => s.status === "Cancelled").length;
  return (
    <Transition keyProp="subscriptions">
      <PageHeader
        title="Subscriptions"
        action={<Button variant="secondary">+ New Plan (Admin)</Button>}
      />
      <div className="flex gap-3 mb-4">
        <StatPill label="Active" count={active} tone="success" />
        <StatPill label="Paused" count={paused} tone="warn" />
        <StatPill label="Cancelled" count={cancelled} tone="neutral" />
      </div>
      <Card>
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <Th>Customer</Th>
              <Th>Plan</Th>
              <Th>Cycle</Th>
              <Th>Next Bill</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            {data.map((s) => (
              <Tr key={s.id} onClick={() => navigate(`/subscriptions/${s.id}`)}>
                <Td>{s.customer}</Td>
                <Td>{s.plan}</Td>
                <Td>{s.cycle}</Td>
                <Td>{s.next_bill}</Td>
                <Td>
                  <Badge status={s.status} />
                </Td>
              </Tr>
            ))}
          </tbody>
        </table>
      </Card>
    </Transition>
  );
}
