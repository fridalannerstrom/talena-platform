// Shared #359/#180/#181 regression: near-A4-height covers must be ONE page.
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const core = fs.readFileSync("static/js/talena/pdf-export-core.js", "utf8");
let images = [], extraPages = 0;
function FakePdf() {}
FakePdf.prototype = {
  internal: { pageSize: { getWidth: () => 210, getHeight: () => 297 } },
  setProperties() {},
  addPage() { extraPages += 1; },
  addImage(image, type, x, y, width, height) {
    images.push({ type, x, y, width, height });
  },
  setFont() {}, setFontSize() {}, setTextColor() {}, text() {},
  output() { return new Uint8Array([37,80,68,70]).buffer; },
  save() { throw new Error("No browser save in Blob test"); }
};
const ctx = {
  window: {
    html2canvas: async node => ({
      width: 900, height: node.kind === "cover" ? 1273 : 500,
      toDataURL: () => "data:image/jpeg;base64,dGVzdA=="
    }),
    jspdf: { jsPDF: FakePdf }
  },
  document: {
    fonts: { ready: Promise.resolve() },
    documentElement: { clientWidth: 1200 },
    createElement: tag => ({
      width: 0, height: 0,
      getContext: () => ({ drawImage() {} }),
      toDataURL: () => "data:image/jpeg;base64,dGVzdA=="
    })
  },
  Promise, Blob
};
vm.runInNewContext(core, ctx);
const sections = [
  { node: { kind: "cover", querySelectorAll: () => [] }, cover: true },
  { node: { kind: "body", querySelectorAll: () => [] }, continuous: true }
];
(async () => {
  const blob = await ctx.window.TalenaPdfExport.exportSections(sections, {
    returnBlob: true, filename: "never-saved.pdf"
  });
  assert.equal(blob.type, "application/pdf");
  assert.equal(images.length, 2,
    "A4 cover and short body must produce exactly two pages, not a 1px blank extra page");
  assert.equal(extraPages, 1);
  assert.deepEqual(images[0], {
    type: "JPEG", x: 0, y: 0, width: 210, height: 297
  });
  console.log("Shared PDF A4 cover overflow test: single cover page and one body page OK");
})().catch(err => { console.error(err); process.exitCode = 1; });
