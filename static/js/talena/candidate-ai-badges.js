(function () {
  "use strict";

  // Explicit data provenance: each output selector refers to an AI response
  // field or an AI-generated question, never a heading keyword or a chart.
  // Candidate reports, static test interpretations and interviewer notes have
  // no corresponding rules, so they cannot be marked by this code.
  const RULES = [
    ["[data-overview-interpretation-card]", "[data-overview-interpretation-title]", "[data-overview-interpretation-content]"],
    ["[data-personality-ai-root] .personality-interpretation__overall", ".purpose-fit-section-title", "[data-personality-ai-interpretation]"],
    ["[data-motivation-ai-root] .purpose-fit-section", ".purpose-fit-section-title", "[data-motivation-ai-interpretation]"],
    ["[data-cognitive-interpretation-root] .purpose-fit-section", ".purpose-fit-section-title", "[data-cognitive-ai-interpretation]"],
    ["[data-pre-interview-content] > .purpose-fit-section:first-child", ".purpose-fit-section-title", "[data-pre-interview-overall-synthesis]"],
    ["[data-post-interview-content] > .purpose-fit-section:first-child", ".purpose-fit-section-title", ".purpose-fit-summary"],
    ["[data-personality-ai-dynamics-section]", ".purpose-fit-section-title", "[data-personality-ai-dynamics]"],
    ["[data-personality-ai-motivation-section]:not([data-personality-ai-motivation-missing])", ".purpose-fit-section-title", "[data-personality-ai-motivation-interaction]"],
    ["[data-personality-ai-supportive-section]", ".purpose-fit-section-title", "[data-personality-ai-supportive] li"],
    ["[data-personality-ai-explore-section]", ".purpose-fit-section-title", "[data-personality-ai-explore] li"],
    ["[data-motivation-ai-expectation-section]", ".purpose-fit-section-title", "[data-motivation-ai-expectation]"],
    ["[data-motivation-ai-engagement-section]", ".purpose-fit-section-title", "[data-motivation-ai-engagement] li"],
    ["[data-motivation-ai-clarify-section]", ".purpose-fit-section-title", "[data-motivation-ai-clarify] li"],
    ["[data-cognitive-ai-considerations-section]", ".purpose-fit-section-title", "[data-cognitive-ai-considerations] li"],
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

  // #431 / #401: the Overview mirrors each area tab's own current AI text.
  // The area streams can finish after Overview was first rendered; mirror the
  // DOM source without an extra request or a second interpretation lifecycle.
  function syncOverviewInterpretations() {
    const definitions = [
      ["cognitive", "[data-cognitive-interpretation-root]", "[data-cognitive-ai-interpretation]"],
      ["personality", "[data-personality-ai-root]", "[data-personality-ai-interpretation]"],
      ["motivation", "[data-motivation-ai-root]", "[data-motivation-ai-interpretation]"],
    ];
    document.querySelectorAll("[data-candidate-insights-workspace]").forEach((workspace) => {
      definitions.forEach(([key, rootSelector, textSelector]) => {
        const card = workspace.querySelector('[data-overview-interpretation-card="' + key + '"]');
        if (!card) return;
        const content = card.querySelector("[data-overview-interpretation-content]");
        const empty = card.querySelector("[data-overview-interpretation-empty]");
        const message = card.querySelector("[data-overview-interpretation-empty-text]");
        const sourceRoot = workspace.querySelector(rootSelector);
        const sourceText = sourceRoot?.querySelector(textSelector)?.textContent.trim() || "";
        const outdated = sourceRoot?.dataset.status === "outdated";
        const current = sourceRoot?.dataset.hasResult === "true" &&
          !["outdated", "generating"].includes(sourceRoot?.dataset.status);
        const value = current ? sourceText : "";
        if (content && content.textContent !== value) content.textContent = value;
        if (content) content.classList.toggle("d-none", !value);
        if (empty) empty.classList.toggle("d-none", Boolean(value));
        if (message) {
          const sv = isSwedish();
          const newMessage = outdated
            ? (sv ? "Tolkningen behöver uppdateras innan den kan visas här." : "Update the interpretation before viewing it here.")
            : (sv ? "Ingen tolkning har skapats för detta område ännu." : "No interpretation has been generated for this area yet.");
          if (message.textContent.trim() !== newMessage) message.textContent = newMessage;
        }
      });
    });
  }

  function markRichTextHeadings() {
    // #442: one discreet AI tag per *generated report section*. Do not
    // label every generated Markdown subheading as a separate AI result.
    document.querySelectorAll(
      '[data-candidate-insights-workspace] .after-interview-tab-card'
    ).forEach((card) => {
      const body = card.querySelector(
        '[data-after-interview-block-content][data-after-interview-ai-origin="true"]'
      );
      const heading = card.querySelector(
        ".after-interview-tab-card__header .after-interview-tab-card__title"
      );
      if (!heading) return;
      setBadge(heading, hasGeneratedText(body), false);
    });
  }

  function markManagerReportBlocks() {
    // Group the six editable Personality texts under ONE provenance tag on
    // "Personlighet", and the single wellbeing_tips text under its title.
    // Static skills and MQ reference cards must never carry AI badges.
    document.querySelectorAll(
      "[data-candidate-insights-workspace] .after-interview-manager-report"
    ).forEach((report) => {
      [
        [".after-interview-manager-report__personality",
          ".after-interview-manager-report__personality-title"],
        [".after-interview-manager-report__wellbeing",
          ".after-interview-manager-report__wellbeing-title"],
      ].forEach(([sectionSelector, titleSelector]) => {
        const section = report.querySelector(sectionSelector);
        if (!section) return;
        const fields = [...section.querySelectorAll(
          "[data-manager-report-edit-key][data-manager-report-ai-text]"
        )];
        const hasAi = fields.some((field) =>
          (field.dataset.managerReportAiText || "").trim()
        );
        const hasManualEdit = fields.some((field) =>
          field.dataset.managerReportManuallyEdited === "true"
        );
        setBadge(section.querySelector(titleSelector), hasAi, hasManualEdit);
        // Remove legacy per-paragraph badges if a live partial was updated.
        fields.forEach((field) => {
          const previous = field.previousElementSibling;
          if (previous?.classList.contains("talena-ai-field-badge")) {
            previous.remove();
          }
        });
      });
    });
  }

  let scheduled = false;
  function scan() {
    if (!document.querySelector("[data-candidate-insights-workspace]")) return;
    document.querySelectorAll("[data-candidate-insights-workspace]").forEach(removeLegacyKickers);
    syncOverviewInterpretations();
    RULES.forEach((rule) => markRule(...rule));
    markRichTextHeadings();
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
          ["class", "hidden", "data-has-result", "data-status", "data-manager-report-ai-text"].includes(change.attributeName))
      )) {
        schedule();
      }
    });
    observer.observe(document.body, {
      subtree: true, childList: true, characterData: true,
      attributes: true, attributeFilter: ["class", "hidden", "data-has-result", "data-status", "data-manager-report-ai-text"]
    });
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else start();
})();
