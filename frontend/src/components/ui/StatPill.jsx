import { C } from "@/constants/theme";

export function StatPill({ label, count, tone }) {
  const toneMap = {
    success: { text: C.successText, bg: C.successBg },
    warn: { text: C.warnText, bg: C.warnBg },
    danger: { text: C.dangerText, bg: C.dangerBg },
    neutral: { text: C.neutralText, bg: C.neutralBg },
  };
  const s = toneMap[tone] || toneMap.neutral;
  return (
    <div
      className="rounded-full px-4 py-2 text-sm font-medium inline-flex items-center gap-1.5"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      <span className="font-semibold">{count}</span> {label}
    </div>
  );
}
