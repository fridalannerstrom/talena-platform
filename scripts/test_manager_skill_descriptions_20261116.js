"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");

const source = fs.readFileSync("static/js/talena/after-interview-tabs.js", "utf8");

const sv = {
  numerical: {
    title: "Numerisk förmåga",
    intro: "Avser att mäta en persons förmåga att hantera och använda numerisk information",
    outro: "bearbetar siffror och numerisk data.",
  },
  logical: {
    title: "Logisk förmåga",
    intro: "Avser att mäta en persons förmåga att tänka logiskt, analytiskt",
    outro: "inte finns någon uppenbar logik.",
  },
  verbal: {
    title: "Verbal förmåga",
    intro: "Avser att mäta en persons förmåga att analysera och tolka skriftlig information",
    outro: "förstå och bearbeta skriftlig information.",
  },
};

for (const item of Object.values(sv)) {
  assert.ok(source.includes(item.title), "Missing Swedish manager skill title: " + item.title);
  assert.ok(source.includes(item.intro), "Missing Swedish manager skill description: " + item.title);
  assert.ok(source.includes(item.outro), "Truncated Swedish description: " + item.title);
}
for (const title of ["Numerical ability", "Logical ability", "Verbal ability"]) {
  assert.ok(source.includes(title), "Missing English skill title: " + title);
}
assert.ok(source.includes("managerSkillDescriptions: {"), "Descriptions must be non-AI copy");
assert.ok(
  source.includes('skillDescription.textContent = copy().managerSkillDescriptions[key] || "";'),
  "Render the correct copy from the same result key as the heading",
);
const start = source.indexOf('const skillDescription = document.createElement("p");');
const append = source.indexOf("skill.append(heading, skillDescription);", start);
const cards = source.indexOf('const levels = document.createElement("div");', append);
assert.ok(start >= 0 && append > start && cards > append,
  "Description must appear between the skill heading and four band cards",
);
assert.ok(source.includes("after-interview-manager-report__skill-description"),
  "Description needs dedicated typography for both screen and PDF",
);
assert.ok(source.includes("const printableReport = managerReportCard.cloneNode(true);"),
  "PDF must clone the complete manager report including skill descriptions",
);
assert.ok(!source.includes('".after-interview-manager-report__skill-description,"'),
  "The new description must not be filtered out of PDF clone");
assert.ok(source.includes('if (percentile === undefined) return;'),
  "No test result must mean no candidate-specific description/cards");
assert.ok(source.includes('const selectedBandIndex = percentile <= 20 ? 0'),
  "Do not change the existing skill band boundaries");
console.log("Manager-report skill titles, descriptions, order and PDF contract: OK");
