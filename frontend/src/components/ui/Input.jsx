import { useState } from "react";
import { C } from "@/constants/theme";

export function Input({
  value,
  onChange,
  type = "text",
  placeholder,
  className = "",
}) {
  const [focus, setFocus] = useState(false);
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      className={`rounded-md px-3 py-2 text-sm transition-all duration-150 outline-none w-full ${className}`}
      style={{
        border: `1px solid ${focus ? C.accent : C.border}`,
        boxShadow: focus ? `0 0 0 2px ${C.accent}4D` : "none",
      }}
    />
  );
}
