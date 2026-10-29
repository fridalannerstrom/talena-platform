// Ticket #180: execute the real anonymous selection, cover and privacy
// functions rather than relying on static source-text checks alone.
"use strict";
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const source = fs.readFileSync("static/js/talena/team-report-export.js", "utf8");
function loadFunction(name, context) {
  const marker = "    function " + name + "(";
  const start = source.indexOf(marker);
  assert.ok(start >= 0, "Missing function: " + name);
  let depth = 0;
  const bodyStart = source.indexOf("{", start);
  let end = -1;
  depth = 0;
  for (let i = bodyStart; i < source.length; i++) {
    if (source[i] === "{") depth += 1;
    if (source[i] === "}") {
      depth -= 1;
      if (depth === 0) { end = i; break; }
    }
  }
  assert.ok(end > start, "Unterminated function: " + name);
  return vm.runInNewContext("(" + source.slice(start, end + 1) + ")", context, { timeout: 1000 });
}

const selectors = loadFunction("sourceSelectors", {});
assert.deepEqual(Array.from(selectors(true)), [
  "[data-team-report-summary]",
  "[data-team-report-composite]",
  "[data-team-report-maximum-numeric]"
]);
assert.ok(selectors(false).includes("[data-team-report-members]"));
assert.ok(selectors(false).includes("[data-team-report-insights]"));
assert.ok(!selectors(true).some(s => /members|context|insights|profile/i.test(s)),
  "No member, context or AI sections in anonymised PDF");

const profiles = [
  { dataset: { reportName: "Anna Exempel" },
    querySelector: () => ({ dataset: { originalText: "anna@example.test" }, textContent: "******" }) },
  { dataset: { reportName: "Bertil Test" },
    querySelector: () => ({ dataset: {}, textContent: "bertil@example.test" }) }
];
const page = {
  dataset: {
    teamReportBrandPrimary: "#294F72",
    teamReportBrandFocus: "25",
    teamReportBrandCover: "/companies/1/branding/asset/cover/",
    teamReportBrandLogo: "",
    teamReportBrandCompany: "Example Company",
    teamReportCompany: "Example Company",
    teamReportName: "Confidential team"
  },
  querySelectorAll: () => profiles
};
const copy = {
  privacy: "Private identity in anonymous PDF",
  anonymous: "Anonymiserad teamrapport",
  anonymousNotice: "Enbart aggregerade teamresultat ingår i anonymiserat läge.",
  named: "Teamrapport"
};
const guard = loadFunction("assertAnonymousSafe", { page, copy });
function report(text, containsMemberNode = false) {
  return {
    textContent: text,
    querySelector: () => containsMemberNode ? {} : null
  };
}
guard(report("Medlemmar med data: 2. Genomsnitt: 3,8. Aktivator."));
assert.throws(() => guard(report("Anna Exempel, 3.8")), /Private identity/);
assert.throws(() => guard(report("anna@example.test")), /Private identity/);
assert.throws(() => guard(report("Bertil Test")), /Private identity/);
assert.throws(() => guard(report("Aggregated result", true)), /Private identity/);

function element(tag, className, text = "") {
  const obj = {
    tag, className, text,
    children: [],
    style: { setProperty() {}, backgroundPosition: "", backgroundImage: "" },
    classList: { add() {} },
    append(...children) { this.children.push(...children); },
    get textContent() { return [this.text, ...this.children.map(c => c.textContent)].join(" "); },
    set textContent(value) { this.text = value; this.children = []; }
  };
  return obj;
}
const makeCover = loadFunction("makeCover", { page, copy, newElement: element });
const anonymousCover = makeCover(true);
assert.ok(anonymousCover.textContent.includes(copy.anonymous));
assert.ok(!anonymousCover.textContent.includes(page.dataset.teamReportName),
  "Anonymous cover must never print the team name");
assert.ok(!anonymousCover.textContent.includes("Anna Exempel"));
assert.ok(!anonymousCover.textContent.includes("Example Company"),
  "Without a logo, anonymous cover should use neutral Talena wordmark");
const regularCover = makeCover(false);
assert.ok(regularCover.textContent.includes(page.dataset.teamReportName));
assert.ok(regularCover.textContent.includes("Example Company"));

// The file name and PDF metadata are assembled inside the actual click
// callback. These literal branches are additional guards against accidental
// identifying names being passed to the PDF save function.
assert.ok(source.includes('anonymous ? "anonym-teamrapport.pdf" : "teamrapport.pdf"'));
assert.ok(source.includes('title = anonymous ? copy.anonymous : copy.named'));
assert.ok(source.includes('subject: anonymous ? "Aggregated team scores"'));

console.log("Team report anonymization runtime: aggregate-only, identity guard, cover, metadata OK");
