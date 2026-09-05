import { C } from "@/constants/theme";

export const BADGE_MAP = {
  OK: { text: C.successText, bg: C.successBg },
  Approved: { text: C.successText, bg: C.successBg },
  Paid: { text: C.successText, bg: C.successBg },
  Active: { text: C.successText, bg: C.successBg },
  Confirmed: { text: C.successText, bg: C.successBg },
  LOW: { text: C.successText, bg: C.successBg },
  Auto_approved: { text: C.successText, bg: C.successBg },
  OVER: { text: C.dangerText, bg: C.dangerBg },
  Rejected: { text: C.dangerText, bg: C.dangerBg },
  Unpaid: { text: C.dangerText, bg: C.dangerBg },
  HIGH: { text: C.dangerText, bg: C.dangerBg },
  Pending: { text: C.warnText, bg: C.warnBg },
  "Pending Approval": { text: C.warnText, bg: C.warnBg },
  Paused: { text: C.warnText, bg: C.warnBg },
  Partial: { text: C.warnText, bg: C.warnBg },
  MEDIUM: { text: C.warnText, bg: C.warnBg },
  Draft: { text: C.neutralText, bg: C.neutralBg },
  Negotiation: { text: C.warnText, bg: C.warnBg },
  Cancelled: { text: C.neutralText, bg: C.neutralBg },
  Discontinued: { text: C.neutralText, bg: C.neutralBg },
};

export function Badge({ status, label }) {
  const s = BADGE_MAP[status] || { text: C.neutralText, bg: C.neutralBg };
  return (
    <span
      className="rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors duration-200 inline-block"
      style={{ color: s.text, backgroundColor: s.bg }}
    >
      {label || status}
    </span>
  );
}
