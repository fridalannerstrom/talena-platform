(function () {
  "use strict";

  const WORKSPACE_SELECTOR = "[data-candidate-insights-workspace]";

  const SWEDISH_INTERVIEW_TRANSLATIONS = new Map([
    ["Prepare for interview", "Förbered inför intervju"],
    [
      "Use the assessment evidence to prepare the conversation and focus the interview on areas that are useful to explore further.",
      "Använd testresultaten för att förbereda samtalet och fokusera intervjun på områden som är värdefulla att utforska vidare."
    ],
    ["Needs update", "Behöver uppdateras"],
    ["Generate updated decision support", "Generera uppdaterat beslutsstöd"],
    ["The process information has changed", "Processinformationen har ändrats"],
    [
      "This interview preparation was created using an earlier purpose or process context. Generate an updated version before relying on it.",
      "Den här intervjuförberedelsen skapades med ett tidigare syfte eller en tidigare processkontext. Generera en uppdaterad version innan du använder den som underlag."
    ],
    [
      "Combining the available evidence and preparing the interview…",
      "Sammanställer tillgängligt underlag och förbereder intervjun…"
    ],
    ["The interview preparation could not be generated.", "Intervjuförberedelsen kunde inte genereras."],
    ["Prepare the interview", "Förbered intervjun"],
    [
      "Generate an overall synthesis and practical guidance before reviewing the candidate-specific interview questions.",
      "Generera en övergripande sammanställning och praktisk vägledning innan du går igenom de kandidatspecifika intervjufrågorna."
    ],
    ["Generate interview preparation", "Generera intervjuförberedelse"],
    ["Overall synthesis", "Övergripande sammanställning"],
    ["AI-generated insight", "AI-genererad insikt"],
    ["How to approach the conversation", "Så kan du lägga upp samtalet"],
    [
      "Practical interview guidance based on how the candidate used the personality questionnaire response scale.",
      "Praktisk intervjuguide baserad på hur kandidaten använde svarsskalan i personlighetstestet."
    ],
    ["Recommended approach", "Rekommenderat upplägg"],
    ["Questions to explore", "Frågor att utforska"],
    [
      "Response-style interview guidance is not available yet.",
      "Intervjuguide baserad på svarsstil är inte tillgänglig ännu."
    ]
  ]);

  function isSwedish() {
    return (document.documentElement.lang || "").toLowerCase().startsWith("sv");
  }

  function translateInterviewUi(scope) {
    if (!isSwedish() || !scope) return;

    const panels = [];

    if (scope.matches?.("#candidate-insights-panel-prepare-interview")) {
      panels.push(scope);
    }

    scope.querySelectorAll?.("#candidate-insights-panel-prepare-interview").forEach((panel) => {
      panels.push(panel);
    });

    const closestPanel = scope.closest?.("#candidate-insights-panel-prepare-interview");
    if (closestPanel) {
      panels.push(closestPanel);
    }

    [...new Set(panels)].forEach((panel) => {
      const walker = document.createTreeWalker(panel, NodeFilter.SHOW_TEXT);
      let node;

      while ((node = walker.nextNode())) {
        const value = node.nodeValue;
        const trimmed = value.trim();
        const replacement = SWEDISH_INTERVIEW_TRANSLATIONS.get(trimmed);

        if (replacement) {
          node.nodeValue = value.replace(trimmed, replacement);
        }
      }

      panel.querySelectorAll("[title], [aria-label]").forEach((element) => {
        ["title", "aria-label"].forEach((attribute) => {
          const value = element.getAttribute(attribute);
          const replacement = SWEDISH_INTERVIEW_TRANSLATIONS.get(value);
          if (replacement) {
            element.setAttribute(attribute, replacement);
          }
        });
      });
    });
  }

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
    const teamStylesLabel = getTabLabel(root, "team-styles");
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
      teamStylesLabel
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
    translateInterviewUi(scope);

    if (scope.matches?.(WORKSPACE_SELECTOR)) {
      initCandidateEyebrows(scope);
    }

    scope.querySelectorAll?.(WORKSPACE_SELECTOR).forEach((workspace) => {
      translateInterviewUi(workspace);
      initCandidateEyebrows(workspace);
    });
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
