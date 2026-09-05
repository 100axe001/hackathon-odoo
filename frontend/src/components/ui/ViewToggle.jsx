import { C } from "@/constants/theme";

// Segmented control. The wireframe labels this "Switch to Table View", implying
// the board is the default - PS section 4 B1 lists Pipeline as a top-level view,
// not a nice-to-have.
export function ViewToggle({ value, onChange, options }) {
  return (
    <div
      className="inline-flex rounded-md p-0.5"
      style={{ border: `1px solid ${C.border}`, backgroundColor: C.neutralBg }}
    >
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <button
            key={opt.value}
            onClick={() => onChange(opt.value)}
            className="rounded px-3 py-1 text-sm transition-colors duration-150"
            style={{
              backgroundColor: active ? "#fff" : "transparent",
              color: active ? C.text : C.muted,
              fontWeight: active ? 500 : 400,
              boxShadow: active ? "0 1px 2px rgba(0,0,0,0.06)" : "none",
            }}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
