import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { Transition } from "@/components/ui/Transition";

export function ReportsScreen() {
  const [period, setPeriod] = useState("Last 30 Days");
  const [team, setTeam] = useState("All Teams");
  const [status, setStatus] = useState("All Statuses");
  const [product, setProduct] = useState("All Products");
  return (
    <Transition keyProp="reports">
      <PageHeader
        title="Reports"
        action={
          <div className="flex gap-3">
            <Button variant="secondary">Export PDF</Button>
            <Button variant="secondary">Export XLS</Button>
          </div>
        }
      />
      <div className="flex gap-3 mb-6">
        <Select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          options={["Last 30 Days", "Last 90 Days", "This Year"]}
        />
        <Select
          value={team}
          onChange={(e) => setTeam(e.target.value)}
          options={["All Teams", "East Region", "West Region"]}
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={["All Statuses", "Pending", "Approved", "Rejected"]}
        />
        <Select
          value={product}
          onChange={(e) => setProduct(e.target.value)}
          options={["All Products", "Hardware", "Services"]}
        />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Quotes Created" value="142" />
        <StatCard label="Avg Approval Time" value="1.8 days" />
        <StatCard label="Top Upsold Product" value="Extended Warranty" />
      </div>
    </Transition>
  );
}
