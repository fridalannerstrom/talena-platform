"use strict";

// Layout regression: the three Motivation factors must remain full-width
// in the manager-report PDF and page breaks should respect whole cards.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const manager = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const engine = fs.readFileSync("static/js/talena/pdf-export-core.js", "utf8");

assert.ok(
  manager.includes('printableReport.classList.add("after-interview-manager-report__pdf-layout")'),
  "Manager PDF must opt into its own print layout."
);
assert.ok(
  manager.includes('data-manager-report-pdf-layout", "a4-portrait"'),
  "PDF pagination must detect the manager-report print layout."
);
assert.ok(
  /__PANEL__ \.after-interview-manager-report__pdf-layout\s+\.after-interview-manager-report__motivation-grid\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\) !important/.test(manager),
  "Motivation factors must stack in A4 portrait, never two side-by-side."
);
assert.ok(
  /__PANEL__ \.after-interview-manager-report__pdf-layout\s+\.after-interview-manager-report__motivator\s*\{\s*grid-template-columns:\s*minmax\(0, 1fr\) !important/.test(manager),
  "Each Motivation factor must have a full-width introductory row."
);
assert.ok(
  /__PANEL__ \.after-interview-manager-report__pdf-layout\s+\.after-interview-manager-report__motivator-practical-grid\s*\{\s*grid-template-columns:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\) !important/.test(manager),
  "Do/Avoid tips must occupy two wide, readable columns."
);
const printableGrids = manager.slice(
  manager.indexOf("const printableReport = managerReportCard.cloneNode(true);"),
  manager.indexOf("exportRoot.appendChild(printableReport);")
);
assert.ok(!printableGrids.includes('".after-interview-manager-report__motivation-grid"'),
  "Never force two Motivation columns when exporting the PDF."
);

for (const selector of [
  "__skills-title", "__motivation-title", "__personality-title", "__wellbeing-title",
  "__skill-title", "__personality-theme-title", "__personality-part-text",
  "__interview-comments-text", "__section-intro",
]) {
  assert.ok(manager.includes("after-interview-manager-report" + selector),
    "Missing report hierarchy or text style: " + selector);
}
assert.ok(engine.includes("getManagerReportPageGuides(opts.node, source, maxHeight)"));
assert.ok(engine.includes('".after-interview-manager-report__motivator, "'));
assert.ok(engine.includes('".after-interview-manager-report__interview-comments, "'));
assert.ok(engine.includes("end - start <= maxHeight * maxPageFraction"),
  "Content larger than one page must be allowed to split rather than hang.");

// Exercise the real shared PDF page slicer without DOM or PDF libraries.
const context = {
  window: {}, document: {},
};
vm.runInNewContext(engine, context);
const { calculatePageSlices } = context.window.TalenaPdfExport;
const protectedRanges = [
  { start: 830, end: 1170 },
  { start: 1770, end: 2050 },
];
const slices = calculatePageSlices(
  2670, 1000, [360, 590, 830, 1170, 1500, 1770, 2050, 2370],
  protectedRanges
);
let cursor = 0;
for (const slice of slices) {
  assert.equal(slice.start, cursor);
  assert.ok(slice.height > 0);
  cursor += slice.height;
  if (cursor === 2670) continue;
  for (const range of protectedRanges) {
    assert.ok(cursor <= range.start || cursor >= range.end,
      "PDF page cut the middle of a protected Motivation card.");
  }
}
assert.equal(cursor, 2670);

console.log("Chefsrapport A4 portrait Motivation and heading hierarchy layout contract OK");
