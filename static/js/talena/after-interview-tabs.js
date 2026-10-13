(() => {
  "use strict";

  const PANEL_SELECTOR = "#candidate-insights-panel-after-interview";
  const STYLE_ID = "talena-after-interview-tabs-v1";
  const URL_PARAM = "afterTab";

  const COPY = {
    sv: {
      tabs: {
        overview: "Helhetsbild",
        interview: "Intervjusammanfattning",
        explore: "Undersök vidare",
        wellbeing: "Tips för trivsel",
        managerReport: "Chefsrapport",
        evidence: "Underlag",
      },
      descriptions: {
        overview: "En samlad bild av testresultat, intervjuunderlag och processkontext.",
        interview: "Vad intervjun bekräftar, nyanserar eller tillför till testresultaten.",
        explore: "Frågor och områden där ytterligare underlag kan ge en mer komplett bild.",
        wellbeing: "Förutsättningar och samtalspunkter som kan bidra till trivsel i rollen.",
        managerReport: "Ett samlat stöd för rekryteraren och ansvarig chef, med fokus på kandidatens resultat och relevanta frågor att följa upp.",
        evidence: "Intervjuanteckningar och svar som Talena använder som underlag.",
      },
      managerReportTitle: "Chefsrapport",
      managerReportIntro: "Chefsrapporten är ett stöd för rekryteraren och ansvarig chef. Här samlas kandidatens testresultat och sådant som kan vara värdefullt att följa upp i samtal.",
      savePdf: "Spara som PDF",
      managerSkillsTitle: "Färdighet",
      managerSkillNames: { numerical: "Numeriskt", logical: "Logiskt", verbal: "Verbalt" },
      managerSkillsUnavailable: "Färdighetsresultat visas här när de är tillgängliga.",
      managerSkillsGuideTitle: "Så tolkar du färdighetsresultaten",
      managerSkillsGuideIntro: "Resultaten visar hur kandidaten kan hantera uppgifter med olika grad av komplexitet. Se dem som ett underlag i samtalet och väg in rollens krav och övrig information.",
      managerSkillsGuideCaveat: "Resultatet säger inte ensamt hur kandidaten kommer att prestera i en viss roll.",
      managerSkillSelected: "Markerad nivå",
      managerSkillBands: [
        {
          title: "Mer tid kan behövas",
          shortDescription: "Det kan ta längre tid att lösa den här typen av uppgift.",
          description: "Det kan ta längre tid för kandidaten att lösa den här typen av uppgift. Om uppgiften är mer komplex kan den innebära en utmaning.",
          examples: [],
        },
        {
          title: "Mindre komplex",
          shortDescription: "Ofta tillräckligt för mindre komplexa arbetsuppgifter.",
          description: "Ofta tillräckligt för mindre komplexa arbetsuppgifter, vilket kan innebära:",
          examples: [
            "Följa etablerade rutiner eller instruktioner",
            "Utföra återkommande och förutsägbara aktiviteter",
            "Arbeta med konkret och tydlig information",
            "Begränsat behov av problemlösning eller beslutsfattande",
          ],
        },
        {
          title: "Relativt komplex",
          shortDescription: "Ofta tillräckligt för relativt komplexa arbetsuppgifter.",
          description: "Ofta tillräckligt för relativt komplexa arbetsuppgifter, vilket kan innebära:",
          examples: [
            "Viss grad av problemlösning eller felsökning",
            "Anpassa sig till förändrade situationer eller ny information",
            "Fatta beslut med måttliga konsekvenser",
            "Bearbeta och koppla samman flera informationsdelar",
          ],
        },
        {
          title: "Mer komplexa",
          shortDescription: "Ofta tillräckligt för mer komplexa arbetsuppgifter.",
          description: "Ofta tillräckligt för mer komplexa arbetsuppgifter, vilket kan innebära:",
          examples: [
            "Analysera abstrakt eller tvetydig information",
            "Strategiskt tänkande och planering",
            "Lösa nya eller oförutsägbara problem",
            "Fatta beslut med stora och betydande konsekvenser",
            "Snabbt lära sig och tillämpa nya koncept",
          ],
        },
      ],
      generated: "AI-genererat",
      generatedComplete: "Sammanställning genererad",
      generatedCompleteDescription: "Sammanställningen är klar och övriga flikar är nu tillgängliga.",
      unavailable: "Det här innehållet blir tillgängligt när intervjuunderlaget har sammanställts.",
    },
    en: {
      tabs: {
        overview: "Overall picture",
        interview: "Interview summary",
        explore: "Explore further",
        wellbeing: "Wellbeing tips",
        managerReport: "Manager report",
        evidence: "Evidence",
      },
      descriptions: {
        overview: "A combined view of assessment results, interview evidence and process context.",
        interview: "What the interview confirms, nuances or adds to the assessment results.",
        explore: "Questions and areas where additional evidence may create a more complete view.",
        wellbeing: "Conditions and conversation points that may support wellbeing in the role.",
        managerReport: "A practical overview for the recruiter and manager, focused on the candidate’s results and relevant topics to follow up.",
        evidence: "Interview notes and answers used by Talena as evidence.",
      },
      managerReportTitle: "Manager report",
      managerReportIntro: "The manager report is a practical resource for the recruiter and hiring manager. It brings together the candidate’s assessment results and topics that may be useful to explore in conversation.",
      savePdf: "Save as PDF",
      managerSkillsTitle: "Skills",
      managerSkillNames: { numerical: "Numerical", logical: "Logical", verbal: "Verbal" },
      managerSkillsUnavailable: "Skills results will appear here when they are available.",
      managerSkillsGuideTitle: "How to interpret the skills results",
      managerSkillsGuideIntro: "The results indicate how the candidate may handle tasks with different levels of complexity. Use them as a starting point for conversation and consider the role requirements alongside other information.",
      managerSkillsGuideCaveat: "The result alone does not determine how the candidate will perform in a specific role.",
      managerSkillSelected: "Selected level",
      managerSkillBands: [
        {
          title: "More time may be needed",
          shortDescription: "It may take longer to solve this type of task.",
          description: "It may take the candidate longer to solve this type of task. A more complex task may be challenging.",
          examples: [],
        },
        {
          title: "Less complex",
          shortDescription: "Often sufficient for less complex work tasks.",
          description: "Often sufficient for less complex work tasks, which may involve:",
          examples: [
            "Following established routines or instructions",
            "Carrying out recurring and predictable activities",
            "Working with concrete and clear information",
            "Limited need for problem-solving or decision-making",
          ],
        },
        {
          title: "Relatively complex",
          shortDescription: "Often sufficient for relatively complex work tasks.",
          description: "Often sufficient for relatively complex work tasks, which may involve:",
          examples: [
            "Some degree of problem-solving or troubleshooting",
            "Adapting to changing situations or new information",
            "Making decisions with moderate consequences",
            "Processing and connecting several pieces of information",
          ],
        },
        {
          title: "More complex",
          shortDescription: "Often sufficient for more complex work tasks.",
          description: "Often sufficient for more complex work tasks, which may involve:",
          examples: [
            "Analysing abstract or ambiguous information",
            "Strategic thinking and planning",
            "Solving new or unpredictable problems",
            "Making decisions with significant consequences",
            "Learning and applying new concepts quickly",
          ],
        },
      ],
      generated: "AI-generated",
      generatedComplete: "Compilation generated",
      generatedCompleteDescription: "The compilation is ready and the other tabs are now available.",
      unavailable: "This content becomes available when the interview evidence has been compiled.",
    },
  };

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const copy = () => (isSwedish() ? COPY.sv : COPY.en);

  const textOf = (element) =>
    (element?.textContent || "").replace(/\s+/g, " ").trim();

  const sourceBlock = (panel, key) =>
    panel.querySelector('[data-after-interview-block="' + key + '"]');

  const appendInlineMarkdown = (parent, text) => {
    const pattern = /(\*\*[^*]+?\*\*|__[^_]+?__|\*[^*]+?\*)/g;
    let cursor = 0;
    let match;
    while ((match = pattern.exec(text))) {
      if (match.index > cursor) {
        parent.appendChild(document.createTextNode(text.slice(cursor, match.index)));
      }
      const token = match[0];
      const isBold = token.startsWith("**") || token.startsWith("__");
      const element = document.createElement(isBold ? "strong" : "em");
      const value = token.slice(isBold ? 2 : 1, isBold ? -2 : -1);
      element.textContent = value;
      parent.appendChild(element);
      cursor = pattern.lastIndex;
    }
    if (cursor < text.length) {
      parent.appendChild(document.createTextNode(text.slice(cursor)));
    }
  };

  const renderGeneratedMarkdown = (container) => {
    if (container.dataset.markdownRendered === "true") return;
    const source = (container.textContent || "").replace(/\r\n?/g, "\n").trim();
    if (!source) return;

    const fragment = document.createDocumentFragment();
    const lines = source.split("\n");
    let index = 0;

    while (index < lines.length) {
      const line = lines[index].trim();
      if (!line) {
        index += 1;
        continue;
      }

      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        const level = Math.min(5, heading[1].length + 1);
        const element = document.createElement("h" + level);
        element.className = "after-interview-rich-text__heading";
        appendInlineMarkdown(element, heading[2].trim());
        fragment.appendChild(element);
        index += 1;
        continue;
      }

      const isUnordered = /^[-*•]\s+/.test(line);
      const isOrdered = /^\d+[.)]\s+/.test(line);
      if (isUnordered || isOrdered) {
        const list = document.createElement(isOrdered ? "ol" : "ul");
        list.className = "after-interview-rich-text__list";
        while (index < lines.length) {
          const item = lines[index].trim();
          const matches = isOrdered
            ? item.match(/^\d+[.)]\s+(.+)$/)
            : item.match(/^[-*•]\s+(.+)$/);
          if (!matches) break;
          const li = document.createElement("li");
          appendInlineMarkdown(li, matches[1]);
          list.appendChild(li);
          index += 1;
        }
        fragment.appendChild(list);
        continue;
      }

      const paragraphLines = [line];
      index += 1;
      while (index < lines.length && lines[index].trim()) {
        const next = lines[index].trim();
        if (/^(#{1,6})\s+/.test(next) || /^[-*•]\s+/.test(next) || /^\d+[.)]\s+/.test(next)) break;
        paragraphLines.push(next);
        index += 1;
      }
      const paragraph = document.createElement("p");
      paragraph.className = "after-interview-rich-text__paragraph";
      appendInlineMarkdown(paragraph, paragraphLines.join(" "));
      fragment.appendChild(paragraph);
    }

    container.replaceChildren(fragment);
    container.classList.add("after-interview-rich-text");
    container.dataset.markdownRendered = "true";
  };

  const sourceContent = (panel, key) => {
    const source = sourceBlock(panel, key);
    const content = source?.querySelector("[data-after-interview-block-content]") || null;
    if (!content || !content.textContent.trim()) return null;
    renderGeneratedMarkdown(content);
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
      __PANEL__ .after-interview-rich-text { color: var(--talena-ink, #191817); font-size: .9rem; line-height: 1.75; }
      __PANEL__ .after-interview-rich-text__heading { margin: 1.4rem 0 .55rem; color: var(--talena-ink, #191817); font-size: 1.05rem; font-weight: 700; letter-spacing: -.015em; line-height: 1.3; }
      __PANEL__ .after-interview-rich-text__heading:first-child { margin-top: 0; }
      __PANEL__ .after-interview-rich-text__paragraph { margin: 0 0 .85rem; }
      __PANEL__ .after-interview-rich-text__paragraph:last-child { margin-bottom: 0; }
      __PANEL__ .after-interview-rich-text__list { margin: 0 0 1rem; padding-left: 1.35rem; }
      __PANEL__ .after-interview-rich-text__list li { margin: .25rem 0; padding-left: .2rem; }
      __PANEL__ .after-interview-tab-empty {
        padding: 1rem; border: 1px dashed var(--talena-border, #e5dfd8);
        border-radius: 11px; color: var(--talena-text-muted, #766e68);
        font-size: .78rem; line-height: 1.55;
      }
      __PANEL__ [data-after-interview-blocks-source],
      __PANEL__ [data-post-interview-content].after-interview-content-source {
        display: none !important;
      }
      @media print {
        body.manager-report-printing * { visibility: hidden !important; }
        body.manager-report-printing #candidate-insights-panel-after-interview,
        body.manager-report-printing #candidate-insights-panel-after-interview * { visibility: visible !important; }
        body.manager-report-printing #candidate-insights-panel-after-interview .candidate-insights-subnavigation { display: none !important; }
        body.manager-report-printing .after-interview-tab-panel:not([data-after-interview-tab-panel="managerReport"]) { display: none !important; }
        body.manager-report-printing .after-interview-tab-panel[data-after-interview-tab-panel="managerReport"] { display: block !important; position: absolute; inset: 0; width: 100%; }
        body.manager-report-printing .after-interview-manager-report__actions { display: none !important; }
        body.manager-report-printing .after-interview-manager-report__guide { display: block; }
        body.manager-report-printing .after-interview-manager-report__guide > * { display: block !important; }
        body.manager-report-printing .after-interview-manager-report { border: 0 !important; padding: 0 !important; }
      }
      __PANEL__ .after-interview-manager-report__header {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
      }
      __PANEL__ .after-interview-manager-report__actions { flex: 0 0 auto; }
      __PANEL__ .after-interview-manager-report__skills { margin-top: 1.6rem; }
      __PANEL__ .after-interview-manager-report__skills-title {
        margin: 0 0 .85rem; color: var(--talena-ink, #191817); font-size: 1.25rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__skill { margin: 0 0 1.5rem; }
      __PANEL__ .after-interview-manager-report__skill-title {
        margin: 0 0 .7rem; color: var(--talena-ink, #191817); font-size: 1rem; font-weight: 700;
      }
      __PANEL__ .after-interview-manager-report__levels {
        display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .75rem;
      }
      __PANEL__ .after-interview-manager-report__level {
        position: relative; min-width: 0; min-height: 145px; padding: 1rem;
        overflow: hidden; border: 1px solid var(--talena-border, #e5dfd8); border-radius: 12px;
        background: #fff; color: var(--talena-ink, #191817);
        transition: border-color .16s ease, background-color .16s ease, box-shadow .16s ease;
      }
      __PANEL__ .after-interview-manager-report__level::before {
        display: block; width: 30px; height: 6px; margin-bottom: .8rem;
        border-radius: 99px; background: #e8e2dd; content: "";
      }
      __PANEL__ .after-interview-manager-report__level-title {
        margin: 0 1.4rem .45rem 0; font-size: .9rem; font-weight: 750; line-height: 1.3;
      }
      __PANEL__ .after-interview-manager-report__level-description {
        margin: 0; color: #777b84; font-size: .76rem; line-height: 1.5;
      }
      __PANEL__ .after-interview-manager-report__level--selected {
        border-color: var(--talena-coral, #ff6f61);
        background: #fff4f1;
        box-shadow: 0 0 0 1px var(--talena-coral, #ff6f61);
      }
      __PANEL__ .after-interview-manager-report__skill {
        --skill-accent: var(--talena-coral, #ff6f61);
      }
      __PANEL__ .after-interview-manager-report__skill .after-interview-manager-report__level--selected::before {
        background: var(--talena-coral, #ff6f61);
      }
      __PANEL__ .after-interview-manager-report__level-check {
        position: absolute; top: .72rem; right: .78rem; display: grid; place-items: center;
        width: 22px; height: 22px; border-radius: 50%; background: var(--skill-accent);
        color: #fff; font-size: .8rem; font-weight: 800; line-height: 1;
      }
      __PANEL__ .after-interview-manager-report__guide {
        margin-top: 1.6rem; padding: 1.1rem 1.2rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 13px; background: #fff;
        transition: border-color .16s ease, background-color .16s ease;
      }
      __PANEL__ .after-interview-manager-report__guide[open] {
        border-color: var(--talena-border, #e5dfd8); background: #fff;
      }
      __PANEL__ .after-interview-manager-report__guide-summary {
        display: flex; align-items: center; justify-content: space-between; gap: 1rem;
        list-style: none; cursor: pointer; color: var(--talena-ink, #191817); font-weight: 700;
      }
      __PANEL__ .after-interview-manager-report__guide-summary::-webkit-details-marker { display: none; }
      __PANEL__ .after-interview-manager-report__guide-summary::marker { content: ""; }
      __PANEL__ .after-interview-manager-report__guide-summary::after {
        flex: 0 0 auto; width: .62rem; height: .62rem; margin-right: .2rem;
        border-right: 2px solid var(--talena-coral-strong, #ed7468);
        border-bottom: 2px solid var(--talena-coral-strong, #ed7468);
        content: ""; transform: rotate(45deg) translateY(-2px);
        transition: transform .16s ease;
      }
      __PANEL__ .after-interview-manager-report__guide[open] .after-interview-manager-report__guide-summary::after {
        transform: rotate(225deg) translate(-2px, -1px);
      }
      __PANEL__ .after-interview-manager-report__guide-summary:focus-visible {
        outline: 2px solid var(--talena-coral, #ff6f61); outline-offset: 4px; border-radius: 3px;
      }
      __PANEL__ .after-interview-manager-report__guide-intro {
        max-width: 860px; margin: .8rem 0 0; color: var(--talena-text-muted, #766e68);
        font-size: .82rem; line-height: 1.6;
      }
      __PANEL__ .after-interview-manager-report__guide-levels {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .8rem; margin-top: 1rem;
      }
      __PANEL__ .after-interview-manager-report__guide-level {
        padding: .9rem; border-radius: 10px; background: #fff;
      }
      __PANEL__ .after-interview-manager-report__guide-level h5 {
        margin: 0 0 .4rem; font-size: .82rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__guide-level p {
        margin: 0; color: var(--talena-text-muted, #766e68); font-size: .75rem; line-height: 1.5;
      }
      __PANEL__ .after-interview-manager-report__guide-level ul {
        margin: .45rem 0 0; padding-left: 1.1rem; color: var(--talena-text-muted, #766e68);
        font-size: .74rem; line-height: 1.5;
      }
      __PANEL__ .after-interview-manager-report__guide-caveat {
        margin: 1rem 0 0; padding-top: .8rem; border-top: 1px solid var(--talena-border, #e5dfd8);
        color: var(--talena-text-muted, #766e68); font-size: .74rem; line-height: 1.5;
      }
      __PANEL__ .after-interview-manager-report__skills-empty {
        margin: 0; padding: 1rem; border: 1px dashed var(--talena-border, #e5dfd8);
        border-radius: 11px; color: var(--talena-text-muted, #766e68); font-size: .8rem;
      }
      __PANEL__ .after-interview-manager-report__intro {
        max-width: 760px; margin: .65rem 0 0; color: var(--talena-text-muted, #766e68); font-size: .9rem; line-height: 1.65;
      }
      __PANEL__ .after-interview-manager-report .after-interview-tab-card__title {
        font-size: clamp(1.15rem, 1.8vw, 1.55rem);
      }
      __PANEL__ .after-interview-manager-report__intro { font-size: .84rem; }
      __PANEL__ .after-interview-manager-report__skills-title { font-size: 1.15rem; }
      __PANEL__ .after-interview-manager-report__skill-title { font-size: .95rem; }
      __PANEL__ .after-interview-manager-report__level-title { font-size: .84rem; }
      __PANEL__ .after-interview-manager-report__level-description { font-size: .72rem; }
      __PANEL__ .after-interview-manager-report__level-check { font-size: .76rem; }
      __PANEL__ .after-interview-manager-report__guide-summary { font-size: .9rem; }
      __PANEL__ .after-interview-manager-report__guide-intro { font-size: .78rem; }
      __PANEL__ .after-interview-manager-report__guide-level h5 { font-size: .78rem; }
      __PANEL__ .after-interview-manager-report__guide-level p { font-size: .71rem; }
      __PANEL__ .after-interview-manager-report__guide-level ul { font-size: .70rem; }
      __PANEL__ .after-interview-manager-report__guide-caveat { font-size: .70rem; }
      __PANEL__ .after-interview-manager-report__skills-empty { font-size: .76rem; }
      __PANEL__ .after-interview-manager-report__actions .btn { font-size: .84rem; }
      @media (max-width: 1050px) {
        __PANEL__ .after-interview-manager-report__levels { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }
      @media (max-width: 720px) {
        __PANEL__ .after-interview-manager-report__guide-levels { grid-template-columns: 1fr; }
      }
      @media (max-width: 575px) {
        __PANEL__ .after-interview-manager-report__header { flex-direction: column; }
        __PANEL__ .after-interview-manager-report__levels { grid-template-columns: 1fr; }
        __PANEL__ .after-interview-manager-report__level { min-height: 0; }
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

    const keys = ["overview", "interview", "explore", "wellbeing", "managerReport", "evidence"];
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
    panels.get("interview").appendChild(
      makeCard(panel, "interview_summary", copy().tabs.interview, copy().descriptions.interview, evidenceGrid),
    );
    panels.get("explore").appendChild(
      makeCard(panel, "explore_further", copy().tabs.explore, copy().descriptions.explore, exploreFallback.childNodes.length ? exploreFallback : null),
    );
    panels.get("wellbeing").appendChild(
      makeCard(panel, "wellbeing_tips", copy().tabs.wellbeing, copy().descriptions.wellbeing, wellbeingFallback.childNodes.length ? wellbeingFallback : null),
    );

    const managerReportCard = document.createElement("section");
    managerReportCard.className = "after-interview-tab-card after-interview-manager-report";
    const managerReportHeader = document.createElement("div");
    managerReportHeader.className = "after-interview-manager-report__header";
    const managerReportHeading = document.createElement("h3");
    managerReportHeading.className = "after-interview-tab-card__title";
    managerReportHeading.textContent = copy().managerReportTitle;
    const managerReportActions = document.createElement("div");
    managerReportActions.className = "after-interview-manager-report__actions";
    const pdfButton = document.createElement("button");
    pdfButton.type = "button";
    pdfButton.className = "btn btn-outline-primary d-inline-flex align-items-center gap-2";
    pdfButton.setAttribute("aria-label", copy().savePdf);
    const pdfIcon = document.createElement("i");
    pdfIcon.setAttribute("data-feather", "download");
    const pdfLabel = document.createElement("span");
    pdfLabel.textContent = copy().savePdf;
    pdfButton.append(pdfIcon, pdfLabel);
    pdfButton.addEventListener("click", () => {
      const originalTitle = document.title;
      const cleanup = () => {
        document.body.classList.remove("manager-report-printing");
        document.title = originalTitle;
      };
      document.title = copy().managerReportTitle;
      document.body.classList.add("manager-report-printing");
      window.addEventListener("afterprint", cleanup, { once: true });
      window.print();
      window.setTimeout(cleanup, 1000);
    });
    managerReportActions.appendChild(pdfButton);
    managerReportHeader.append(managerReportHeading, managerReportActions);
    const managerReportIntro = document.createElement("p");
    managerReportIntro.className = "after-interview-manager-report__intro";
    managerReportIntro.textContent = copy().managerReportIntro;
    managerReportCard.append(managerReportHeader, managerReportIntro);

    const managerSkills = document.createElement("section");
    managerSkills.className = "after-interview-manager-report__skills";
    const managerSkillsTitle = document.createElement("h4");
    managerSkillsTitle.className = "after-interview-manager-report__skills-title";
    managerSkillsTitle.textContent = copy().managerSkillsTitle;
    managerSkills.appendChild(managerSkillsTitle);

    const workspace = panel.closest("[data-candidate-insights-workspace]");
    const skillNodes = [
      ...(workspace?.querySelectorAll(
        '#candidate-insights-panel-cognitive [data-manager-skill-key][data-manager-skill-result]'
      ) || []),
    ];
    const completedSkills = new Map();
    skillNodes.forEach((node) => {
      const key = node.dataset.managerSkillKey;
      const percentile = Number(node.dataset.managerSkillResult);
      if (["numerical", "logical", "verbal"].includes(key)
        && Number.isFinite(percentile) && percentile >= 1 && percentile <= 99) {
        completedSkills.set(key, percentile);
      }
    });

    const skillLabels = copy().managerSkillNames;
    const skillOrder = ["numerical", "logical", "verbal"];
    skillOrder.forEach((key) => {
      const percentile = completedSkills.get(key);
      if (percentile === undefined) return;

      const selectedBandIndex = percentile <= 20 ? 0
        : percentile <= 40 ? 1
        : percentile <= 60 ? 2
        : 3;
      const skill = document.createElement("section");
      skill.className = "after-interview-manager-report__skill";
      skill.dataset.skillKey = key;
      const heading = document.createElement("h5");
      heading.className = "after-interview-manager-report__skill-title";
      heading.textContent = skillLabels[key];
      skill.appendChild(heading);

      const levels = document.createElement("div");
      levels.className = "after-interview-manager-report__levels";
      levels.setAttribute("role", "list");
      copy().managerSkillBands.forEach((band, index) => {
        const selected = index === selectedBandIndex;
        const level = document.createElement("article");
        level.className = "after-interview-manager-report__level";
        level.setAttribute("role", "listitem");
        if (selected) {
          level.classList.add("after-interview-manager-report__level--selected");
          level.setAttribute("aria-current", "true");
          level.setAttribute("aria-label", band.title + " · " + copy().managerSkillSelected);
        } else {
          level.setAttribute("aria-current", "false");
        }
        const title = document.createElement("h6");
        title.className = "after-interview-manager-report__level-title";
        title.textContent = band.title;
        const description = document.createElement("p");
        description.className = "after-interview-manager-report__level-description";
        description.textContent = band.shortDescription;
        level.append(title, description);
        if (selected) {
          const check = document.createElement("span");
          check.className = "after-interview-manager-report__level-check";
          check.setAttribute("aria-hidden", "true");
          check.textContent = "✓";
          level.appendChild(check);
        }
        levels.appendChild(level);
      });
      skill.appendChild(levels);
      managerSkills.appendChild(skill);
    });

    if (!completedSkills.size) {
      const empty = document.createElement("p");
      empty.className = "after-interview-manager-report__skills-empty";
      empty.textContent = copy().managerSkillsUnavailable;
      managerSkills.appendChild(empty);
    }

    const guide = document.createElement("details");
    guide.className = "after-interview-manager-report__guide";
    const guideSummary = document.createElement("summary");
    guideSummary.className = "after-interview-manager-report__guide-summary";
    guideSummary.textContent = copy().managerSkillsGuideTitle;
    const guideContent = document.createElement("div");
    guideContent.className = "after-interview-manager-report__guide-content";
    const guideIntro = document.createElement("p");
    guideIntro.className = "after-interview-manager-report__guide-intro";
    guideIntro.textContent = copy().managerSkillsGuideIntro;
    const guideLevels = document.createElement("div");
    guideLevels.className = "after-interview-manager-report__guide-levels";
    copy().managerSkillBands.forEach((band) => {
      const level = document.createElement("section");
      level.className = "after-interview-manager-report__guide-level";
      const title = document.createElement("h5");
      title.textContent = band.title;
      const description = document.createElement("p");
      description.textContent = band.description;
      level.append(title, description);
      if (band.examples.length) {
        const list = document.createElement("ul");
        band.examples.forEach((example) => {
          const item = document.createElement("li");
          item.textContent = example;
          list.appendChild(item);
        });
        level.appendChild(list);
      }
      guideLevels.appendChild(level);
    });
    const guideCaveat = document.createElement("p");
    guideCaveat.className = "after-interview-manager-report__guide-caveat";
    guideCaveat.textContent = copy().managerSkillsGuideCaveat;
    guideContent.append(guideIntro, guideLevels, guideCaveat);
    guide.append(guideSummary, guideContent);
    managerSkills.appendChild(guide);
    managerReportCard.appendChild(managerSkills);
    panels.get("managerReport").appendChild(managerReportCard);

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

    const url = new URL(window.location.href);
    const requested = url.searchParams.get(URL_PARAM);
    const initial = keys.includes(requested)
      ? requested
      : hasPostInterviewResult ? "overview" : "evidence";
    activate(initial, false);
    if (requested === "tests" || url.searchParams.has("afterTestTab")) {
      url.searchParams.delete("afterTestTab");
      url.searchParams.set(URL_PARAM, initial);
      window.history.replaceState({}, "", url);
    }
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