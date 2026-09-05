import { C } from "@/constants/theme";

export function LogoMark() {
  return (
    <div className="flex items-center gap-2">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <rect
          x="2"
          y="2"
          width="12"
          height="12"
          transform="rotate(45 8 8)"
          fill={C.accent}
        />
      </svg>
      <span className="text-white font-semibold text-sm">DealFlow360</span>
    </div>
  );
}

export function LogoMarkLight() {
  return (
    <div className="flex items-center gap-2">
      <svg width="16" height="16" viewBox="0 0 16 16">
        <rect
          x="2"
          y="2"
          width="12"
          height="12"
          transform="rotate(45 8 8)"
          fill={C.accent}
        />
      </svg>
      <span className="font-semibold text-sm" style={{ color: C.text }}>
        DealFlow360
      </span>
    </div>
  );
}
