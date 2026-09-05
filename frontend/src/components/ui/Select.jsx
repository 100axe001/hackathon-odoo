import { useState } from "react";
import { C } from "@/constants/theme";

// Native <select> with the browser's default arrow suppressed, so it matches
// Input and Button instead of rendering as OS chrome in the middle of the page.
export function Select({ value, onChange, options, className = "" }) {
  const [focus, setFocus] = useState(false);

  return (
    <div className={`relative inline-block ${className}`}>
      <select
        value={value}
        onChange={onChange}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        className="w-full appearance-none rounded-md pl-3 pr-8 py-2 text-sm transition-all duration-150 outline-none bg-white cursor-pointer"
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
      <span
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs"
        style={{ color: C.muted }}
      >
        ▾
      </span>
    </div>
  );
}
