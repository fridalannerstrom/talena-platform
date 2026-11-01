(function () {
  "use strict";

  // Explicit data provenance: each output selector refers to an AI response
  // field or an AI-generated question, never a heading keyword or a chart.
  // Candidate reports, static test interpretations and interviewer notes have
  // no corresponding rules, so they cannot be marked by this code.
  const RULES = [
    ["#purposeFitCard", "#purposeFitTitle", "#purposeFitSummary"],
    ["#purposeFitResult", ".purpose-fit-section:first-child .purpose-fit-section-title", "#purposeFitSummary"],
    [".personality-overview-summary", ".personality-overview-summary__title", "[data-personality-area-summary]"],
    [".purpose-fit-list-card--positive", ".purpose-fit-section-title", "#purposeFitAlignment li"],
    [".purpose-fit-list-card--verify", ".purpose-fit-section-title", "#purposeFitVerify li"],
    ["[data-personality-ai-root]", "[data-personality-ai-title]", "[data-personality-ai-interpretation]"],
    ["[data-personality-ai-root] .personality-interpretation__overall", ".purpose-fit-section-title", "[data-personality-ai-interpretation]"],
    ["[data-motivation-ai-root]", "h2.insight-summary-title", "[data-motivation-ai-interpretation]"],
    ["[data-cognitive-interpretation-root]", "h2.insight-summary-title", "[data-cognitive-ai-interpretation]"],
    ["[data-personality-questions-root]", ".personality-questions-header h2", "[data-personality-questions-list] .personality-question-card"],
    ["[data-motivation-questions-root]", ".personality-questions-header h2", "[data-motivation-questions-list] .personality-question-card"],
    ["[data-cognitive-questions-root]", ".personality-questions-header h2", "[data-cognitive-questions-list] .personality-question-card"],
    ["[data-combined-questions-root]", ".personality-questions-header h2", ".combined-question-sections .personality-question-card__text"],
    ["#candidate-insights-panel-prepare-interview > .final-output-card", "h2.insight-summary-title", "[data-pre-interview-overall-synthesis]"],
    ["[data-post-interview-section]", "h3.insight-summary-title", "[data-post-interview-content] .purpose-fit-summary"],
    [".after-interview-tab-card", ".after-interview-tab-card__title", "[data-after-interview-block-content]"],
    ["[data-overall-picture-structured-card]", ".after-interview-tab-card__title", "[data-after-interview-block-content]"]
  ];
  const BADGE_CLASS = "talena-ai-generated-badge";
  const ROW_CLASS = "talena-ai-title-row";

  function isSwedish() {
    return (document.documentElement.lang || "").toLowerCase().startsWith("sv");
  }

  function label(assisted) {
    return assisted
      ? (isSwedish() ? "AI-assisterat" : "AI-assisted")
      : (isSwedish() ? "AI-genererat" : "AI-generated");
  }

  function setLabel(badge, assisted) {
    const value = label(assisted);
    const nextText = "✦ " + value;
    if (badge.textContent !== nextText) badge.textContent = nextText;
    if (badge.getAttribute("aria-label") !== value) badge.setAttribute("aria-label", value);
    const lang = isSwedish() ? "sv" : "en";
    if (badge.getAttribute("lang") !== lang) badge.setAttribute("lang", lang);
  }

  function findRuleOutput(root, selector) {
    try {
      return root.querySelector(selector);
    } catch (_error) {
      return null;
    }
  }

  function hasGeneratedText(element) {
    if (!element || element.closest("[hidden], .d-none")) return false;
    if (element.classList?.contains("after-interview-tab-empty")) return false;
    return Boolean((element.textContent || "").trim());
  }

  function setBadge(heading, visible, assisted) {
    if (!heading) return;
    let row = heading.parentElement;
    if (!row || !row.classList.contains(ROW_CLASS)) {
      if (!visible) return;
      row = document.createElement("div");
      row.className = ROW_CLASS;
      heading.parentNode.insertBefore(row, heading);
      row.appendChild(heading);
    }
    let badge = row.querySelector(":scope > ." + BADGE_CLASS);
    if (!badge && visible) {
      badge = document.createElement("span");
      badge.className = BADGE_CLASS;
      row.appendChild(badge);
    }
    if (badge) {
      if (badge.hidden !== !visible) badge.hidden = !visible;
      if (visible) setLabel(badge, assisted);
    }
  }

  function removeLegacyKickers(root) {
    // Only old AI-specific labels immediately beside an AI heading, not
    // category labels on unrelated content such as test-result cards.
    root.querySelectorAll(".insight-summary-kicker").forEach((kicker) => {
      if (/AI-generated insight|AI-supported questions|AI-genererad insikt|AI-frågor/i.test(kicker.textContent || "")) {
        if (!kicker.hidden) kicker.hidden = true;
        if (kicker.getAttribute("aria-hidden") !== "true") kicker.setAttribute("aria-hidden", "true");
      }
    });
  }

  function markRule(rootSelector, headingSelector, outputSelector) {
    document.querySelectorAll(
      '[data-candidate-insights-workspace] ' + rootSelector
    ).forEach((root) => {
      const heading = root.querySelector(headingSelector);
      const output = findRuleOutput(root, outputSelector);
      setBadge(heading, hasGeneratedText(output), false);
    });
  }

  function markManagerReportBlocks() {
    // These text fields are explicitly tracked by the editable AI block
    // controller. Manual edits retain the AI-assisted provenance.
    document.querySelectorAll(
      "[data-candidate-insights-workspace] [data-manager-report-edit-key][data-manager-report-ai-text]"
    ).forEach((field) => {
      const aiValue = (field.dataset.managerReportAiText || "").trim();
      const edited = field.dataset.managerReportManuallyEdited === "true";
      let badge = field.previousElementSibling;
      if (!badge?.classList.contains("talena-ai-field-badge")) {
        badge = document.createElement("span");
        badge.className = BADGE_CLASS + " talena-ai-field-badge";
        field.parentNode.insertBefore(badge, field);
      }
      if (badge.hidden !== !aiValue) badge.hidden = !aiValue;
      if (aiValue) setLabel(badge, edited);
    });
  }

  let scheduled = false;
  function scan() {
    if (!document.querySelector("[data-candidate-insights-workspace]")) return;
    document.querySelectorAll("[data-candidate-insights-workspace]").forEach(removeLegacyKickers);
    RULES.forEach((rule) => markRule(...rule));
    markManagerReportBlocks();
  }

  function schedule() {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(() => {
      scheduled = false;
      scan();
    });
  }

  function start() {
    scan();
    const observer = new MutationObserver((changes) => {
      if (changes.some((change) =>
        change.type === "characterData" ||
        change.type === "childList" ||
        (change.type === "attributes" &&
          ["class", "hidden", "data-has-result", "data-manager-report-ai-text"].includes(change.attributeName))
      )) {
        schedule();
      }
    });
    observer.observe(document.body, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ["class", "hidden", "data-has-result", "data-manager-report-ai-text"]
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else start();
})();
