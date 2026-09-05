import { Card } from "@/components/ui/Card";
import { C } from "@/constants/theme";

export function StatCard({ label, value, onClick, valueColor }) {
  return (
    <Card
      onClick={onClick}
      className={
        onClick ? "hover:bg-[#FAF7F2] transition-colors duration-150" : ""
      }
    >
      <div
        className="text-xs uppercase font-medium mb-1"
        style={{ color: C.muted }}
      >
        {label}
      </div>
      <div
        className="text-2xl font-semibold"
        style={{ color: valueColor || C.text }}
      >
        {value}
      </div>
    </Card>
  );
}
