import { C } from "@/constants/theme";

export function Th({ children, right }) {
  return (
    <th
      className={`text-xs uppercase tracking-wide font-medium pb-2 px-3 ${right ? "text-right" : "text-left"}`}
      style={{ color: C.muted }}
    >
      {children}
    </th>
  );
}

export function Td({ children, right, className = "", colSpan }) {
  return (
    <td
      colSpan={colSpan}
      className={`text-sm py-3 px-3 ${right ? "text-right tabular-nums" : ""} ${className}`}
      style={{ color: C.text }}
    >
      {children}
    </td>
  );
}

export function Tr({ children, onClick }) {
  return (
    <tr
      onClick={onClick}
      className={`border-b last:border-0 transition-colors duration-150 ${onClick ? "cursor-pointer" : ""}`}
      style={{ borderColor: C.border }}
      onMouseEnter={(e) =>
        onClick && (e.currentTarget.style.backgroundColor = C.bg)
      }
      onMouseLeave={(e) =>
        onClick && (e.currentTarget.style.backgroundColor = "transparent")
      }
    >
      {children}
    </tr>
  );
}
