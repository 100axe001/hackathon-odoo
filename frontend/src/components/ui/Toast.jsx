import { useEffect } from "react";
import { C } from "@/constants/theme";

export function Toast({ message, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3000);
    return () => clearTimeout(t);
  }, [message]);
  if (!message) return null;
  return (
    <div
      className="fixed bottom-6 right-6 rounded-md px-4 py-3 text-sm font-medium shadow-sm transition-all duration-200 z-50"
      style={{ backgroundColor: C.text, color: "#fff" }}
    >
      {message}
    </div>
  );
}
