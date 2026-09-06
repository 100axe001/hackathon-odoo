// Report export. Both paths produce a real file rather than a toast: the CSV is
// built and downloaded in the browser, and PDF goes through the print dialog,
// which is where "save as PDF" actually lives on every platform.

// Excel opens CSV natively, so this is the honest version of "Export XLS"
// without shipping a spreadsheet library for one button.
function toCsv(rows) {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const text = cell == null ? "" : String(cell);
          // Quote anything that would otherwise break the column structure.
          return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
        })
        .join(","),
    )
    .join("\n");
}

export function downloadCsv(filename, rows) {
  // The BOM is what makes Excel read UTF-8 rather than mangling it.
  const blob = new Blob(["﻿" + toCsv(rows)], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function printReport() {
  window.print();
}
