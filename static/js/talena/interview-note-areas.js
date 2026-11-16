/* Presentation-only structure for interview notes.
 *
 * The existing interview_notes field remains the sole persisted source of
 * truth. AI prompts, model fields, report generation and saved-answer
 * provenance are deliberately unchanged.
 */
(function (scope) {
  "use strict";

  const ORDER = ["personality", "motivation", "skills"];
  const HEADINGS = Object.freeze({
    personality: "Personlighet",
    motivation: "Motivation",
    skills: "Färdighet",
  });
  const HEADER_PATTERN = /^## (Personlighet|Motivation|Färdighet)[ \t]*$/gm;
  const KEY_BY_HEADING = Object.freeze(
    Object.fromEntries(ORDER.map(key => [HEADINGS[key], key]))
  );

  function parse(value) {
    const text = String(value || "");
    const sections = { personality: "", motivation: "", skills: "" };
    if (!text.trim()) {
      return { sections, legacy: false };
    }

    // Only treat our exact generated headings as structured storage. Do not
    // guess the topics of older unstructured notes, which may mix all areas.
    const headings = Array.from(text.matchAll(HEADER_PATTERN));
    if (!headings.length || text.slice(0, headings[0].index).trim()) {
      return {
        sections: { ...sections, personality: text },
        legacy: true,
      };
    }

    // If a heading is repeated, preserve both fragments rather than dropping
    // one. This is also safe if pasted notes contain a matching heading.
    headings.forEach((match, i) => {
      const key = KEY_BY_HEADING[match[1]];
      const start = match.index + match[0].length;
      const end = headings[i + 1]?.index ?? text.length;
      const fragment = text.slice(start, end).trim();
      if (!fragment) return;
      sections[key] = [sections[key], fragment].filter(Boolean).join("\n\n");
    });
    return { sections, legacy: false };
  }

  function serialize(sections) {
    return ORDER.map(key => {
      const value = String(sections?.[key] || "").trim();
      return value ? "## " + HEADINGS[key] + "\n" + value : "";
    }).filter(Boolean).join("\n\n");
  }

  function initialise(root) {
    if (!root?.querySelector) return;
    const sectionRoot = root.querySelector("[data-interview-notes-areas]");
    const combined = root.querySelector("[data-interview-notes-input]");
    if (!sectionRoot || !combined || sectionRoot.dataset.notesAreasBound === "true") {
      return;
    }
    const fields = Object.fromEntries(ORDER.map(key => [
      key, sectionRoot.querySelector('[data-interview-notes-area="' + key + '"]'),
    ]));
    if (ORDER.some(key => !fields[key])) return;
    sectionRoot.dataset.notesAreasBound = "true";

    const parsed = parse(combined.value);
    ORDER.forEach(key => {
      fields[key].value = parsed.sections[key];
    });
    const legacyHelp = sectionRoot.querySelector("[data-interview-notes-legacy-help]");
    if (legacyHelp) legacyHelp.hidden = !parsed.legacy;

    // One native input event keeps all pre-existing save handlers, evidence
    // availability checks and stale-report warnings in sync. No second API,
    // no separate shadow storage, and no alterations to the AI input path.
    function sync() {
      const updated = serialize(Object.fromEntries(
        ORDER.map(key => [key, fields[key].value])
      ));
      if (combined.value === updated) return;
      combined.value = updated;
      combined.dispatchEvent(new Event("input", { bubbles: true }));
    }

    ORDER.forEach(key => fields[key].addEventListener("input", sync));
  }

  scope.TalenaInterviewNoteAreas = Object.freeze({
    initialise, parse, serialize,
  });
})(typeof window !== "undefined" ? window : globalThis);
