import { useState } from "react";
import { C } from "@/constants/theme";

export function Input({
  value,
  onChange,
  type = "text",
  placeholder,
  className = "",
  readOnly = false,
}) {
  const [focus, setFocus] = useState(false);
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      readOnly={readOnly}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      className={`rounded-md px-3 py-2 text-sm transition-all duration-150 outline-none w-full ${className}`}
      style={{
        border: `1px solid ${focus && !readOnly ? C.accent : C.border}`,
        boxShadow: focus && !readOnly ? `0 0 0 2px ${C.accent}4D` : "none",
        backgroundColor: readOnly ? C.bg : undefined,
        color: readOnly ? C.muted : undefined,
        cursor: readOnly ? "default" : undefined,
      }}
    />
  );
}
