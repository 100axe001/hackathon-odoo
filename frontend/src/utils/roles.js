// SALES_MANAGER reads as a database value, not as a person's job. Three screens
// now spell a role out for a person to read, so the transform lives in one place.
export function roleLabel(role) {
  return String(role || "")
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
