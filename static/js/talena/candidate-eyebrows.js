(function () {
  "use strict";

  const WORKSPACE_SELECTOR = "[data-candidate-insights-workspace]";
  const AFTER_INTERVIEW_STYLE_ID = "talena-after-interview-simplified-styles";

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

  function setText(element, swedish, english) {
    if (!element) return;
    const next = isSwedish() ? swedish : english;
    if (element.textContent.trim() === next) return;
    element.textContent = next;
  }

  function replaceExactText(root, replacements) {
    if (!root) return;

    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    let node;

    while ((node = walker.nextNode())) {
      const value = node.nodeValue;
      const trimmed = value.trim();
      const replacement = replacements.get(trimmed);

      if (replacement) {
        node.nodeValue = value.replace(trimmed, replacement);
      }
    }
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
      replaceExactText(panel, SWEDISH_INTERVIEW_TRANSLATIONS);

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

  function ensureAfterInterviewStyles() {
    if (document.getElementById(AFTER_INTERVIEW_STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = AFTER_INTERVIEW_STYLE_ID;
    style.textContent = `
      #candidate-insights-panel-after-interview.after-interview-simplified
      [data-interview-notes-root] {
        margin-top: 1.4rem !important;
        margin-bottom: 0 !important;
        padding: 1.15rem 1.2rem !important;
        border: 1px solid var(--talena-border) !important;
        border-radius: 12px !important;
        background: #fff !important;
        box-shadow: none !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      [data-post-interview-section] {
        margin-top: 1.5rem !important;
        padding-top: 1.5rem !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      [data-post-interview-empty] {
        margin-top: 1rem !important;
        padding: 1.15rem !important;
        border: 1px solid var(--talena-border) !important;
        border-radius: 12px !important;
        background: rgba(255, 248, 242, 0.42) !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      [data-post-interview-empty] .combined-questions-empty-state__icon {
        display: none !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      [data-post-interview-content] > .purpose-fit-section:first-child {
        margin-top: 1.15rem !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      .post-evidence-grid {
        margin-top: 0.35rem !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      .post-evidence-col > section {
        margin-top: 1rem !important;
      }

      #candidate-insights-panel-after-interview.after-interview-simplified
      .personality-questions-context-note:last-child {
        margin-top: 1.5rem !important;
        border-top: 1px solid var(--talena-border) !important;
        border-right: 0 !important;
        border-bottom: 0 !important;
        border-left: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        padding: 1rem 0 0 !important;
      }

      @media (max-width: 767px) {
        #candidate-insights-panel-after-interview.after-interview-simplified
        [data-interview-notes-root] {
          padding: 1rem !important;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function simplifyAfterInterviewPanel(panel) {
    if (!panel) return;

    ensureAfterInterviewStyles();
    panel.classList.add("after-interview-simplified");

    const copy = isSwedish()
      ? {
          headerDescription:
            "Samla intervjuunderlaget och jämför det med testresultaten för att nyansera bilden och se vad som återstår att utforska.",
          notesTitle: "Intervjuunderlag",
          notesDescription:
            "Samla relevanta exempel, svar och observationer från intervjun här.",
          compileTitle: "Sammanställ underlag",
          compileDescription:
            "Jämför testresultaten med det sparade intervjuunderlaget och skapa en gemensam, nyanserad bild.",
          compileButton: "Sammanställ underlag",
          updateButton: "Uppdatera sammanställningen",
          readyTitle: "Redo att sammanställa",
          overall: "Övergripande sammanställning",
          supports: "Det intervjun stärker",
          supportsDescription:
            "Intervjuunderlag som stödjer eller bekräftar mönster i testresultaten.",
          nuances: "Det intervjun nyanserar",
          nuancesDescription:
            "Områden där intervjun tillför kontext eller ger anledning till en mer nyanserad tolkning.",
          contradictions: "Skillnader att utforska vidare",
          contradictionsDescription:
            "Här skiljer sig testindikationer och intervjuunderlag åt. Utforska skillnaderna i stället för att automatiskt prioritera den ena källan.",
          remains: "Kvar att utforska",
          remainsDescription:
            "Områden där mer underlag kan hjälpa till att skapa en mer komplett bild.",
          uncertainties: "Kvarstående frågetecken",
          nextSteps: "Nästa steg",
          assessment: "Indikation från test",
          interview: "Intervjuunderlag",
          combined: "Samlad tolkning",
          disclaimerTitle: "Beslutsstöd, inte ett beslut",
          outdatedTitle: "Intervjuunderlaget har ändrats",
          loading: "Jämför testresultat med intervjuunderlaget…",
          error: "Underlaget kunde inte sammanställas."
        }
      : {
          headerDescription:
            "Bring the interview evidence together with the assessment results to add context, nuance and identify what still needs to be explored.",
          notesTitle: "Interview evidence",
          notesDescription:
            "Capture relevant examples, answers and observations from the interview here.",
          compileTitle: "Compile evidence",
          compileDescription:
            "Compare the assessment results with the saved interview evidence and create one balanced, contextualised view.",
          compileButton: "Compile evidence",
          updateButton: "Update compiled evidence",
          readyTitle: "Ready to compile",
          overall: "Overall synthesis",
          supports: "What the interview supports",
          supportsDescription:
            "Interview evidence that supports or reinforces patterns in the assessment results.",
          nuances: "What the interview adds or nuances",
          nuancesDescription:
            "Areas where the interview adds context or suggests a more nuanced interpretation.",
          contradictions: "Differences to explore further",
          contradictionsDescription:
            "Assessment indications and interview evidence differ here. Explore the difference rather than automatically favouring either source.",
          remains: "What remains to be explored",
          remainsDescription:
            "Areas where additional evidence may help create a more complete picture.",
          uncertainties: "Remaining questions",
          nextSteps: "Next steps",
          assessment: "Assessment indication",
          interview: "Interview evidence",
          combined: "Combined interpretation",
          disclaimerTitle: "Decision support, not a decision",
          outdatedTitle: "The interview evidence has changed",
          loading: "Comparing assessment results with the interview evidence…",
          error: "The evidence could not be compiled."
        };

    const card = panel.querySelector(".final-output-card");
    const cardHeader = card?.firstElementChild;
    setText(
      cardHeader?.querySelector("h2.insight-summary-title"),
      "Efter intervju",
      "After interview"
    );
    setText(
      cardHeader?.querySelector("p.text-muted"),
      copy.headerDescription,
      copy.headerDescription
    );

    const notesRoot = panel.querySelector("[data-interview-notes-root]");
    if (notesRoot) {
      setText(
        notesRoot.querySelector(".purpose-fit-section-title"),
        copy.notesTitle,
        copy.notesTitle
      );
      setText(
        notesRoot.querySelector(".purpose-fit-section-title + .small.text-muted"),
        copy.notesDescription,
        copy.notesDescription
      );
    }

    const postSection = panel.querySelector("[data-post-interview-section]");
    if (!postSection) return;

    const postHeader = postSection.firstElementChild;
    setText(
      postHeader?.querySelector("h3.insight-summary-title"),
      copy.compileTitle,
      copy.compileTitle
    );
    setText(
      postHeader?.querySelector("p.text-muted"),
      copy.compileDescription,
      copy.compileDescription
    );

    postSection.querySelectorAll("[data-post-interview-generate]").forEach((button) => {
      const isRegenerate = button.dataset.regenerate === "true";

      if (isRegenerate) {
        if (button.getAttribute("title") !== copy.updateButton) {
          button.setAttribute("title", copy.updateButton);
        }
        if (button.getAttribute("aria-label") !== copy.updateButton) {
          button.setAttribute("aria-label", copy.updateButton);
        }
      } else if (button.textContent.trim() !== copy.compileButton) {
        const icon = button.querySelector("svg, i");
        button.textContent = copy.compileButton;
        if (icon) {
          button.prepend(icon);
        }
      }
    });

    setText(
      postSection.querySelector("[data-post-interview-outdated] .fw-semibold"),
      copy.outdatedTitle,
      copy.outdatedTitle
    );

    const thinking = postSection.querySelector("[data-post-interview-thinking]");
    if (thinking) {
      const textNodes = [...thinking.querySelectorAll("span")];
      setText(textNodes[textNodes.length - 1], copy.loading, copy.loading);
    }

    setText(
      postSection.querySelector("[data-post-interview-error]"),
      copy.error,
      copy.error
    );

    const emptyState = postSection.querySelector("[data-post-interview-empty]");
    setText(
      emptyState?.querySelector(".personality-questions-section-title"),
      copy.readyTitle,
      copy.readyTitle
    );

    const content = postSection.querySelector("[data-post-interview-content]");
    if (!content) return;

    setText(
      content.querySelector(":scope > .purpose-fit-section:first-child .purpose-fit-section-title"),
      copy.overall,
      copy.overall
    );

    const leftColumn = content.querySelector(".post-evidence-col--left");
    setText(
      leftColumn?.querySelector(".response-style-item__title"),
      copy.supports,
      copy.supports
    );
    setText(
      leftColumn?.querySelector(".post-evidence-column__description"),
      copy.supportsDescription,
      copy.supportsDescription
    );

    const rightColumn = [...content.querySelectorAll(".post-evidence-col")]
      .find((column) => !column.classList.contains("post-evidence-col--left"));
    setText(
      rightColumn?.querySelector(".response-style-item__title"),
      copy.nuances,
      copy.nuances
    );
    setText(
      rightColumn?.querySelector(".post-evidence-column__description"),
      copy.nuancesDescription,
      copy.nuancesDescription
    );

    content.querySelectorAll(".post-evidence-block--assessment .post-evidence-block__label")
      .forEach((element) => setText(element, copy.assessment, copy.assessment));
    content.querySelectorAll(".post-evidence-block--interview .post-evidence-block__label")
      .forEach((element) => setText(element, copy.interview, copy.interview));
    content.querySelectorAll(".post-evidence-interpretation__label")
      .forEach((element) => setText(element, copy.combined, copy.combined));

    content.querySelectorAll("h3.insight-summary-title").forEach((heading) => {
      const current = heading.textContent.trim();

      if (
        current === "Contradictions or tensions to consider"
        || current === "Motsägelser eller spänningar att beakta"
        || current === "Skillnader att utforska vidare"
        || current === "Differences to explore further"
      ) {
        setText(heading, copy.contradictions, copy.contradictions);
        setText(
          heading.parentElement?.querySelector("p.text-muted"),
          copy.contradictionsDescription,
          copy.contradictionsDescription
        );
      }

      if (
        current === "What remains to be explored"
        || current === "Vad som återstår att utforska"
        || current === "Kvar att utforska"
      ) {
        setText(heading, copy.remains, copy.remains);
        setText(
          heading.parentElement?.querySelector("p.text-muted"),
          copy.remainsDescription,
          copy.remainsDescription
        );
      }
    });

    content.querySelectorAll(".purpose-fit-list-card .purpose-fit-section-title")
      .forEach((title) => {
        const current = title.textContent.trim();

        if (
          current === "Remaining uncertainties"
          || current === "Kvarstående osäkerheter"
          || current === "Kvarstående frågetecken"
          || current === "Remaining questions"
        ) {
          setText(title, copy.uncertainties, copy.uncertainties);
        }

        if (
          current === "Suggested follow-up"
          || current === "Föreslagen uppföljning"
          || current === "Nästa steg"
          || current === "Next steps"
        ) {
          setText(title, copy.nextSteps, copy.nextSteps);
        }
      });

    const disclaimer = panel.querySelector(
      ".personality-questions-context-note:last-child .personality-questions-context-note__title"
    );
    setText(disclaimer, copy.disclaimerTitle, copy.disclaimerTitle);
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

    const afterPanels = [];
    if (scope.matches?.("#candidate-insights-panel-after-interview")) {
      afterPanels.push(scope);
    }
    scope.querySelectorAll?.("#candidate-insights-panel-after-interview")
      .forEach((panel) => afterPanels.push(panel));
    const closestAfterPanel = scope.closest?.("#candidate-insights-panel-after-interview");
    if (closestAfterPanel) {
      afterPanels.push(closestAfterPanel);
    }
    [...new Set(afterPanels)].forEach(simplifyAfterInterviewPanel);

    if (scope.matches?.(WORKSPACE_SELECTOR)) {
      simplifyAfterInterviewPanel(
        scope.querySelector("#candidate-insights-panel-after-interview")
      );
      initCandidateEyebrows(scope);
    }

    scope.querySelectorAll?.(WORKSPACE_SELECTOR).forEach((workspace) => {
      translateInterviewUi(workspace);
      simplifyAfterInterviewPanel(
        workspace.querySelector("#candidate-insights-panel-after-interview")
      );
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
