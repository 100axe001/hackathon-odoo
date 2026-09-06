import { useState } from "react";
import { C } from "@/constants/theme";

export function Button({
  children,
  variant = "primary",
  onClick,
  className = "",
  type = "button",
  disabled = false,
}) {
  const base =
    "rounded-md px-4 py-2 text-sm font-medium transition-colors duration-150";
  const styles = {
    primary: { backgroundColor: C.accent, color: "#fff" },
    secondary: {
      backgroundColor: "#fff",
      color: C.text,
      border: `1px solid ${C.border}`,
    },
    destructive: {
      backgroundColor: "#fff",
      color: C.dangerText,
      border: `1px solid ${C.dangerText}`,
    },
    // The wireframe colour-codes approval decisions: green approve, amber
    // return, red reject. The colour is the fastest signal on that screen.
    success: { backgroundColor: C.successText, color: "#fff" },
    warning: { backgroundColor: C.warnText, color: "#fff" },
  };
  const [hover, setHover] = useState(false);
  const hoverStyles = {
    primary: { backgroundColor: C.accentHover, color: "#fff" },
    secondary: {
      backgroundColor: C.bg,
      color: C.text,
      border: `1px solid ${C.border}`,
    },
    destructive: {
      backgroundColor: C.dangerText,
      color: "#fff",
      border: `1px solid ${C.dangerText}`,
    },
    success: { backgroundColor: C.successText, color: "#fff", opacity: 0.9 },
    warning: { backgroundColor: C.warnText, color: "#fff", opacity: 0.9 },
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className={`${base} ${className}`}
      style={{
        ...(hover && !disabled ? hoverStyles[variant] : styles[variant]),
        ...(disabled
          ? { opacity: 0.45, cursor: "not-allowed" }
          : { cursor: "pointer" }),
      }}
    >
      {children}
    </button>
  );
}
