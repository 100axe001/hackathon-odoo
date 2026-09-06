// One money format across the app. toLocaleString() alone renders 2751.2 as
// "$2,751.2", which reads as a typo next to every other figure on the page.
export function money(value) {
  return `$${Number(value ?? 0).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
