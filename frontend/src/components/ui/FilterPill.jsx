import { C } from "@/constants/theme";

export function FilterPill({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className="rounded-full px-3 py-1.5 text-sm transition-colors duration-150"
      style={
        active
          ? { backgroundColor: "#FDF0E7", color: C.accent, fontWeight: 500 }
          : { color: C.muted }
      }
      onMouseEnter={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = C.bg;
      }}
      onMouseLeave={(e) => {
        if (!active) e.currentTarget.style.backgroundColor = "transparent";
      }}
    >
      {children}
    </button>
  );
}
