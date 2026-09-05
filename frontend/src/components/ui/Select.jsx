import { useState } from "react";
import { C } from "@/constants/theme";

export function Select({ value, onChange, options, className = "" }) {
  const [focus, setFocus] = useState(false);
  return (
    <select
      value={value}
      onChange={onChange}
      onFocus={() => setFocus(true)}
      onBlur={() => setFocus(false)}
      className={`rounded-md px-3 py-2 text-sm transition-all duration-150 outline-none bg-white ${className}`}
      style={{
        border: `1px solid ${focus ? C.accent : C.border}`,
        boxShadow: focus ? `0 0 0 2px ${C.accent}4D` : "none",
        color: C.text,
      }}
    >
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}
