import { Card } from "@/components/ui/Card";
import { C } from "@/constants/theme";

// The wireframe puts a short qualifier under every figure - "4 quotations
// waiting", "3 flagged by Deal Health". The number alone reads as filler.
export function StatCard({ label, value, detail, onClick, valueColor }) {
  return (
    <Card
      onClick={onClick}
      className={
        onClick ? "hover:bg-[#FAF7F2] transition-colors duration-150" : ""
      }
    >
      <div
        className="text-xs uppercase font-medium mb-1 tracking-wide"
        style={{ color: C.muted }}
      >
        {label}
      </div>
      <div
        className="text-3xl font-semibold tabular-nums leading-none mb-1.5"
        style={{ color: valueColor || C.text }}
      >
        {value}
      </div>
      {detail && (
        <div className="text-xs" style={{ color: C.muted }}>
          {detail}
        </div>
      )}
    </Card>
  );
}
