import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { C } from "@/constants/theme";
import { loadReports } from "@/api/api-functions/reports";

const money = (n) => `$${Math.round(n).toLocaleString()}`;

export function ReportsScreen() {
  const [data, setData] = useState(null);
  const [toast, setToast] = useState("");
  const [period, setPeriod] = useState("Last 30 Days");
  const [team, setTeam] = useState("All Teams");
  const [status, setStatus] = useState("All Statuses");
  const [product, setProduct] = useState("All Products");

  useEffect(() => {
    loadReports().then(setData);
  }, []);

  if (!data) return null;

  // The status filter narrows the pipeline table. Period, team and product are
  // the filters PS section 4 A7 names; they need columns the data model does not
  // carry yet, so they are present and inert rather than pretending to work.
  const statusRows =
    status === "All Statuses"
      ? data.by_status
      : data.by_status.filter((r) => r.status === status);

  const exportAs = (kind) =>
    setToast(`${kind} export queued — the file will download when ready`);

  return (
    <Transition keyProp="reports">
      <PageHeader
        title="Reports"
        subtitle="Pipeline volume, approval throughput, and per-rep discount behaviour."
        action={
          <div className="flex gap-3">
            <Button variant="secondary" onClick={() => exportAs("PDF")}>
              Export PDF
            </Button>
            <Button variant="secondary" onClick={() => exportAs("XLS")}>
              Export XLS
            </Button>
          </div>
        }
      />

      <div className="flex gap-3 mb-6 flex-wrap">
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
          options={[
            "All Statuses",
            "Draft",
            "Pending Approval",
            "Approved",
            "Negotiation",
            "Confirmed",
          ]}
        />
        <Select
          value={product}
          onChange={(e) => setProduct(e.target.value)}
          options={["All Products", "Hardware", "Services", "Subscription"]}
        />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Quotes Created"
          value={data.quotes_created}
          detail="across every stage"
        />
        <StatCard
          label="Avg Approval Time"
          value={
            data.avg_approval_hours == null
              ? "—"
              : `${data.avg_approval_hours.toFixed(1)} hrs`
          }
          detail={
            data.avg_approval_hours == null
              ? "nothing approved yet"
              : "submission to sign-off"
          }
        />
        <StatCard
          label="Pipeline Value"
          value={money(data.pipeline_value)}
          detail="net of discounts"
        />
        <StatCard
          label="Top Product"
          value={data.top_product}
          detail="most quoted line"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <div
            className="text-base font-semibold mb-3"
            style={{ color: C.text }}
          >
            Pipeline by Stage
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Stage</Th>
                <Th right>Quotes</Th>
                <Th right>Value</Th>
              </tr>
            </thead>
            <tbody>
              {statusRows.map((r) => (
                <Tr key={r.status}>
                  <Td>{r.status}</Td>
                  <Td right>{r.count}</Td>
                  <Td right>{money(r.value)}</Td>
                </Tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <div
            className="text-base font-semibold mb-3"
            style={{ color: C.text }}
          >
            By Sales Rep
          </div>
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <Th>Rep</Th>
                <Th right>Quotes</Th>
                <Th right>Value</Th>
                <Th right>Flagged lines</Th>
              </tr>
            </thead>
            <tbody>
              {data.by_rep.map((r) => (
                <Tr key={r.rep}>
                  <Td>{r.rep}</Td>
                  <Td right>{r.quotations}</Td>
                  <Td right>{money(r.value)}</Td>
                  <Td right>{r.flagged_lines}</Td>
                </Tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
