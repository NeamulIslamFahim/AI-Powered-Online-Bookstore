function escapePdfText(value) {
  return String(value ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/\(/g, "\\(")
    .replace(/\)/g, "\\)");
}

function buildPdfTextLines(summary) {
  return [
    "ONLINE BOOKSTORE",
    "POS RECEIPT",
    "",
    `Book: ${summary.book}`,
    `Quantity: ${summary.quantity}`,
    `Customer: ${summary.name}`,
    `Phone: ${summary.phone}`,
    `Address: ${summary.address}`,
    `Total: ${summary.total}`,
    `Generated: ${new Date().toLocaleString()}`,
  ];
}

export function downloadPosPdf(summary) {
  const lines = buildPdfTextLines(summary);
  const content = [
    "BT",
    "/F1 22 Tf",
    "50 780 Td",
    `(${escapePdfText(lines[0])}) Tj`,
    "0 -28 Td",
    "/F1 16 Tf",
    `(${escapePdfText(lines[1])}) Tj`,
    "0 -34 Td",
    "/F1 12 Tf",
    ...lines.slice(2).map((line, index) => `${index === 0 ? "" : "0 -22 Td\n"}(${escapePdfText(line)}) Tj`).join("\n").split("\n"),
    "ET",
  ].join("\n");

  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];

  objects.forEach((object, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });

  const xrefOffset = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  offsets.slice(1).forEach((offset) => {
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  });
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;

  const blob = new Blob([pdf], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `online-bookstore-pos-${Date.now()}.pdf`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
