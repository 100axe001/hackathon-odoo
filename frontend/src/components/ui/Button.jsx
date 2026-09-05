import { useState } from "react";
import { C } from "@/constants/theme";

export function Button({
  children,
  variant = "primary",
  onClick,
  className = "",
  type = "button",
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
  };
  return (
    <button
      type={type}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      className={`${base} ${className}`}
      style={hover ? hoverStyles[variant] : styles[variant]}
    >
      {children}
    </button>
  );
}
