import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { C } from "@/constants/theme";

// Kanban pipeline. One column per stage, so a deal's position in the funnel is
// the first thing you read - PS section 4 B2.
//
// Cards are draggable between columns: dropping a card on a stage is how a rep
// moves the deal, which is the whole point of a board over a table.
export function QuotationBoard({ stages, quotations, onOpen, onMove }) {
  const [dragId, setDragId] = useState(null);
  const [overStage, setOverStage] = useState(null);

  const handleDrop = (stage) => {
    if (dragId && onMove) onMove(dragId, stage);
    setDragId(null);
    setOverStage(null);
  };

  return (
    <div
      className="grid gap-3 items-stretch min-h-[calc(100vh-260px)]"
      style={{
        gridTemplateColumns: `repeat(${stages.length}, minmax(0, 1fr))`,
      }}
    >
      {stages.map((stage) => {
        const cards = quotations.filter((q) => q.status === stage);
        const total = cards.reduce((sum, q) => sum + (q.amount || 0), 0);
        const isOver = overStage === stage;

        return (
          <section
            key={stage}
            onDragOver={(e) => {
              e.preventDefault();
              setOverStage(stage);
            }}
            onDragLeave={() => setOverStage((s) => (s === stage ? null : s))}
            onDrop={() => handleDrop(stage)}
            className="flex flex-col rounded-lg transition-colors duration-150"
            style={{
              backgroundColor: isOver ? "#FDF0E7" : C.neutralBg,
              outline: isOver
                ? `2px dashed ${C.accent}`
                : "2px dashed transparent",
            }}
          >
            <header
              className="flex items-baseline justify-between px-3 pt-3 pb-2"
              style={{ borderBottom: `1px solid ${C.border}` }}
            >
              <span className="text-sm font-medium" style={{ color: C.text }}>
                {stage}
              </span>
              <span
                className="text-xs tabular-nums rounded-full px-1.5"
                style={{ color: C.muted, backgroundColor: "#fff" }}
              >
                {cards.length}
              </span>
            </header>

            <div className="flex flex-col gap-2 p-2 flex-1">
              {cards.map((q) => (
                <article
                  key={q.id}
                  draggable
                  onDragStart={() => setDragId(q.id)}
                  onDragEnd={() => setDragId(null)}
                  onClick={() => onOpen(q.id)}
                  className="bg-white rounded-md p-3 cursor-grab active:cursor-grabbing transition-all duration-150 hover:shadow-md"
                  style={{
                    border: `1px solid ${C.border}`,
                    opacity: dragId === q.id ? 0.4 : 1,
                  }}
                >
                  <div
                    className="text-sm font-medium mb-1"
                    style={{ color: C.text }}
                  >
                    {q.customer_name}
                  </div>
                  <div
                    className="text-base font-semibold tabular-nums mb-2"
                    style={{ color: C.text }}
                  >
                    ${(q.amount || 0).toLocaleString()}
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge status={q.status} />
                    <span className="text-xs" style={{ color: C.muted }}>
                      {q.id.toUpperCase()}
                    </span>
                  </div>
                </article>
              ))}

              {cards.length === 0 && (
                <div
                  className="text-xs px-2 py-10 text-center rounded-md"
                  style={{ color: C.muted, border: `1px dashed ${C.border}` }}
                >
                  Drop a deal here
                </div>
              )}
            </div>

            <footer
              className="px-3 py-2 text-xs tabular-nums"
              style={{ color: C.muted, borderTop: `1px solid ${C.border}` }}
            >
              ${total.toLocaleString()}
            </footer>
          </section>
        );
      })}
    </div>
  );
}
