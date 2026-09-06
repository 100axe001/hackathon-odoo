import { useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { C } from "@/constants/theme";
import { loadJourney } from "@/api/api-functions/quotations";

// One strip, shown on every screen that touches a deal, so the workspace reads
// as a single flow rather than five tabs that each know only their own step.
// The next action is deliberately singular: offering three choices puts the
// guesswork straight back.
const TONE = {
  done: { dot: C.successText, text: C.text },
  current: { dot: C.accent, text: C.text },
  todo: { dot: C.border, text: C.muted },
  skipped: { dot: C.border, text: C.muted },
};

export function DealJourney({ quotationId, onRefresh }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [journey, setJourney] = useState(null);

  useEffect(() => {
    let live = true;
    loadJourney(quotationId)
      .then((data) => live && setJourney(data))
      .catch(() => live && setJourney(null));
    return () => {
      live = false;
    };
  }, [quotationId, onRefresh]);

  if (!journey) return null;

  const next = journey.next_action;
  // The next step is often on this very screen. Offering a button that
  // navigates to where you already are is worse than saying nothing - it
  // duplicates the real control and reads as broken when it does nothing.
  const here = next?.path === pathname;

  return (
    <div
      className="rounded-lg px-5 py-4 mb-6"
      style={{ backgroundColor: "#fff", border: `1px solid ${C.border}` }}
    >
      <div className="flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-6 flex-wrap">
          {journey.stages.map((stage, i) => {
            const tone = TONE[stage.state] ?? TONE.todo;
            return (
              <div key={stage.key} className="flex items-center gap-2">
                <span
                  className="rounded-full shrink-0"
                  style={{
                    width: 9,
                    height: 9,
                    backgroundColor: tone.dot,
                    outline:
                      stage.state === "current"
                        ? `3px solid ${C.accent}33`
                        : "none",
                  }}
                />
                <span className="leading-tight">
                  <span
                    className="block text-sm"
                    style={{
                      color: tone.text,
                      fontWeight: stage.state === "current" ? 600 : 400,
                    }}
                  >
                    {stage.label}
                  </span>
                  <span className="block text-xs" style={{ color: C.muted }}>
                    {stage.detail}
                  </span>
                </span>
                {i < journey.stages.length - 1 && (
                  <span className="ml-4" style={{ color: C.border }}>
                    ›
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {next && (
          <div className="text-right">
            {here ? (
              <div className="text-sm" style={{ color: C.text }}>
                Next: <span className="font-medium">{next.label}</span>
                <div className="text-xs" style={{ color: C.muted }}>
                  on this screen
                </div>
              </div>
            ) : (
              <>
                <Button variant="primary" onClick={() => navigate(next.path)}>
                  {next.label}
                </Button>
                {/* Naming the role stops a rep opening an approval screen they
                    cannot act on and reading the refusal as a bug. */}
                <div className="text-xs mt-1" style={{ color: C.muted }}>
                  {next.role}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
