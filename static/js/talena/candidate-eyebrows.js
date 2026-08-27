(function () {
  "use strict";

  const WORKSPACE_SELECTOR = "[data-candidate-insights-workspace]";

  function getTabLabel(root, key) {
    const tab = root.querySelector(`[data-insights-tab="${key}"]`);
    return tab ? tab.textContent.trim() : "";
  }

  function getInterviewLabel() {
    const lang = (document.documentElement.lang || "").toLowerCase();
    return lang.startsWith("sv") ? "Intervju" : "Interview";
  }

  function cleanExistingKickers(root) {
    root.querySelectorAll(".insight-summary-kicker").forEach((kicker) => {
      kicker.textContent = kicker.textContent
        .replace(/^[\s✨⭐]+/u, "")
        .trim();
    });
  }

  function addEyebrowBefore(heading, label) {
    if (!heading || !label) return;

    const previous = heading.previousElementSibling;

    if (previous?.classList.contains("candidate-section-eyebrow")) {
      previous.textContent = label;
      return;
    }

    const eyebrow = document.createElement("div");
    eyebrow.className = "candidate-section-eyebrow";
    eyebrow.textContent = label;

    heading.parentNode.insertBefore(eyebrow, heading);
  }

  function initCandidateEyebrows(root) {
    if (!root || root.dataset.eyebrowsReady === "true") return;

    cleanExistingKickers(root);

    const personalityLabel = getTabLabel(root, "personality");
    const motivationLabel = getTabLabel(root, "motivation");
    const cognitiveLabel = getTabLabel(root, "cognitive");
    const interviewLabel = getInterviewLabel();

    const aiLabel =
      root.querySelector("#candidate-insights-panel-overview .insight-summary-kicker")
        ?.textContent.trim() || "";

    addEyebrowBefore(
      root.querySelector(
        ".response-styles-section .response-styles-header h2.insight-summary-title"
      ),
      personalityLabel
    );

    addEyebrowBefore(
      root.querySelector(
        ".personality-profile > .response-styles-header h2.insight-summary-title"
      ),
      personalityLabel
    );

    addEyebrowBefore(
      root.querySelector(
        ".motivation-profile-card .team-styles-header h2.insight-summary-title"
      ),
      motivationLabel
    );

    addEyebrowBefore(
      root.querySelector(
        ".team-styles-section .team-styles-header h2.insight-summary-title"
      ),
      personalityLabel
    );

    root.querySelectorAll(".cognitive-result-card__header h3").forEach((heading) => {
      addEyebrowBefore(heading, cognitiveLabel);
    });

    addEyebrowBefore(
      root.querySelector(
        "#candidate-insights-panel-prepare-interview .final-output-card > div:first-child h2.insight-summary-title"
      ),
      aiLabel || interviewLabel
    );

    addEyebrowBefore(
      root.querySelector(
        "#candidate-insights-panel-after-interview .final-output-card > div:first-child h2.insight-summary-title"
      ),
      interviewLabel
    );

    addEyebrowBefore(
      root.querySelector(
        "#candidate-insights-panel-after-interview [data-post-interview-section] h3.insight-summary-title"
      ),
      aiLabel || interviewLabel
    );

    addEyebrowBefore(
      root.querySelector(
        ".combined-questions-card .personality-questions-header h2.insight-summary-title"
      ),
      interviewLabel
    );

    root.dataset.eyebrowsReady = "true";
  }

  function scan(scope) {
    if (scope.matches?.(WORKSPACE_SELECTOR)) {
      initCandidateEyebrows(scope);
    }

    scope.querySelectorAll?.(WORKSPACE_SELECTOR).forEach(initCandidateEyebrows);
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
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
