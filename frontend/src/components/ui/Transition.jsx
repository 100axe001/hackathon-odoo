import { useState, useEffect } from "react";

export function Transition({ children, keyProp }) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    setVisible(false);
    const t = setTimeout(() => setVisible(true), 10);
    return () => clearTimeout(t);
  }, [keyProp]);
  return (
    <div
      className="transition-all duration-200 ease-in-out"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(4px)",
      }}
    >
      {children}
    </div>
  );
}
