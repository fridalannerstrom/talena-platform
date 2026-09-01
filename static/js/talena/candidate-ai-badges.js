(function () {
  "use strict";

  const WORKSPACE_SELECTOR = "[data-candidate-insights-workspace]";
  const STYLE_ID = "talena-ai-generated-badge-styles";
  const BADGE_CLASS = "talena-ai-generated-badge";
  const ROW_CLASS = "talena-ai-title-row";

  const MAJOR_AI_HEADING_SELECTORS = [
    "#purposeFitTitle",
    "[data-personality-ai-root] h2[data-personality-ai-title]",
    "[data-motivation-ai-root] > div:first-of-type > div:first-child > h2.insight-summary-title",
    "[data-cognitive-interpretation-root] > div:first-of-type > div:first-child > h2.insight-summary-title",
    "[data-personality-questions-root] .personality-questions-header h2.insight-summary-title",
    "[data-motivation-questions-root] .personality-questions-header h2.insight-summary-title",
    "[data-cognitive-questions-root] .personality-questions-header h2.insight-summary-title",
    "[data-combined-questions-root] > .personality-questions-header h2.insight-summary-title",
    "#candidate-insights-panel-prepare-interview > .final-output-card > .d-flex:first-child > div:first-child > h2.insight-summary-title",
    "[data-post-interview-section] > .d-flex:first-child > div:first-child > h3.insight-summary-title"
  ];

  function isSwedish() {
    return (document.documentElement.lang || "").toLowerCase().startsWith("sv");
  }

  function badgeLabel() {
    return isSwedish() ? "AI-genererat" : "AI-generated";
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .process-page .${ROW_CLASS} {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.65rem;
        margin-bottom: 0.25rem;
      }

      .process-page .${ROW_CLASS} > .insight-summary-title {
        margin: 0 !important;
      }

      .process-page .${BADGE_CLASS} {
        display: inline-flex;
        align-items: center;
        gap: 0.32rem;
        width: fit-content;
        padding: 0.34rem 0.58rem;
        border: 1px solid #cdddf8;
        border-radius: 999px;
        background: #eff5ff;
        color: #3f67a3;
        font-size: 0.68rem;
        font-weight: 720;
        line-height: 1;
        letter-spacing: 0;
        text-transform: none;
        white-space: nowrap;
        box-shadow: 0 1px 0 rgba(61, 103, 165, 0.04);
      }

      .process-page [data-talena-ai-badged="true"]::after {
        content: none !important;
        display: none !important;
      }

      @media (max-width: 575.98px) {
        .process-page .${ROW_CLASS} {
          gap: 0.5rem;
        }

        .process-page .${BADGE_CLASS} {
          padding: 0.3rem 0.5rem;
          font-size: 0.65rem;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function setText(element, swedish, english) {
    if (!element) return;
    const next = isSwedish() ? swedish : english;
    if (element.textContent.trim() !== next) {
      element.textContent = next;
    }
  }

  function polishAiLabels(scope) {
    if (!scope?.querySelector) return;

    setText(
      scope.querySelector('[data-insights-tab="overview"]'),
      "Sammanfattning",
      "Summary"
    );

    const summaryTitle = scope.querySelector("#purposeFitTitle");
    if (summaryTitle) {
      const current = summaryTitle.textContent.trim().toLowerCase();
      const preliminary = current.includes("preliminary") || current.includes("preliminär");
      setText(
        summaryTitle,
        preliminary ? "Preliminär sammanfattning" : "Sammanfattning",
        preliminary ? "Preliminary summary" : "Summary"
      );
    }

    setText(
      scope.querySelector("#motivation-tab-interpretation span"),
      "Tolkning",
      "Interpretation"
    );

    setText(
      scope.querySelector("#cognitive-tab-interpretation span"),
      "Tolkning",
      "Interpretation"
    );
  }

  function removeGeneratedEyebrowNearHeading(heading) {
    if (!heading) return;

    const parent = heading.parentElement;
    if (!parent) return;

    parent.querySelectorAll(":scope > .insight-summary-kicker").forEach((kicker) => {
      kicker.remove();
    });

    const previous = heading.previousElementSibling;
    if (previous?.classList.contains("candidate-section-eyebrow")) {
      previous.remove();
    }
  }

  function ensureBadgeForHeading(heading) {
    if (!heading) return;

    ensureStyles();

    if (heading.dataset.talenaAiBadged === "true") {
      const row = heading.closest(`.${ROW_CLASS}`);
      const badge = row?.querySelector(`.${BADGE_CLASS}`);
      if (badge) badge.textContent = `✦ ${badgeLabel()}`;
      return;
    }

    removeGeneratedEyebrowNearHeading(heading);

    const parent = heading.parentElement;
    if (!parent) return;

    const row = document.createElement("div");
    row.className = ROW_CLASS;

    parent.insertBefore(row, heading);
    row.appendChild(heading);

    const badge = document.createElement("span");
    badge.className = `${BADGE_CLASS} badge rounded-pill`;
    badge.textContent = `✦ ${badgeLabel()}`;
    badge.setAttribute("aria-label", badgeLabel());

    row.appendChild(badge);
    heading.dataset.talenaAiBadged = "true";
  }

  function removeLegacyNestedAiMarkers(scope) {
    scope
      .querySelectorAll(
        "#candidate-insights-panel-prepare-interview [data-response-style-interview-guidance] .insight-summary-kicker"
      )
      .forEach((marker) => marker.remove());
  }

  function removeWrongAiEyebrows(scope) {
    const prepareHeading = scope.querySelector(
      "#candidate-insights-panel-prepare-interview > .final-output-card > .d-flex:first-child > div:first-child > h2.insight-summary-title"
    );

    const postHeading = scope.querySelector(
      "[data-post-interview-section] > .d-flex:first-child > div:first-child > h3.insight-summary-title"
    );

    [prepareHeading, postHeading].forEach((heading) => {
      if (!heading) return;

      const previous = heading.previousElementSibling;
      if (previous?.classList.contains("candidate-section-eyebrow")) {
        previous.remove();
      }
    });
  }

  function applyBadges(scope) {
    if (!scope?.querySelectorAll) return;

    ensureStyles();
    polishAiLabels(scope);
    removeWrongAiEyebrows(scope);
    removeLegacyNestedAiMarkers(scope);

    MAJOR_AI_HEADING_SELECTORS.forEach((selector) => {
      scope.querySelectorAll(selector).forEach(ensureBadgeForHeading);
    });
  }

  function scan(scope) {
    if (!scope) return;

    if (scope.matches?.(WORKSPACE_SELECTOR)) {
      applyBadges(scope);
    }

    scope.querySelectorAll?.(WORKSPACE_SELECTOR).forEach(applyBadges);

    const workspace = scope.closest?.(WORKSPACE_SELECTOR);
    if (workspace) applyBadges(workspace);
  }

  function start() {
    scan(document);

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) {
            scan(node);
          }
        });
      });
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
