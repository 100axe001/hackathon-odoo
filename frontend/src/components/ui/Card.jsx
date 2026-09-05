import { C } from "@/constants/theme";

export function Card({ children, className = "", onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-lg p-4 ${onClick ? "cursor-pointer" : ""} ${className}`}
      style={{ border: `1px solid ${C.border}` }}
    >
      {children}
    </div>
  );
}
