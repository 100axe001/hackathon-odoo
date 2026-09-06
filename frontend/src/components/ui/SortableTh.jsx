import { C } from "@/constants/theme";

// A column header that sorts. The arrow only appears on the active column, so
// the table still reads as a table rather than a row of controls.
export function SortableTh({ column, sort, onSort, right = false, children }) {
  const active = sort.key === column;
  return (
    <th
      onClick={() => onSort(column)}
      className={`text-xs font-medium uppercase tracking-wide pb-2 select-none cursor-pointer ${
        right ? "text-right" : "text-left"
      }`}
      style={{
        color: active ? C.text : C.muted,
        borderBottom: `1px solid ${C.border}`,
      }}
      title={`Sort by ${String(children)}`}
    >
      {children}
      <span
        className="ml-1"
        style={{ color: active ? C.accent : "transparent" }}
      >
        {active && sort.direction === "desc" ? "▾" : "▴"}
      </span>
    </th>
  );
}

// Sorts a copy, comparing numbers as numbers and everything else as text.
export function sortRows(rows, sort, accessor) {
  if (!sort.key) return rows;
  const factor = sort.direction === "desc" ? -1 : 1;
  return [...rows].sort((a, b) => {
    const left = accessor(a, sort.key);
    const right = accessor(b, sort.key);
    if (typeof left === "number" && typeof right === "number") {
      return (left - right) * factor;
    }
    return String(left ?? "").localeCompare(String(right ?? "")) * factor;
  });
}

// Click the active column to flip direction, a new one to sort by it ascending.
export function nextSort(current, key) {
  if (current.key !== key) return { key, direction: "asc" };
  return { key, direction: current.direction === "asc" ? "desc" : "asc" };
}
