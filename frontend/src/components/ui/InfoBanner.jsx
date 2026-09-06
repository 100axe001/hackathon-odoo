import { C } from "@/constants/theme";

export function InfoBanner({ children, tone = "neutral", action }) {
  const toneMap = {
    neutral: { bg: C.neutralBg, text: C.text },
    warn: { bg: C.warnBg, text: C.warnText },
    danger: { bg: C.dangerBg, text: C.dangerText },
    success: { bg: C.successBg, text: C.successText },
  };
  // Fall back rather than crash. An unknown tone used to take the whole screen
  // down with it, which is how the portal's confirmation banner went unnoticed.
  const s = toneMap[tone] ?? toneMap.neutral;
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
