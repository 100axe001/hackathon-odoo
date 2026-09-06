import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Select } from "@/components/ui/Select";
import { StatCard } from "@/components/ui/StatCard";
import { Td, Th, Tr } from "@/components/ui/Table";
import { Toast } from "@/components/ui/Toast";
import { Transition } from "@/components/ui/Transition";
import { LoadFailed } from "@/components/ui/LoadFailed";
import { C } from "@/constants/theme";
import { loadReports } from "@/api/api-functions/reports";
import { downloadCsv, printReport } from "@/utils/exportReport";

const money = (n) => `$${Math.round(n).toLocaleString()}`;

// Label to day count. "All time" sends no days at all rather than a huge
// number, so the server does not filter on a date it cannot really mean.
const PERIODS = {
  "Last 30 Days": 30,
  "Last 90 Days": 90,
  "This Year": 365,
  "All Time": null,
};

const ANY_REP = "All Reps";
const ANY_CATEGORY = "All Products";
const ANY_STATUS = "All Statuses";

export function ReportsScreen() {
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [toast, setToast] = useState("");
  const [period, setPeriod] = useState("Last 90 Days");
  const [rep, setRep] = useState(ANY_REP);
  const [status, setStatus] = useState(ANY_STATUS);
  const [category, setCategory] = useState(ANY_CATEGORY);

  // Period, rep and category are server-side: they change which rows the
  // aggregates are built from, so every figure on the page moves together.
  useEffect(() => {
    loadReports({
      days: PERIODS[period],
      rep: rep === ANY_REP ? null : rep,
      category: category === ANY_CATEGORY ? null : category,
    })
      .then(setData)
      .catch(setLoadError);
  }, [period, rep, category]);

  if (loadError)
    return (
      <LoadFailed error={loadError} onRetry={() => window.location.reload()} />
    );
  if (!data) return null;

  // Status is the exception, and stays client-side: it is a breakdown *of* the
  // result, so filtering it server-side would leave one row and no comparison.
  const statusRows =
    status === ANY_STATUS
      ? data.by_status
      : data.by_status.filter((r) => r.status === status);

  const scope = [
    period,
    rep === ANY_REP ? null : rep,
    category === ANY_CATEGORY ? null : category,
    status === ANY_STATUS ? null : status,
  ]
    .filter(Boolean)
    .join(" · ");

  const exportCsv = () => {
    downloadCsv(`dealflow-report-${PERIODS[period] ?? "all"}d`, [
      ["Report scope", scope],
      [],
      ["Quotes created", data.quotes_created],
      [
        "Average approval hours",
        data.avg_approval_hours == null
          ? ""
          : data.avg_approval_hours.toFixed(1),
      ],
      ["Pipeline value", Math.round(data.pipeline_value)],
      ["Top product", data.top_product],
      [],
      ["Stage", "Quotes", "Value"],
      ...statusRows.map((r) => [r.status, r.count, Math.round(r.value)]),
      [],
      ["Rep", "Quotes", "Value", "Flagged lines"],
      ...data.by_rep.map((r) => [
        r.rep,
        r.quotations,
        Math.round(r.value),
        r.flagged_lines,
      ]),
    ]);
    setToast("Report downloaded as CSV");
  };

  return (
    <Transition keyProp="reports">
      <PageHeader
        title="Reports"
        subtitle="Pipeline volume, approval throughput, and per-rep discount behaviour."
        action={
          <div className="flex gap-3">
            <Button variant="secondary" onClick={printReport}>
              Export PDF
            </Button>
            <Button variant="secondary" onClick={exportCsv}>
              Export XLS
            </Button>
          </div>
        }
      />

      <div className="flex gap-3 mb-6 flex-wrap items-center">
        <Select
          value={period}
          onChange={(e) => setPeriod(e.target.value)}
          options={Object.keys(PERIODS)}
        />
        <Select
          value={rep}
          onChange={(e) => setRep(e.target.value)}
          options={[ANY_REP, ...(data.filter_options?.reps ?? [])]}
        />
        <Select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          options={[
            ANY_STATUS,
            "Draft",
            "Pending Approval",
            "Approved",
            "Negotiation",
            "Confirmed",
          ]}
        />
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={[ANY_CATEGORY, ...(data.filter_options?.categories ?? [])]}
        />
        <span className="text-sm ml-auto" style={{ color: C.muted }}>
          Showing {scope}
        </span>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Quotes Created"
          value={data.quotes_created}
          detail="in the selected period"
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
          {statusRows.length === 0 && (
            <div
              className="text-sm py-6 text-center"
              style={{ color: C.muted }}
            >
              No quotations match these filters.
            </div>
          )}
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
          {data.by_rep.length === 0 && (
            <div
              className="text-sm py-6 text-center"
              style={{ color: C.muted }}
            >
              No reps have quotations in this period.
            </div>
          )}
        </Card>
      </div>

      {toast && <Toast message={toast} onClose={() => setToast("")} />}
    </Transition>
  );
}
