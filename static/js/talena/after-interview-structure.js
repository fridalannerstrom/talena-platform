(function () {
  "use strict";

  const PANEL_SELECTOR = "#candidate-insights-panel-after-interview";
  const STYLE_ID = "talena-after-interview-structure-v2";

  const TEXT = {
    sv: {
      areas: "Områden att utforska",
      areasDescription:
        "Viktiga delar av rollen eller processkontexten där underlaget behöver fördjupas, nyanseras eller valideras.",
      gaps: "Saknas fortfarande i underlaget",
      gapsDescription:
        "Konkreta informationsluckor som fortfarande behöver fyllas för att bilden ska bli mer komplett.",
      next: "Nästa steg",
      nextDescription:
        "Konkreta uppföljningar som kan ge bättre underlag i de områden som fortfarande behöver fördjupas."
    },
    en: {
      areas: "Areas to explore",
      areasDescription:
        "Important parts of the role or process context where the evidence needs further depth, nuance or validation.",
      gaps: "Still missing from the evidence",
      gapsDescription:
        "Specific evidence gaps that still need to be filled to create a more complete view.",
      next: "Next steps",
      nextDescription:
        "Concrete follow-up actions that may provide better evidence in the areas that still need further exploration."
    }
  };

  function isSwedish() {
    return (document.documentElement.lang || "")
      .toLowerCase()
      .startsWith("sv");
  }

  function copy() {
    return isSwedish() ? TEXT.sv : TEXT.en;
  }

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-column__header {
        display: block !important;
        margin-bottom: 1rem !important;
        text-align: left !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .response-style-item__title {
        margin: 0 0 0.25rem !important;
        color: var(--talena-ink) !important;
        font-size: clamp(1.35rem, 1.9vw, 1.7rem) !important;
        font-weight: 725 !important;
        line-height: 1.12 !important;
        letter-spacing: -0.035em !important;
        text-align: left !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-column__description {
        max-width: 760px;
        color: var(--talena-text-muted) !important;
        font-size: 0.72rem !important;
        line-height: 1.55 !important;
        text-align: left !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-list {
        display: grid !important;
        gap: 0.8rem !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-item {
        padding: 1rem 1.05rem !important;
        border: 1px solid var(--talena-border) !important;
        border-radius: 12px !important;
        background: #fff !important;
        box-shadow: none !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-item__title {
        display: flex !important;
        align-items: center !important;
        gap: 0.6rem !important;
        margin: 0 !important;
        color: var(--talena-ink) !important;
        font-size: 0.83rem !important;
        font-weight: 650 !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-item__title::before {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 25px;
        height: 25px;
        flex: 0 0 25px;
        border-radius: 8px;
        background: #e3f2e7;
        color: #567d63;
        content: "✓";
        font-size: 0.72rem;
        font-weight: 750;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-interpretation {
        margin: 0.58rem 0 0 2.18rem !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-support .post-evidence-interpretation__text {
        color: var(--talena-text) !important;
        font-size: 0.73rem !important;
        line-height: 1.55 !important;
      }

      ${PANEL_SELECTOR} .after-interview-role-exploration .purpose-fit-list-icon {
        background: var(--talena-warning-soft) !important;
        color: #946b31 !important;
      }

      ${PANEL_SELECTOR} .after-interview-evidence-gaps {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid var(--talena-border);
      }

      ${PANEL_SELECTOR} .after-interview-evidence-gaps__title {
        margin-bottom: 0.18rem;
        color: var(--talena-ink);
        font-size: 0.76rem;
        font-weight: 650;
      }

      ${PANEL_SELECTOR} .after-interview-evidence-gaps__description {
        margin-bottom: 0.7rem;
        color: var(--talena-text-muted);
        font-size: 0.68rem;
        line-height: 1.5;
      }

      ${PANEL_SELECTOR} .after-interview-evidence-gaps .purpose-fit-list-card {
        margin: 0 !important;
        padding: 0.85rem 0.95rem !important;
        border-radius: 11px !important;
        background: rgba(250, 249, 247, 0.62) !important;
      }

      ${PANEL_SELECTOR} .after-interview-evidence-gaps .purpose-fit-section-title {
        display: none !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section > .row {
        display: block !important;
        margin-top: 0.75rem !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .after-interview-next-steps-column {
        width: 100% !important;
        max-width: 100% !important;
        padding: 0 !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .purpose-fit-list-card {
        height: auto !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .purpose-fit-list-card > .purpose-fit-section-title {
        display: none !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .purpose-fit-list {
        display: grid;
        gap: 0.55rem;
        margin: 0 !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .purpose-fit-list li {
        margin: 0 !important;
        padding: 0.72rem 0.8rem !important;
        border: 1px solid var(--talena-border) !important;
        border-radius: 11px !important;
        background: #fff !important;
      }

      ${PANEL_SELECTOR} .after-interview-next-steps-section .purpose-fit-list-icon {
        background: #e3f2e7 !important;
        color: #567d63 !important;
      }
    `;

    document.head.appendChild(style);
  }

  function textOf(element) {
    return element?.textContent?.trim() || "";
  }

  function hasMeaningfulUncertainty(card) {
    if (!card) return false;

    const fallback = new Set([
      "No specific remaining uncertainties were identified.",
      "Inga specifika kvarstående osäkerheter identifierades.",
      "Inga kvarstående frågetecken identifierades."
    ]);

    return [...card.querySelectorAll("li")]
      .some((item) => {
        const value = textOf(item);
        return value && !fallback.has(value);
      });
  }

  function findHeadingSection(content, values) {
    return [...content.querySelectorAll("h3.insight-summary-title")]
      .map((heading) => ({ heading, section: heading.closest("section") }))
      .find(({ heading }) => values.includes(textOf(heading))) || null;
  }

  function createAreasSection(referenceSection) {
    const c = copy();
    const section = document.createElement("section");
    section.className = "border-top pt-4 mt-4 mb-4 pb-4 after-interview-role-exploration";
    section.innerHTML = `
      <h3 class="insight-summary-title mb-1"></h3>
      <p class="text-muted small mb-3"></p>
      <div class="d-grid gap-3" data-after-interview-exploration-list></div>
    `;
    section.querySelector("h3").textContent = c.areas;
    section.querySelector("p").textContent = c.areasDescription;
    referenceSection.parentNode.insertBefore(section, referenceSection);
    return section;
  }

  function restructurePanel(panel) {
    if (!panel || panel.dataset.afterInterviewStructureV2 === "true") return;

    const content = panel.querySelector("[data-post-interview-content]");
    if (!content) return;

    panel.dataset.afterInterviewStructureV2 = "true";
    ensureStyles();

    const c = copy();

    const areasMatch = findHeadingSection(content, [
      "Contradictions or tensions to consider",
      "Motsägelser eller spänningar att beakta",
      "Skillnader att utforska vidare",
      "Differences to explore further",
      "Områden att utforska",
      "Areas to explore"
    ]);

    const remainsMatch = findHeadingSection(content, [
      "What remains to be explored",
      "Vad som återstår att utforska",
      "Kvar att utforska",
      "What remains to explore"
    ]);

    if (!remainsMatch?.section) return;

    let areasSection = areasMatch?.section || null;

    if (areasMatch?.heading) {
      areasMatch.heading.textContent = c.areas;
      const description = areasMatch.heading.parentElement?.querySelector("p.text-muted");
      if (description) description.textContent = c.areasDescription;
      areasSection.classList.add("after-interview-role-exploration");
    }

    const remainsSection = remainsMatch.section;
    const cards = [...remainsSection.querySelectorAll(".purpose-fit-list-card")];

    const uncertaintiesCard = cards.find((card) => {
      const title = textOf(card.querySelector(".purpose-fit-section-title"));
      return [
        "Remaining uncertainties",
        "Remaining questions",
        "Kvarstående osäkerheter",
        "Kvarstående frågetecken"
      ].includes(title);
    });

    const nextStepsCard = cards.find((card) => {
      const title = textOf(card.querySelector(".purpose-fit-section-title"));
      return [
        "Suggested follow-up",
        "Föreslagen uppföljning",
        "Nästa steg",
        "Next steps"
      ].includes(title);
    });

    const hasGaps = hasMeaningfulUncertainty(uncertaintiesCard);

    if (hasGaps) {
      if (!areasSection) {
        areasSection = createAreasSection(remainsSection);
      }

      const gaps = document.createElement("div");
      gaps.className = "after-interview-evidence-gaps";

      const title = document.createElement("div");
      title.className = "after-interview-evidence-gaps__title";
      title.textContent = c.gaps;

      const description = document.createElement("div");
      description.className = "after-interview-evidence-gaps__description";
      description.textContent = c.gapsDescription;

      gaps.append(title, description, uncertaintiesCard);
      areasSection.appendChild(gaps);
    }

    const uncertaintyColumn = uncertaintiesCard?.closest(".col-lg-6, .col-12");
    if (uncertaintyColumn && uncertaintyColumn.isConnected) {
      uncertaintyColumn.remove();
    }

    remainsMatch.heading.textContent = c.next;
    const remainsDescription = remainsMatch.heading.parentElement?.querySelector("p.text-muted");
    if (remainsDescription) remainsDescription.textContent = c.nextDescription;

    remainsSection.classList.add("after-interview-next-steps-section");

    const nextColumn = nextStepsCard?.closest(".col-lg-6, .col-12");
    nextColumn?.classList.add("after-interview-next-steps-column");

    if (!nextStepsCard) {
      remainsSection.style.display = "none";
    }
  }

  function scan(scope) {
    if (!scope) return;

    if (scope.matches?.(PANEL_SELECTOR)) {
      restructurePanel(scope);
    }

    scope.querySelectorAll?.(PANEL_SELECTOR).forEach(restructurePanel);

    const closest = scope.closest?.(PANEL_SELECTOR);
    if (closest) restructurePanel(closest);
  }

  function start() {
    scan(document);

    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
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
