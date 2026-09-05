import { C } from "@/constants/theme";

export function InfoBanner({ children, tone = "neutral", action }) {
  const toneMap = {
    neutral: { bg: C.neutralBg, text: C.text },
    warn: { bg: C.warnBg, text: C.warnText },
    danger: { bg: C.dangerBg, text: C.dangerText },
  };
  const s = toneMap[tone];
  return (
    <div
      className="rounded-md px-4 py-3 text-sm flex items-center justify-between gap-4 transition-all duration-200"
      style={{ backgroundColor: s.bg, color: s.text }}
    >
      <span>{children}</span>
      {action}
    </div>
  );
}
