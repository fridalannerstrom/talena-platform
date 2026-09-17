(() => {
  "use strict";

  const PANEL_SELECTOR = "#candidate-insights-panel-after-interview";
  const STYLE_ID = "talena-after-interview-tabs-v1";
  const URL_PARAM = "afterTab";

  const COPY = {
    sv: {
      tabs: {
        overview: "Helhetsbild",
        tests: "Testresultat",
        interview: "Intervjusammanfattning",
        explore: "Undersök vidare",
        wellbeing: "Tips för trivsel",
        evidence: "Underlag",
      },
      descriptions: {
        overview: "En samlad bild av testresultat, intervjuunderlag och processkontext.",
        tests: "Testresultat presenterade för samtalet med chef eller kandidat.",
        interview: "Vad intervjun bekräftar, nyanserar eller tillför till testresultaten.",
        explore: "Frågor och områden där ytterligare underlag kan ge en mer komplett bild.",
        wellbeing: "Förutsättningar och samtalspunkter som kan bidra till trivsel i rollen.",
        evidence: "Intervjuanteckningar och svar som Talena använder som underlag.",
      },
      generated: "AI-genererat",
      generatedComplete: "Sammanställning genererad",
      generatedCompleteDescription: "Sammanställningen är klar och övriga flikar är nu tillgängliga.",
      unavailable: "Det här innehållet blir tillgängligt när intervjuunderlaget har sammanställts.",
      candidateUnavailable: "Kandidatversionen är inte genererad ännu.",
      manager: "Till chef",
      candidate: "Till kandidat",
    },
    en: {
      tabs: {
        overview: "Overall picture",
        tests: "Assessment results",
        interview: "Interview summary",
        explore: "Explore further",
        wellbeing: "Wellbeing tips",
        evidence: "Evidence",
      },
      descriptions: {
        overview: "A combined view of assessment results, interview evidence and process context.",
        tests: "Assessment content prepared for a conversation with a manager or candidate.",
        interview: "What the interview confirms, nuances or adds to the assessment results.",
        explore: "Questions and areas where additional evidence may create a more complete view.",
        wellbeing: "Conditions and conversation points that may support wellbeing in the role.",
        evidence: "Interview notes and answers used by Talena as evidence.",
      },
      generated: "AI-generated",
      generatedComplete: "Compilation generated",
      generatedCompleteDescription: "The compilation is ready and the other tabs are now available.",
      unavailable: "This content becomes available when the interview evidence has been compiled.",
      candidateUnavailable: "The candidate version has not been generated yet.",
      manager: "For manager",
      candidate: "For candidate",
    },
  };

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const copy = () => (isSwedish() ? COPY.sv : COPY.en);

  const textOf = (element) =>
    (element?.textContent || "").replace(/\s+/g, " ").trim();

  const sourceBlock = (panel, key) =>
    panel.querySelector('[data-after-interview-block="' + key + '"]');

  const sourceContent = (panel, key) => {
    const source = sourceBlock(panel, key);
    const content = source?.querySelector("[data-after-interview-block-content]") || null;
    if (!content || !content.textContent.trim()) return null;
    return content;
  };

  const makeCard = (panel, key, title, description, fallback) => {
    const card = document.createElement("section");
    card.className = "after-interview-tab-card";
    const header = document.createElement("div");
    header.className = "after-interview-tab-card__header";

    const eyebrow = document.createElement("div");
    eyebrow.className = "after-interview-tab-card__eyebrow";
    eyebrow.textContent = "✦ " + copy().generated;

    const heading = document.createElement("h3");
    heading.className = "after-interview-tab-card__title";
    heading.textContent = title;

    const intro = document.createElement("p");
    intro.className = "after-interview-tab-card__description";
    intro.textContent = description;

    header.append(eyebrow, heading, intro);
    card.appendChild(header);

    const supplied = sourceContent(panel, key);
    const body = supplied || fallback;
    if (body) {
      body.classList.add("after-interview-tab-card__body");
      card.appendChild(body);
    } else {
      const empty = document.createElement("div");
      empty.className = "after-interview-tab-empty";
      empty.textContent = copy().unavailable;
      card.appendChild(empty);
    }
    return card;
  };

  const makeTab = (key, label, panelId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "candidate-insights-view-option";
    button.dataset.afterInterviewTab = key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", panelId);
    button.setAttribute("aria-selected", "false");
    button.textContent = label;
    return button;
  };

  const makePanel = (key, panelId) => {
    const panel = document.createElement("div");
    panel.className = "candidate-insights-subpanel after-interview-tab-panel";
    panel.dataset.afterInterviewTabPanel = key;
    panel.id = panelId;
    panel.setAttribute("role", "tabpanel");
    panel.hidden = true;
    return panel;
  };

  const makeInnerTab = (key, label, panelId) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "candidate-insights-view-option";
    button.dataset.afterInterviewInnerTab = key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", panelId);
    button.setAttribute("aria-selected", "false");
    button.textContent = label;
    return button;
  };

  const makeTestCard = (panel, summary, evidenceGrid) => {
    const card = document.createElement("section");
    card.className = "after-interview-tab-card";
    card.dataset.afterInterviewGeneratedCard = "test-results";

    const heading = document.createElement("h3");
    heading.className = "after-interview-tab-card__title";
    heading.textContent = copy().tabs.tests;

    const intro = document.createElement("p");
    intro.className = "after-interview-tab-card__description";
    intro.textContent = copy().descriptions.tests;
    const suppliedIntro = sourceContent(panel, "test_results_intro");
    if (suppliedIntro) suppliedIntro.classList.add("after-interview-tab-card__body");

    const nav = document.createElement("div");
    nav.className = "candidate-insights-view-switcher after-interview-inner-tabs";
    nav.setAttribute("role", "tablist");
    nav.setAttribute("aria-label", copy().tabs.tests);

    const manager = document.createElement("div");
    manager.className = "after-interview-inner-panel";
    manager.dataset.afterInterviewInnerPanel = "manager";
    manager.id = "after-interview-test-manager";
    manager.setAttribute("role", "tabpanel");

    const candidate = document.createElement("div");
    candidate.className = "after-interview-inner-panel";
    candidate.dataset.afterInterviewInnerPanel = "candidate";
    candidate.id = "after-interview-test-candidate";
    candidate.setAttribute("role", "tabpanel");

    nav.append(
      makeInnerTab("manager", copy().manager, manager.id),
      makeInnerTab("candidate", copy().candidate, candidate.id),
    );

    const managerContent = sourceContent(panel, "test_results_manager");
    const candidateContent = sourceContent(panel, "test_results_candidate");

    if (managerContent) manager.appendChild(managerContent);
    else if (evidenceGrid) manager.appendChild(evidenceGrid.cloneNode(true));
    else if (summary) manager.appendChild(summary.cloneNode(true));
    else manager.textContent = copy().unavailable;

    if (candidateContent) candidate.appendChild(candidateContent);
    else {
      const empty = document.createElement("div");
      empty.className = "after-interview-tab-empty";
      empty.textContent = copy().candidateUnavailable;
      candidate.appendChild(empty);
    }

    const activate = (key, updateUrl = true) => {
      card.querySelectorAll("[data-after-interview-inner-tab]").forEach((button) => {
        const active = button.dataset.afterInterviewInnerTab === key;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
      });
      card.querySelectorAll("[data-after-interview-inner-panel]").forEach((item) => {
        item.hidden = item.dataset.afterInterviewInnerPanel !== key;
      });
      if (updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set("afterTestTab", key);
        window.history.replaceState({}, "", url);
      }
    };

    nav.addEventListener("click", (event) => {
      const button = event.target.closest("[data-after-interview-inner-tab]");
      if (button) activate(button.dataset.afterInterviewInnerTab);
    });

    card.append(heading, intro);
    if (suppliedIntro) card.appendChild(suppliedIntro);
    card.append(nav, manager, candidate);
    activate(
      new URL(window.location.href).searchParams.get("afterTestTab") === "candidate"
        ? "candidate"
        : "manager",
      false,
    );
    return card;
  };

  const ensureStyles = () => {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = String.raw`
      __PANEL__ .candidate-insights-subnavigation {
        margin: 0 !important; padding: 0 1.5rem;
        border-bottom: 1px solid var(--talena-border, #e5dfd8);
      }
      __PANEL__ .candidate-insights-subnavigation__layout { margin: 0 !important; }
      __PANEL__ .candidate-insights-view-switcher {
        display: flex; align-items: center; gap: 1.05rem; width: 100%;
        padding: 0; border: 0; border-radius: 0; background: transparent;
        overflow-x: auto; scrollbar-width: none;
      }
      __PANEL__ .candidate-insights-view-switcher::-webkit-scrollbar { display: none; }
      __PANEL__ .candidate-insights-view-option {
        position: relative; min-height: 45px; padding: 0 !important;
        border: 0 !important; border-bottom: 2px solid transparent !important;
        border-radius: 0 !important; background: transparent !important;
        color: var(--talena-text-muted, #766e68) !important;
        cursor: pointer; font: inherit; font-size: .7rem; font-weight: 550;
        line-height: 1.25; white-space: nowrap; box-shadow: none !important;
      }
      __PANEL__ .candidate-insights-view-option:hover {
        border-bottom-color: rgba(255, 111, 97, .28) !important;
        background: transparent !important; color: var(--talena-ink, #191817) !important;
      }
      __PANEL__ .candidate-insights-view-option.is-active,
      __PANEL__ .candidate-insights-view-option[aria-selected="true"] {
        border-bottom-color: var(--talena-coral, #ff6f61) !important;
        background: transparent !important;
        color: var(--talena-coral-strong, #ed7468) !important;
        font-weight: 550;
      }
      __PANEL__ .candidate-insights-subworkspace__panels { padding: 1.25rem 1.5rem 1.5rem; }
      __PANEL__ .after-interview-tab-panels { min-width: 0; }
      __PANEL__ .after-interview-tab-panel { display: grid; gap: 1rem; min-width: 0; }
      __PANEL__ .after-interview-tab-card {
        min-width: 0; padding: 1.25rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 14px; background: #fff;
      }
      __PANEL__ .after-interview-tab-card__eyebrow {
        margin-bottom: .3rem; color: var(--talena-coral, #ed7468);
        font-size: .68rem; font-weight: 750; letter-spacing: .08em; text-transform: uppercase;
      }
      __PANEL__ .after-interview-tab-card__title {
        margin: 0; color: var(--talena-ink, #191817);
        font-size: clamp(1.25rem, 2vw, 1.7rem); font-weight: 750;
        letter-spacing: -.035em; line-height: 1.1;
      }
      __PANEL__ .after-interview-tab-card__description {
        max-width: 760px; margin: .45rem 0 1rem; color: var(--talena-text-muted, #766e68);
        font-size: .78rem; line-height: 1.55;
      }
      __PANEL__ .after-interview-tab-card__body { margin: 0 !important; }
      __PANEL__ .after-interview-tab-empty {
        padding: 1rem; border: 1px dashed var(--talena-border, #e5dfd8);
        border-radius: 11px; color: var(--talena-text-muted, #766e68);
        font-size: .78rem; line-height: 1.55;
      }
      __PANEL__ [data-after-interview-blocks-source],
      __PANEL__ [data-post-interview-content].after-interview-content-source {
        display: none !important;
      }
      @media (max-width: 767px) {
        __PANEL__ .candidate-insights-subnavigation { padding: 0 1rem; }
        __PANEL__ .candidate-insights-view-switcher { gap: .9rem; }
        __PANEL__ .candidate-insights-view-option { min-height: 2.7rem; }
        __PANEL__ .candidate-insights-subworkspace__panels { padding: 1rem; }
        __PANEL__ .after-interview-tab-card { padding: 1rem; border-radius: 12px; }
      }
    `.replaceAll("__PANEL__", PANEL_SELECTOR);
    document.head.appendChild(style);
  };

  const initPanel = (panel) => {
    if (!(panel instanceof Element) || panel.dataset.afterInterviewTabsReady === "true") return;

    const card = panel.querySelector(":scope > .final-output-card");
    const header = card?.querySelector(":scope > div:first-child");
    const notesRoot = card?.querySelector("[data-interview-notes-root]");
    const postSection = card?.querySelector("[data-post-interview-section]");
    const postContent = postSection?.querySelector("[data-post-interview-content]");
    const hasPostInterviewResult =
      panel.closest("[data-final-output-root]")?.dataset.hasPostInterviewResult === "true";

    if (!card || !header || !notesRoot || !postSection) return;

    ensureStyles();
    if (hasPostInterviewResult) {
      const generatedTitle = postSection.querySelector(".insight-summary-title");
      const generatedDescription = postSection.querySelector("p.text-muted.small.mb-0");
      if (generatedTitle) generatedTitle.textContent = copy().generatedComplete;
      if (generatedDescription) {
        generatedDescription.textContent = copy().generatedCompleteDescription;
      }
    }
    panel.dataset.afterInterviewTabsReady = "true";

    const tabs = document.createElement("div");
    tabs.className = "candidate-insights-subworkspace after-interview-tabs";

    const navSection = document.createElement("section");
    navSection.className = "candidate-insights-subnavigation";

    const navLayout = document.createElement("div");
    navLayout.className = "candidate-insights-subnavigation__layout mb-4";

    const nav = document.createElement("div");
    nav.className = "candidate-insights-view-switcher";
    nav.setAttribute("role", "tablist");
    nav.setAttribute("aria-label", copy().tabs.evidence);

    navLayout.appendChild(nav);
    navSection.appendChild(navLayout);

    const tabPanels = document.createElement("div");
    tabPanels.className = "candidate-insights-subworkspace__panels";

    const keys = ["overview", "tests", "interview", "explore", "wellbeing", "evidence"];
    const buttons = new Map();
    const panels = new Map();
    keys.forEach((key) => {
      const id = "after-interview-tab-panel-" + key;
      const button = makeTab(key, copy().tabs[key], id);
      const tabPanel = makePanel(key, id);
      buttons.set(key, button);
      panels.set(key, tabPanel);
      nav.appendChild(button);
      tabPanels.appendChild(tabPanel);
    });
    tabs.append(navSection, tabPanels);
    header.insertAdjacentElement("afterend", tabs);

    const summary = postContent?.querySelector(":scope > .purpose-fit-section:first-child");
    const evidenceGrid = postContent?.querySelector(":scope > .post-evidence-grid");
    const contentChildren = postContent ? [...postContent.children] : [];
    const contradictions = contentChildren.find((node) =>
      ["Contradictions or tensions to consider", "Motsägelser eller spänningar att beakta"]
        .includes(textOf(node.querySelector?.("h3.insight-summary-title"))),
    );
    const remaining = contentChildren.find((node) =>
      ["What remains to be explored", "Vad som återstår att utforska", "Kvar att utforska"]
        .includes(textOf(node.querySelector?.("h3.insight-summary-title"))),
    );
    const contextNote = contentChildren.find((node) =>
      node.classList.contains("purpose-fit-disclaimer"),
    );

    const exploreFallback = document.createElement("div");
    [contradictions, remaining].filter(Boolean).forEach((node) => exploreFallback.appendChild(node));

    const wellbeingFallback = document.createElement("div");
    const suggestedColumn = remaining?.querySelector(".after-interview-next-steps-column");
    if (suggestedColumn) wellbeingFallback.appendChild(suggestedColumn.cloneNode(true));

    panels.get("overview").appendChild(
      makeCard(panel, "overall_picture", copy().tabs.overview, copy().descriptions.overview, summary),
    );
    panels.get("tests").appendChild(makeTestCard(panel, summary, evidenceGrid));
    panels.get("interview").appendChild(
      makeCard(panel, "interview_summary", copy().tabs.interview, copy().descriptions.interview, evidenceGrid),
    );
    panels.get("explore").appendChild(
      makeCard(panel, "explore_further", copy().tabs.explore, copy().descriptions.explore, exploreFallback.childNodes.length ? exploreFallback : null),
    );
    panels.get("wellbeing").appendChild(
      makeCard(panel, "wellbeing_tips", copy().tabs.wellbeing, copy().descriptions.wellbeing, wellbeingFallback.childNodes.length ? wellbeingFallback : null),
    );

    const evidenceCard = document.createElement("section");
    evidenceCard.className = "after-interview-tab-card after-interview-evidence-card";
    evidenceCard.append(notesRoot, postSection);
    panels.get("evidence").appendChild(evidenceCard);

    if (contextNote?.isConnected) panels.get("overview").appendChild(contextNote);
    if (postContent) {
      postContent.classList.add("after-interview-content-source");
      postContent.replaceChildren();
    }

    const activate = (key, updateUrl = true) => {
      const activeKey = panels.has(key) ? key : "evidence";
      buttons.forEach((button, buttonKey) => {
        const active = buttonKey === activeKey;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
      });
      panels.forEach((tabPanel, panelKey) => { tabPanel.hidden = panelKey !== activeKey; });
      if (updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set(URL_PARAM, activeKey);
        window.history.replaceState({}, "", url);
      }
    };

    nav.addEventListener("click", (event) => {
      const button = event.target.closest("[data-after-interview-tab]");
      if (button) activate(button.dataset.afterInterviewTab);
    });

    const requested = new URL(window.location.href).searchParams.get(URL_PARAM);
    const initial = keys.includes(requested)
      ? requested
      : hasPostInterviewResult ? "overview" : "evidence";
    activate(initial, false);
    if (window.feather) window.feather.replace();
  };

  const scan = (scope = document) => {
    if (scope instanceof Element && scope.matches(PANEL_SELECTOR)) initPanel(scope);
    scope.querySelectorAll?.(PANEL_SELECTOR).forEach(initPanel);
  };

  const start = () => {
    scan(document);
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === Node.ELEMENT_NODE) scan(node);
        });
      });
    });
    observer.observe(document.body, { childList: true, subtree: true });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();