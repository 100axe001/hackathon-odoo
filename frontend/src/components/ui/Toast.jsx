import { useEffect } from "react";
import { C } from "@/constants/theme";

// Long messages need longer on screen. A fixed three seconds was fine for
// "Saved" and far too short for a sentence explaining which line broke which
// ceiling and who the quotation went to.
function readingTime(message) {
  return Math.min(12000, Math.max(3000, 1200 + message.length * 45));
}

export function Toast({ message, onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const t = setTimeout(onClose, readingTime(message));
    return () => clearTimeout(t);
  }, [message]);

  if (!message) return null;

  return (
    <div
      className="fixed bottom-6 right-6 rounded-md px-4 py-3 text-sm font-medium shadow-sm transition-all duration-200 z-50 cursor-pointer"
      style={{ backgroundColor: C.text, color: "#fff", maxWidth: 460 }}
      onClick={onClose}
      title="Dismiss"
    >
      {message}
    </div>
  );
}
