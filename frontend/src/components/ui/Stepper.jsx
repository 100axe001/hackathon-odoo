import { Fragment } from "react";
import { C } from "@/constants/theme";

export function Stepper({ steps, currentIndex }) {
  return (
    <div className="flex items-center w-full">
      {steps.map((step, i) => {
        const state =
          i < currentIndex ? "done" : i === currentIndex ? "active" : "pending";
        return (
          <Fragment key={step}>
            <div
              className="flex flex-col items-center gap-1.5"
              style={{ minWidth: 90 }}
            >
              <div
                className="rounded-full flex items-center justify-center text-xs font-semibold transition-colors duration-200"
                style={{
                  width: 28,
                  height: 28,
                  backgroundColor:
                    state === "pending"
                      ? "#fff"
                      : state === "active"
                        ? "#fff"
                        : C.accent,
                  border: `2px solid ${state === "pending" ? C.border : C.accent}`,
                  color:
                    state === "done"
                      ? "#fff"
                      : state === "active"
                        ? C.accent
                        : C.muted,
                }}
              >
                {state === "done" ? "✓" : i + 1}
              </div>
              <span
                className="text-xs text-center"
                style={{
                  color: state === "pending" ? C.muted : C.text,
                  fontWeight: state === "active" ? 600 : 400,
                }}
              >
                {step}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div
                className="flex-1 transition-colors duration-200"
                style={{
                  height: 2,
                  backgroundColor: i < currentIndex ? C.accent : C.border,
                  marginBottom: 18,
                }}
              />
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
