"use strict";

// Regression for #436: AI Markdown may separate ordered entries with blank
// lines and use "1." repeatedly. One semantic <ol> is needed for 1,2,3...
const assert = require("node:assert/strict");
const fs = require("node:fs");

const src = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");
const begin = src.indexOf("  const appendInlineMarkdown = (parent, text) => {");
const end = src.indexOf("  const sourceContent = (panel, key) => {", begin);
assert.ok(begin >= 0 && end > begin, "Markdown renderer not found");

function element(type) {
  return {
    type, children: [], className: "",
    appendChild(child) { this.children.push(child); },
    replaceChildren(fragment) { this.children = fragment.children || [fragment]; },
  };
}
const doc = {
  createElement: element,
  createDocumentFragment: () => element("fragment"),
  createTextNode: (text) => ({ type: "text", text }),
};
const render = new Function(
  "document", src.slice(begin, end) + "\nreturn renderGeneratedMarkdown;"
)(doc);

function renderText(text) {
  const container = {
    textContent: text,
    dataset: {},
    children: [],
    classList: { add() {} },
    replaceChildren(fragment) { this.children = fragment.children; },
  };
  render(container);
  return container.children;
}
const blocks = renderText([
  "Tips för trivsel",
  "",
  "1. **Strukturerade arbetsuppgifter:** Tydliga mål.",
  "",
  "1. **Lugn arbetsmiljö:** Färre störningar.",
  "",
  "1. **Återkoppling:** Regelbundna avstämningar.",
  "",
  "Sammanfattning efter listan.",
].join("\n"));

const lists = blocks.filter(node => node.type === "ol");
assert.equal(lists.length, 1, "Blank lines must not split the numbered list");
assert.equal(lists[0].children.length, 3,
  "All three entries must be in one sequentially numbered list");
assert.ok(lists[0].children.every(node => node.type === "li"));
assert.ok(lists[0].children[0].children.some(node => node.type === "strong"),
  "Bold lead-in must still be rendered");
assert.equal(blocks.at(-1).type, "p", "Following paragraph must not join the list");

const separated = renderText([
  "1. Första", "2. Andra", "", "Fortsättning.", "", "1. Ny lista",
].join("\n"));
assert.equal(separated.filter(node => node.type === "ol").length, 2,
  "Paragraph boundaries must still separate distinct lists");

assert.ok(src.includes("color: #3d3834; font-size: .85rem; line-height: 1.72;"),
  "Wellbeing body must be darker than the muted helper text");
assert.ok(src.includes("ol.after-interview-rich-text__list"),
  "Ordered-list markers must remain decimal");

console.log("Wellbeing Markdown numbering and darker text regression passed.");
