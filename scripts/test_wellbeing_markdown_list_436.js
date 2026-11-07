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
  "document", "copy", src.slice(begin, end) + "\nreturn renderGeneratedMarkdown;"
)(doc, () => ({ managerPersonalityAdviceTitle: "Tips för trivsel" }));

function renderText(text, options = {}) {
  const names = new Set(options.classNames || []);
  const container = {
    textContent: text,
    dataset: options.key ? { managerReportEditKey: options.key } : {},
    children: [],
    classList: { add(value) { names.add(value); }, contains(value) { return names.has(value); } },
    closest(selector) {
      return options.sourceWellbeing && selector.includes("wellbeing_tips") ? {} : null;
    },
    replaceChildren(fragment) { this.children = fragment.children; },
  };
  render(container);
  return { children: container.children, originalSource: container.dataset.markdownSource };
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
].join("\n")).children;

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
].join("\n")).children;
assert.equal(separated.filter(node => node.type === "ol").length, 2,
  "Paragraph boundaries must still separate distinct lists");

// A generated heading may repeat the section title. It is skipped only
// in the wellbeing block and only if it is the very first content line.
// The original source remains available to the edit dialog and PDF.
const original = "## Tips för trivsel\\n\\nFörslag till arbetssätt.\\n\\n1. Först\\n2. Sedan";
const wellbeing = renderText(original, { sourceWellbeing: true });
assert.equal(wellbeing.children.length, 2, "Duplicate heading should not be shown");
assert.equal(wellbeing.children[0].type, "p");
assert.equal(wellbeing.children[1].type, "ol");
assert.equal(wellbeing.originalSource, original, "Never strip text from stored AI content");
const edited = renderText("**Tips för trivsel**\\n\\nEtt konkret råd.", { key: "wellbeing_tips" });
assert.equal(edited.children.length, 1, "Manually edited heading should be deduplicated");
assert.equal(edited.children[0].type, "p");
const english = renderText("# Wellbeing tips\\n\\nOne recommendation.", { key: "wellbeing_tips" });
assert.equal(english.children.length, 1, "English report heading should be deduplicated");
const other = renderText("## Tips för trivsel\\n\\nAndra rubriker.", {});
assert.equal(other.children[0].type, "h3", "Other AI blocks must keep their headings");
const custom = renderText("## Viktiga rekommendationer\\n\\nText.", { key: "wellbeing_tips" });
assert.equal(custom.children[0].type, "h3", "Distinct wellbeing subheadings must remain");

assert.ok(src.includes("color: #3d3834; font-size: .85rem; line-height: 1.72;"),
  "Wellbeing body must be darker than the muted helper text");
assert.ok(src.includes("ol.after-interview-rich-text__list"),
  "Ordered-list markers must remain decimal");

console.log("Wellbeing Markdown, heading deduplication and darker text regression passed.");
