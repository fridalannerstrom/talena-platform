(() => {
  "use strict";

  const PANEL_SELECTOR = "#candidate-insights-panel-after-interview";
  const STYLE_ID = "talena-after-interview-tabs-v1";
  const URL_PARAM = "afterTab";
  let lastRenderedCandidate = null;
  let lastRenderedCompiled = null;

  const COPY = {
    sv: {
      tabs: {
        reports: "Rapporter",
        overview: "Helhetsbild",
        interview: "Intervjusammanfattning",
        explore: "Undersök vidare",
        managerReport: "Chefsrapport",
        evidence: "Underlag",
      },
      descriptions: {
        overview: "En samlad bild av testresultat, intervjuunderlag och rollkontext.",
        interview: "Vad intervjun bekräftar, nyanserar eller tillför till testresultaten.",
        explore: "Frågor och områden där ytterligare underlag kan ge en mer komplett bild.",
        managerReport: "Ett samlat stöd för rekryteraren och ansvarig chef, med fokus på kandidatens resultat och relevanta frågor att följa upp.",
        evidence: "Intervjuanteckningar och svar som Talena använder som underlag.",
      },
      managerReportTitle: "Chefsrapport",
      managerReportIntro: "Här samlas tillgängliga testresultat tillsammans med personens egna perspektiv och konkreta tips för att förstå och använda insikterna i praktiken.",
      savePdf: "Spara som PDF",
      creatingPdf: "Skapar PDF…",
      pdfGenerationFailed: "PDF:en kunde inte skapas. Försök igen.",
      managerSkillsTitle: "Färdighet",
      managerMotivationTitle: "Motivation",
      managerMotivationPracticalTitle: "Led i praktiken",
      managerMotivationDoTitle: "Gör så här",
      managerMotivationAvoidTitle: "Undvik det här",
      managerMotivationUnavailable: "Motivationsresultat visas här när de är tillgängliga.",
      generateSection: "Generera",
      regenerateSection: "Generera igen",
      generateManagerReport: "Generera chefsrapport",
      regenerateManagerReport: "Generera chefsrapport igen",
      generatingManagerReport: "Skapar chefsrapport...",
      sectionGenerationFailed: "Det gick inte att generera innehållet. Försök igen.",
      managerPersonalityTitle: "Personlighet",
      managerPersonalityThemes: [
        { key: "leading_and_working_with_others", title: "Leda och arbeta med andra" },
        { key: "organising_and_thinking_patterns", title: "Organisering och tankemönster" },
        { key: "interaction_and_emotion_management", title: "Interaktion och känslohantering" }
      ],
      managerPersonalityTestbild: "Testbild",
      managerPersonalityCandidateDescribes: "Kandidaten beskriver",
      managerPersonalityAdviceTitle: "Tips för trivsel",
      managerPersonalityTestMissing: "Ingen testtolkning är tillgänglig ännu.",
      managerPersonalityInterviewMissing: "Inga intervjuanteckningar är tillgängliga ännu.",
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
      editText: "Redigera text",
      editDialogTitle: "Redigera text i chefsrapporten",
      editHelp: "Textändringen gäller bara rapporten och ändrar inte testresultat eller testvärden.",
      saveEdit: "Spara",
      cancelEdit: "Avbryt",
      restoreAiText: "Återställ AI-text",
      confirmRestoreAiText: "Ta bort den manuella ändringen och visa den senaste AI-texten igen?",
      manuallyEdited: "Manuellt redigerad",
      editSaved: "Texten har sparats.",
      loadingReportEdits: "Hämtar sparade rapportändringar…",
      reportEditsLoadFailed: "Kunde inte hämta sparade rapportändringar. Rapporten visas inte förrän den sparade texten har lästs in.",
      retryReportEdits: "Försök igen",
      editSaveFailed: "Det gick inte att spara ändringen. Försök igen.",
      editRestoreFailed: "Det gick inte att återställa AI-texten. Försök igen.",
      editVersionConflict: "Texten har ändrats i en annan session. Stäng och öppna redigeraren igen.",
      confirmRegenerationTitle: "Uppdatera AI-texten?",
      confirmRegenerationBody: "AI-texten genereras på nytt. Dina manuella ändringar sparas och fortsätter visas i chefsrapporten.",
      confirmRegenerationNote: "Du kan visa den nya AI-texten senare genom att välja Återställ AI-text i redigeraren.",
      confirmRegenerationCancel: "Avbryt",
      confirmRegenerationContinue: "Fortsätt",
      generatedComplete: "Sammanställning genererad",
      generatedCompleteDescription: "Sammanställningen är klar. Du hittar resultat och rapporter under Rapporter.",
      unavailable: "Det här innehållet blir tillgängligt när intervjuunderlaget har sammanställts.",
      lockedTabsHint: "De andra flikarna öppnas när du väljer Sammanställ underlag.",
      journeyTitle: "Så fungerar Efter intervju",
      journeySteps: [
        { title: "Samla underlag", description: "Lägg till anteckningar och sparade intervjusvar." },
        { title: "Sammanställ", description: "Talena väger samman intervju, tester och rollkontext." },
        { title: "Använd resultatet", description: "Utforska helhetsbilden och ta fram en chefsrapport." },
      ],
      evidenceKicker: "STEG 1 · UNDERLAG",
      evidenceHeading: "Börja med det som kom fram i intervjun",
      evidenceHeadingReady: "Komplettera ditt intervjuunderlag",
      evidenceLead: "Testresultat och rollkontext finns redan i Talena. Lägg till exempel, svar och observationer från samtalet här.",
      evidenceLeadReady: "Du kan komplettera eller ändra anteckningarna här. Sammanställ på nytt för att uppdatera analysen och rapporterna.",
      evidenceTip: "Tips: Beskriv konkreta situationer, vad kandidaten gjorde och vad som hände. Svar som sparats på intervjufrågorna följer med automatiskt.",
      reportsIntro: "Här hittar du de sammanställda resultaten och rapporterna. Underlaget kan alltid kompletteras i fliken Underlag.",
      reportStatusOutdated: "Underlaget har ändrats sedan rapporterna skapades.",
      reportStatusUnsaved: "Du har osparade intervjuanteckningar. Skapa en ny sammanställning för att uppdatera rapporterna.",
      reportStatusDetail: "Rapporterna visar fortfarande den tidigare versionen tills du skapar en ny sammanställning.",
      reportRebuild: "Skapa ny sammanställning",
      reportRebuildShort: "Uppdatera rapporterna",
      reportGenerateUnavailable: "Lägg till och spara intervjuunderlag för att skapa rapporter.",
      reportGenerating: "Sammanställer…",
      reportError: "Det gick inte att uppdatera rapporterna. Försök igen.",
      reportOverviewTitle: "Dina rapporter",
      evidenceRebuildHint: "Du kan alltid skapa en ny sammanställning om intervjuunderlaget har förändrats.",
    },
    en: {
      tabs: {
        reports: "Reports",
        overview: "Overall picture",
        interview: "Interview summary",
        explore: "Explore further",
        managerReport: "Manager report",
        evidence: "Evidence",
      },
      descriptions: {
        overview: "A combined view of assessment results, interview evidence and role context.",
        interview: "What the interview confirms, nuances or adds to the assessment results.",
        explore: "Questions and areas where additional evidence may create a more complete view.",
        managerReport: "A practical overview for the recruiter and manager, focused on the candidate’s results and relevant topics to follow up.",
        evidence: "Interview notes and answers used by Talena as evidence.",
      },
      managerReportTitle: "Manager report",
      managerReportIntro: "This report brings together available assessment results, the person's own perspectives and practical tips for understanding and applying the insights.",
      savePdf: "Save as PDF",
      creatingPdf: "Creating PDF…",
      pdfGenerationFailed: "The PDF could not be created. Please try again.",
      managerSkillsTitle: "Skills",
      managerMotivationTitle: "Motivation",
      managerMotivationPracticalTitle: "In practice",
      managerMotivationDoTitle: "Do this",
      managerMotivationAvoidTitle: "Avoid this",
      managerMotivationUnavailable: "Motivation results will appear here when they are available.",
      generateSection: "Generate",
      regenerateSection: "Generate again",
      generateManagerReport: "Generate manager report",
      regenerateManagerReport: "Generate manager report again",
      generatingManagerReport: "Creating manager report...",
      sectionGenerationFailed: "The content could not be generated. Please try again.",
      managerPersonalityTitle: "Personality",
      managerPersonalityThemes: [
        { key: "leading_and_working_with_others", title: "Leading and working with others" },
        { key: "organising_and_thinking_patterns", title: "Organising and thinking patterns" },
        { key: "interaction_and_emotion_management", title: "Interaction and emotional management" }
      ],
      managerPersonalityTestbild: "Test profile",
      managerPersonalityCandidateDescribes: "The candidate describes",
      managerPersonalityAdviceTitle: "Wellbeing tips",
      managerPersonalityTestMissing: "No test interpretation is available yet.",
      managerPersonalityInterviewMissing: "No interview notes are available yet.",
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
      editText: "Edit text",
      editDialogTitle: "Edit manager report text",
      editHelp: "This change applies only to the report. It does not change assessment results or test values.",
      saveEdit: "Save",
      cancelEdit: "Cancel",
      restoreAiText: "Restore AI text",
      confirmRestoreAiText: "Remove the manual edit and show the latest AI text again?",
      manuallyEdited: "Manually edited",
      editSaved: "Text saved.",
      loadingReportEdits: "Loading saved report edits…",
      reportEditsLoadFailed: "Saved report edits could not be loaded. The report will remain hidden until its saved text has been loaded.",
      retryReportEdits: "Try again",
      editSaveFailed: "The change could not be saved. Please try again.",
      editRestoreFailed: "The AI text could not be restored. Please try again.",
      editVersionConflict: "This text changed in another session. Close and reopen the editor.",
      confirmRegenerationTitle: "Update the AI text?",
      confirmRegenerationBody: "The AI text will be generated again. Your manual edits will remain saved and visible in the manager report.",
      confirmRegenerationNote: "You can view the new AI text later by choosing Restore AI text in the editor.",
      confirmRegenerationCancel: "Cancel",
      confirmRegenerationContinue: "Continue",
      generatedComplete: "Compilation generated",
      generatedCompleteDescription: "The compilation is ready. Open Reports to explore the results.",
      unavailable: "This content becomes available when the interview evidence has been compiled.",
      lockedTabsHint: "The other tabs unlock when you select Compile evidence.",
      journeyTitle: "How After interview works",
      journeySteps: [
        { title: "Collect evidence", description: "Add notes and saved interview answers." },
        { title: "Compile", description: "Talena combines the interview, tests and role context." },
        { title: "Use the results", description: "Explore the overall picture and prepare a manager report." },
      ],
      evidenceKicker: "STEP 1 · EVIDENCE",
      evidenceHeading: "Start with what you learned in the interview",
      evidenceHeadingReady: "Update your interview evidence",
      evidenceLead: "Talena already has the assessment results and role context. Add examples, answers and observations from the conversation here.",
      evidenceLeadReady: "Add or change notes here, then compile again to update the analysis and reports.",
      evidenceTip: "Tip: Describe specific situations, what the candidate did and what happened. Answers saved on interview questions are included automatically.",
      reportsIntro: "Find all compiled results and reports here. You can always update the evidence in the Evidence tab.",
      reportStatusOutdated: "The evidence has changed since these reports were created.",
      reportStatusUnsaved: "You have unsaved interview notes. Create a new compilation to update the reports.",
      reportStatusDetail: "The reports still show the previous version until you create a new compilation.",
      reportRebuild: "Create new compilation",
      reportRebuildShort: "Update reports",
      reportGenerateUnavailable: "Add and save interview evidence to generate reports.",
      reportGenerating: "Compiling…",
      reportError: "Could not update the reports. Please try again.",
      reportOverviewTitle: "Your reports",
      evidenceRebuildHint: "Create a new compilation whenever the interview evidence changes.",
    },
  };

  // #182: use the same branded cover and shared PDF engine as team reports.
  const buildManagerReportCover = (root) => {
    const values = root?.dataset || {};
    const primary = /^#[\da-f]{6}$/i.test(values.managerReportBrandPrimary || "")
      ? values.managerReportBrandPrimary : "#FF6F61";
    const cover = document.createElement("div");
    cover.className = "talena-team-pdf-cover";
    cover.style.setProperty("--team-pdf-primary", primary);
    const focus = Number(values.managerReportBrandFocus);
    cover.style.backgroundPosition = "center " +
      (Number.isFinite(focus) ? Math.max(0, Math.min(100, focus)) : 50) + "%";
    const imageUrl = values.managerReportBrandCover || "";
    if (imageUrl) {
      cover.style.backgroundImage =
        'linear-gradient(180deg,rgba(0,0,0,.15),rgba(0,0,0,.72)),url("' +
        imageUrl.replace(/"/g, "%22") + '")';
    }
    const header = document.createElement("div");
    header.className = "talena-team-pdf-cover-brand";
    const logo = values.managerReportBrandLogo || "";
    if (logo) {
      const img = document.createElement("img");
      img.src = logo;
      img.alt = "";
      header.appendChild(img); // A transparent PNG keeps its actual alpha channel.
    } else {
      header.classList.add("talena-team-pdf-cover-brand-fallback");
      header.textContent = values.managerReportBrandCompany || "Talena";
    }
    const bottom = document.createElement("div");
    bottom.className = "talena-team-pdf-cover-title";
    const accent = document.createElement("div");
    accent.className = "talena-team-pdf-cover-line";
    const kicker = document.createElement("p");
    kicker.className = "talena-team-pdf-cover-kicker";
    kicker.textContent = copy().managerReportTitle;
    const title = document.createElement("h1");
    title.textContent = copy().managerReportTitle;
    const company = document.createElement("p");
    company.textContent = values.managerReportBrandCompany || "Talena";
    bottom.append(accent, kicker, title, company);
    cover.append(header, bottom);
    return cover;
  };

  const renderElementAsPdf = async (element, filename, root) => {
    if (!window.TalenaPdfExport?.exportSections) {
      throw new Error("Shared PDF exporter unavailable.");
    }
    const values = root?.dataset || {};
    const primary = /^#[\da-f]{6}$/i.test(values.managerReportBrandPrimary || "")
      ? values.managerReportBrandPrimary : "#FF6F61";
    const dark = /^#[\da-f]{6}$/i.test(values.managerReportBrandDark || "")
      ? values.managerReportBrandDark : primary;
    const light = /^#[\da-f]{6}$/i.test(values.managerReportBrandLight || "")
      ? values.managerReportBrandLight : "#FFF0ED";
    // PDF-only color overrides: never alter the live manager report.
    element.style.setProperty("--talena-coral", primary);
    element.style.setProperty("--talena-coral-strong", dark);
    element.style.setProperty("--talena-coral-soft", light);
    element.style.borderTop = "6px solid " + primary;
    element.querySelectorAll(
      ".after-interview-tab-card__title, .after-interview-manager-report__skills-title, " +
      ".after-interview-manager-report__motivation-title, " +
      ".after-interview-manager-report__personality-title"
    ).forEach((heading) => { heading.style.color = dark; });
    const cover = buildManagerReportCover(root);
    element.parentElement.insertBefore(cover, element);
    await window.TalenaPdfExport.exportSections(
      [{ node: cover, cover: true }, { node: element, continuous: true }],
      {
        title: copy().managerReportTitle,
        subject: copy().managerReportTitle,
        filename,
      }
    );
  };

  // The same canonical MQ library feeds both this UI and AI's prompt.
  // Read at render time, because candidate fragments refresh over AJAX.
  const getMotivationPracticalAdvice = (panel) => {
    const source = panel.closest("[data-final-output-root]")?.querySelector(
      "#talena-motivation-practical-advice"
    );
    if (!source) return { sv: {}, en: {} };
    try {
      return JSON.parse(source.textContent || "{}");
    } catch (_) {
      return { sv: {}, en: {} };
    }
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
    container.dataset.markdownSource = source;

    const fragment = document.createDocumentFragment();
    const lines = source.split("\n");
    let index = 0;

    // A report already has a heading. AI content can begin with the exact
    // same title, creating two titles and duplicate AI tags. Suppress only
    // that first displayed heading, never change saved/edited source text.
    const blockKey = container.dataset.afterInterviewSourceBlock
      || container.dataset.afterInterviewBlockContent
      || container.dataset.managerReportEditKey
      || container.closest?.("[data-after-interview-block]")?.dataset?.afterInterviewBlock
      || (container.classList.contains("after-interview-manager-report__personality-advice-text")
        ? "wellbeing_tips" : "");
    const duplicateHeadingLabels = {
      overall_picture: [copy().tabs.overview, "Helhetsbild", "Overall picture"],
      interview_summary: [copy().tabs.interview, "Intervjusammanfattning", "Interview summary"],
      explore_further: [copy().tabs.explore, "Undersök vidare", "Explore further", "Investigate further"],
      wellbeing_tips: [copy().managerPersonalityAdviceTitle, "Tips för trivsel", "Wellbeing tips", "For the manager"],
    };
    const isDuplicateBlockHeading = (line) => {
      const heading = line.replace(/^#{1,6}\s+/, "").trim();
      const unwrapped = heading.replace(/^(?:\*\*|__)(.*?)(?:\*\*|__)$/, "$1").trim();
      const normalized = (value) => value.replace(/:$/, "").trim().toLocaleLowerCase("sv-SE");
      return (duplicateHeadingLabels[blockKey] || [])
        .some((label) => normalized(label) === normalized(unwrapped));
    };
    let firstContentLine = true;

    while (index < lines.length) {
      const line = lines[index].trim();
      if (!line) {
        index += 1;
        continue;
      }
      if (firstContentLine && isDuplicateBlockHeading(line)) {
        index += 1;
        firstContentLine = false;
        continue;
      }
      firstContentLine = false;

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
          if (!matches) {
            // AI Markdown frequently places a blank line between numbered
            // items (sometimes writing "1." for every item). Keep those
            // entries in ONE <ol> so the browser numbers them 1, 2, 3...
            // instead of starting a fresh list at 1 after each blank line.
            if (!item) {
              let nextIndex = index;
              while (nextIndex < lines.length && !lines[nextIndex].trim()) {
                nextIndex += 1;
              }
              const next = lines[nextIndex]?.trim() || "";
              const nextIsListItem = isOrdered
                ? /^\d+[.)]\s+/.test(next)
                : /^[-*•]\s+/.test(next);
              if (nextIsListItem) {
                index = nextIndex;
                continue;
              }
            }
            break;
          }
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
    content.dataset.afterInterviewSourceBlock = key;
    renderGeneratedMarkdown(content);
    return content;
  };

  const makeCard = (panel, key, title, description, fallback, blockKey = null) => {
    const card = document.createElement("section");
    card.className = "after-interview-tab-card";
    const header = document.createElement("div");
    header.className = "after-interview-tab-card__header";

    const toolbar = document.createElement("div");
    toolbar.className = "after-interview-tab-card__toolbar";
    const heading = document.createElement("h3");
    heading.className = "after-interview-tab-card__title";
    heading.textContent = title;
    toolbar.appendChild(heading);

    const intro = document.createElement("p");
    intro.className = "after-interview-tab-card__description";
    intro.textContent = description;

    // #363: source-verified tag is attached only when this AI block has text.
    header.append(toolbar, intro);
    card.appendChild(header);

    const supplied = blockKey ? sourceContent(panel, blockKey) : null;
    const body = supplied || fallback || document.createElement("div");
    body.classList.add("after-interview-tab-card__body");
    if (blockKey) {
      body.dataset.afterInterviewBlockContent = blockKey;
      if (supplied) body.dataset.afterInterviewAiOrigin = "true";
      if (!supplied && !fallback) {
        body.classList.add("after-interview-tab-empty");
        body.textContent = copy().unavailable;
      }
      const error = document.createElement("div");
      error.className = "alert alert-danger d-none mt-3 mb-0";
      error.dataset.afterInterviewBlockError = blockKey;
      card.append(body, error);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "btn btn-icon btn-light after-interview-tab-card__regenerate";
      const actionLabel = body.textContent?.trim()
        ? copy().regenerateSection
        : copy().generateSection;
      button.title = actionLabel;
      button.setAttribute("aria-label", actionLabel);
      button.dataset.afterInterviewRegenerate = blockKey;
      button.innerHTML = '<i data-feather="refresh-cw"></i>';
      toolbar.appendChild(button);
      button.addEventListener("click", () => generateContentBlock(panel, blockKey, body, error, button));
    } else {
      card.appendChild(body);
    }
    return card;
  };

  const csrfToken = () => {
    const cookie = document.cookie.split("; ").find((item) => item.startsWith("csrftoken="));
    return cookie ? decodeURIComponent(cookie.slice("csrftoken=".length)) : "";
  };

  const createManagerReportEditController = (panel, root, workspace) => {
    const state = {
      loadUrl: root?.dataset.managerReportEditsUrl || "",
      saveUrl: root?.dataset.managerReportEditSaveUrl || "",
      language: "",
      edits: new Map(),
      bindings: new Map(),
      ready: false,
      statusElement: null,
      dialog: null,
      managerReportGenerating: false,
    };

    const announce = (message) => {
      if (!state.statusElement) return;
      state.statusElement.textContent = message;
      window.clearTimeout(state.statusTimer);
      state.statusTimer = window.setTimeout(() => {
        if (state.statusElement) state.statusElement.textContent = "";
      }, 4500);
    };

    const applyBinding = (binding) => {
      const hasManualEdit = state.edits.has(binding.key);
      const text = hasManualEdit
        ? state.edits.get(binding.key).text
        : binding.aiText;
      binding.target.classList.remove("after-interview-tab-empty");
      if (binding.markdown) {
        binding.target.textContent = text || "";
        delete binding.target.dataset.markdownRendered;
        delete binding.target.dataset.markdownSource;
        if (text) renderGeneratedMarkdown(binding.target);
      } else {
        binding.target.textContent = text || "";
      }
      if (!hasManualEdit && !String(text || "").trim() && binding.fallback) {
        binding.target.textContent = binding.fallback;
        binding.target.classList.add("after-interview-tab-empty");
      }

      const { toolbar, editButton, badge } = binding.controls;
      const canEdit = hasManualEdit || Boolean(String(binding.aiText || "").trim());
      toolbar.hidden = !canEdit;
      editButton.disabled = !state.ready;
      editButton.hidden = !canEdit;
      badge.hidden = !hasManualEdit;
      binding.target.dataset.managerReportEditKey = binding.key;
      // Provenance stays AI-assisted when the generated text is edited.
      binding.target.dataset.managerReportManuallyEdited = hasManualEdit ? "true" : "false";
    };

    const setAiText = (key, text) => {
      const binding = state.bindings.get(key);
      if (!binding) return;
      binding.aiText = String(text || "");
      binding.target.dataset.managerReportAiText = binding.aiText;
      applyBinding(binding);
    };

    const postEdit = async (payload) => {
      if (!state.saveUrl) throw new Error(copy().editSaveFailed);
      const response = await fetch(state.saveUrl, {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({
          ...payload,
          language: state.language,
        }),
      });
      let data = {};
      try { data = await response.json(); } catch (_error) {}
      if (!response.ok || !data.ok) {
        if (response.status === 409) throw new Error(copy().editVersionConflict);
        throw new Error(data.error || copy().editSaveFailed);
      }
      return data;
    };

    const ensureDialog = () => {
      if (state.dialog) return state.dialog;
      const dialog = document.createElement("dialog");
      dialog.className = "after-interview-manager-report__edit-dialog";
      dialog.setAttribute("aria-labelledby", "manager-report-edit-title");
      dialog.setAttribute("aria-describedby", "manager-report-edit-help");

      const heading = document.createElement("h2");
      heading.id = "manager-report-edit-title";
      heading.className = "after-interview-manager-report__edit-title";
      heading.textContent = copy().editDialogTitle;
      const help = document.createElement("p");
      help.id = "manager-report-edit-help";
      help.className = "after-interview-manager-report__edit-help";
      help.textContent = copy().editHelp;
      const label = document.createElement("label");
      label.className = "after-interview-manager-report__edit-label";
      label.textContent = copy().editDialogTitle;
      const textarea = document.createElement("textarea");
      textarea.className = "form-control after-interview-manager-report__edit-textarea";
      textarea.maxLength = 30000;
      textarea.rows = 12;
      textarea.autocomplete = "off";
      textarea.setAttribute("aria-label", copy().editDialogTitle);
      const error = document.createElement("div");
      error.className = "alert alert-danger d-none mt-3 mb-0";
      error.setAttribute("role", "alert");
      const actions = document.createElement("div");
      actions.className = "after-interview-manager-report__edit-actions";
      const restoreButton = document.createElement("button");
      restoreButton.type = "button";
      restoreButton.className = "btn btn-outline-secondary me-auto";
      restoreButton.textContent = copy().restoreAiText;
      const cancelButton = document.createElement("button");
      cancelButton.type = "button";
      cancelButton.className = "btn btn-light";
      cancelButton.textContent = copy().cancelEdit;
      const saveButton = document.createElement("button");
      saveButton.type = "button";
      saveButton.className = "btn btn-primary";
      saveButton.textContent = copy().saveEdit;
      actions.append(restoreButton, cancelButton, saveButton);
      dialog.append(heading, help, label, textarea, error, actions);
      panel.appendChild(dialog);

      let activeBinding = null;
      let opener = null;
      const closeDialog = () => {
        if (dialog.open) dialog.close();
      };
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        closeDialog();
      });
      dialog.addEventListener("close", () => {
        error.textContent = "";
        error.classList.add("d-none");
        if (opener?.isConnected) opener.focus();
        activeBinding = null;
      });
      cancelButton.addEventListener("click", closeDialog);
      saveButton.addEventListener("click", async () => {
        if (!activeBinding || saveButton.disabled) return;
        const binding = activeBinding;
        const current = state.edits.get(binding.key);
        saveButton.disabled = true;
        restoreButton.disabled = true;
        cancelButton.disabled = true;
        error.classList.add("d-none");
        try {
          const data = await postEdit({
            action: "save",
            block_key: binding.key,
            expected_version: current?.version || 0,
            text: textarea.value,
          });
          state.edits.set(binding.key, data.edit);
          applyBinding(binding);
          document.dispatchEvent(new CustomEvent("talena:manager-report-activity-changed"));
          announce(copy().editSaved);
          closeDialog();
        } catch (saveError) {
          error.textContent = saveError.message || copy().editSaveFailed;
          error.classList.remove("d-none");
        } finally {
          saveButton.disabled = false;
          restoreButton.disabled = false;
          cancelButton.disabled = false;
        }
      });
      restoreButton.addEventListener("click", async () => {
        if (!activeBinding || restoreButton.disabled) return;
        const binding = activeBinding;
        const current = state.edits.get(binding.key);
        if (!current || !window.confirm(copy().confirmRestoreAiText)) return;
        saveButton.disabled = true;
        restoreButton.disabled = true;
        cancelButton.disabled = true;
        error.classList.add("d-none");
        try {
          await postEdit({
            action: "restore_ai",
            block_key: binding.key,
            expected_version: current.version,
          });
          state.edits.delete(binding.key);
          applyBinding(binding);
          document.dispatchEvent(new CustomEvent("talena:manager-report-activity-changed"));
          announce(copy().editSaved);
          closeDialog();
        } catch (restoreError) {
          error.textContent = restoreError.message || copy().editRestoreFailed;
          error.classList.remove("d-none");
        } finally {
          saveButton.disabled = false;
          restoreButton.disabled = false;
          cancelButton.disabled = false;
        }
      });

      state.dialog = {
        element: dialog,
        textarea,
        error,
        restoreButton,
        open(binding) {
          if (!state.ready) return;
          activeBinding = binding;
          opener = binding.controls.editButton;
          const current = state.edits.get(binding.key);
          const fieldLabel = binding.label || copy().editDialogTitle;
          heading.textContent = copy().editDialogTitle + " · " + fieldLabel;
          label.textContent = fieldLabel;
          textarea.setAttribute("aria-label", fieldLabel);
          textarea.value = current ? current.text : binding.aiText;
          restoreButton.hidden = !current;
          error.textContent = "";
          error.classList.add("d-none");
          dialog.showModal();
          textarea.focus();
        },
      };
      return state.dialog;
    };

    const register = (target, key, options = {}) => {
      const binding = {
        target,
        key,
        label: String(options.label || copy().editDialogTitle),
        aiText: String(options.aiText || ""),
        fallback: String(options.fallback || ""),
        markdown: options.markdown === true,
        controls: null,
      };
      const toolbar = document.createElement("span");
      toolbar.className = "after-interview-manager-report__edit-controls";
      const badge = document.createElement("span");
      badge.className = "after-interview-manager-report__edited-badge";
      badge.textContent = copy().manuallyEdited;
      badge.setAttribute("role", "status");
      badge.hidden = true;
      const editButton = document.createElement("button");
      editButton.type = "button";
      editButton.className = "btn btn-icon btn-light after-interview-manager-report__edit-button";
      editButton.title = copy().editText;
      editButton.setAttribute("aria-label", copy().editText + ": " + binding.label);
      editButton.disabled = true;
      editButton.innerHTML = '<i data-feather="edit-2" aria-hidden="true"></i>';
      editButton.addEventListener("click", () => ensureDialog().open(binding));
      toolbar.append(badge, editButton);
      binding.controls = { toolbar, badge, editButton };
      target.dataset.managerReportAiText = binding.aiText;
      target.dataset.managerReportEditKey = key;
      state.bindings.set(key, binding);
      applyBinding(binding);
      return toolbar;
    };

    const load = async () => {
      if (!state.loadUrl) throw new Error(copy().reportEditsLoadFailed);
      const response = await fetch(state.loadUrl, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      let data = {};
      try { data = await response.json(); } catch (_error) {}
      if (!response.ok || !data.ok || !["sv", "en"].includes(data.language)) {
        throw new Error(data.error || copy().reportEditsLoadFailed);
      }
      state.language = data.language;
      state.edits = new Map((data.edits || []).map((edit) => [edit.block_key, edit]));
      state.ready = true;
      state.bindings.forEach(applyBinding);
      return data;
    };

    const ensureRegenerationConfirmation = () => {
      if (state.regenerationConfirmation) return state.regenerationConfirmation;

      const dialog = document.createElement("dialog");
      dialog.className = "after-interview-manager-report__confirm-dialog";
      dialog.setAttribute("aria-labelledby", "manager-report-regeneration-title");
      dialog.setAttribute("aria-describedby", "manager-report-regeneration-description");

      const header = document.createElement("div");
      header.className = "after-interview-manager-report__confirm-header";
      const iconWrap = document.createElement("div");
      iconWrap.className = "after-interview-manager-report__confirm-icon";
      const icon = document.createElement("i");
      icon.setAttribute("data-feather", "refresh-cw");
      icon.setAttribute("aria-hidden", "true");
      iconWrap.appendChild(icon);

      const heading = document.createElement("h2");
      heading.id = "manager-report-regeneration-title";
      heading.className = "after-interview-manager-report__confirm-title";
      heading.textContent = copy().confirmRegenerationTitle;
      header.append(iconWrap, heading);

      const description = document.createElement("p");
      description.id = "manager-report-regeneration-description";
      description.className = "after-interview-manager-report__confirm-description";
      description.textContent = copy().confirmRegenerationBody;

      const note = document.createElement("p");
      note.className = "after-interview-manager-report__confirm-note";
      note.textContent = copy().confirmRegenerationNote;

      const actions = document.createElement("div");
      actions.className = "after-interview-manager-report__confirm-actions";
      const cancelButton = document.createElement("button");
      cancelButton.type = "button";
      cancelButton.className = "btn btn-light";
      cancelButton.textContent = copy().confirmRegenerationCancel;
      cancelButton.setAttribute("autofocus", "");
      const continueButton = document.createElement("button");
      continueButton.type = "button";
      continueButton.className = "btn btn-primary";
      continueButton.textContent = copy().confirmRegenerationContinue;
      actions.append(cancelButton, continueButton);
      dialog.append(header, description, note, actions);
      panel.appendChild(dialog);

      let activeTrigger = null;
      let opener = null;
      const close = () => {
        if (dialog.open) dialog.close();
      };
      dialog.addEventListener("cancel", (event) => {
        event.preventDefault();
        close();
      });
      dialog.addEventListener("close", () => {
        activeTrigger = null;
        if (opener?.isConnected) opener.focus();
        opener = null;
      });
      cancelButton.addEventListener("click", close);
      continueButton.addEventListener("click", () => {
        const trigger = activeTrigger;
        activeTrigger = null;
        close();
        if (!trigger?.isConnected || trigger.disabled) return;
        // Let the browser finish removing the modal from the top layer before
        // replaying the original click. Otherwise the underlying button can
        // remain inert for the rest of this event turn in some browsers.
        window.setTimeout(() => {
          if (!trigger.isConnected || trigger.disabled) return;
          const currentState = workspace?._talenaManagerReportEditController?.state;
          if (!currentState) return;
          currentState.confirmedRegenerationTrigger = trigger;
          trigger.click();
        }, 0);
      });

      state.regenerationConfirmation = {
        element: dialog,
        open(trigger) {
          if (dialog.open) return;
          activeTrigger = trigger;
          opener = trigger;
          heading.textContent = copy().confirmRegenerationTitle;
          description.textContent = copy().confirmRegenerationBody;
          note.textContent = copy().confirmRegenerationNote;
          cancelButton.textContent = copy().confirmRegenerationCancel;
          continueButton.textContent = copy().confirmRegenerationContinue;
          dialog.showModal();
          cancelButton.focus();
          if (window.feather) window.feather.replace();
        },
      };
      return state.regenerationConfirmation;
    };

    if (workspace) {
      workspace._talenaManagerReportEditController = {
        state,
        setAiText,
        openRegenerationConfirmation: (trigger) =>
          ensureRegenerationConfirmation().open(trigger),
      };
      if (workspace.dataset.managerReportEditConfirmationBound !== "true") {
        workspace.dataset.managerReportEditConfirmationBound = "true";
        workspace.addEventListener("click", (event) => {
          const controller = workspace._talenaManagerReportEditController;
          const currentState = controller?.state;
          const trigger = event.target.closest?.(
            "[data-after-interview-regenerate], [data-personality-ai-regenerate], [data-post-interview-generate]"
          );
          if (!trigger || !currentState) return;
          if (currentState.confirmedRegenerationTrigger === trigger) {
            currentState.confirmedRegenerationTrigger = null;
            return;
          }
          if (currentState.managerReportGenerating) return;
          if (!currentState.ready) {
            event.preventDefault();
            event.stopImmediatePropagation();
            return;
          }
          const blockKey = trigger.dataset.afterInterviewRegenerate || "";
          const hasEditedBlock = blockKey && currentState.edits.has(blockKey);
          const isPersonalityRegeneration =
            trigger.hasAttribute("data-personality-ai-regenerate")
            && [...currentState.edits.keys()].some((key) => key.startsWith("personality:"));
          const isFullRegeneration =
            trigger.hasAttribute("data-post-interview-generate")
            && currentState.edits.size > 0;
          if (
            hasEditedBlock || isPersonalityRegeneration || isFullRegeneration
          ) {
            event.preventDefault();
            event.stopImmediatePropagation();
            controller.openRegenerationConfirmation?.(trigger);
          }
        }, true);
      }
    }

    return {
      state,
      register,
      load,
      setAiText,
      announce,
      applyAll: () => state.bindings.forEach(applyBinding),
    };
  };

  const generateContentBlock = async (panel, blockKey, body, error, button = null) => {
    if (button?.disabled) return;
    const root = panel.closest("[data-final-output-root]");
    const regenerateUrl = root?.dataset.postInterviewRegenerateUrl || "";
    if (!regenerateUrl) {
      error.textContent = copy().sectionGenerationFailed;
      error.classList.remove("d-none");
      return;
    }

    const editController = panel.closest("[data-candidate-insights-workspace]")
      ?._talenaManagerReportEditController;
    const editState = editController?.state;
    const binding = editState?.bindings.get(blockKey);
    const preserveManualEdit = editState?.edits.has(blockKey) === true;
    const previousText = binding?.aiText
      ?? body.dataset.markdownSource
      ?? body.textContent
      ?? "";
    error.classList.add("d-none");
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
      button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
    }
    if (!preserveManualEdit) {
      body.classList.remove("after-interview-tab-empty", "after-interview-rich-text");
      delete body.dataset.markdownRendered;
      delete body.dataset.markdownSource;
      body.replaceChildren();
    }

    try {
      const startUrl = new URL(regenerateUrl, window.location.origin);
      startUrl.searchParams.set("block", blockKey);
      const startResponse = await fetch(startUrl.toString(), {
        method: "POST",
        headers: {
          "X-CSRFToken": csrfToken(),
          "X-Requested-With": "XMLHttpRequest",
          "Content-Type": "application/json",
        },
        credentials: "same-origin",
        body: JSON.stringify({}),
      });
      const startData = await startResponse.json();
      if (!startResponse.ok) throw new Error(startData.error || copy().sectionGenerationFailed);

      const streamResponse = await fetch(startData.stream_url, {
        headers: { Accept: "application/x-ndjson", "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      });
      if (!streamResponse.ok || !streamResponse.body) {
        let message = copy().sectionGenerationFailed;
        try { message = (await streamResponse.json()).error || message; } catch (_error) {}
        throw new Error(message);
      }

      const reader = streamResponse.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";
      let received = "";
      const handleLine = (rawLine) => {
        const line = rawLine.trim();
        if (!line) return;
        const event = JSON.parse(line);
        if (event.type === "content_block_delta" && event.block === blockKey) {
          received += event.text || "";
          if (!preserveManualEdit) body.textContent = received;
        } else if (event.type === "content_block_error" && event.block === blockKey) {
          throw new Error(event.message || copy().sectionGenerationFailed);
        }
      };

      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        lines.forEach(handleLine);
      }
      buffer += decoder.decode();
      if (buffer.trim()) handleLine(buffer);
      if (!received.trim()) throw new Error(copy().sectionGenerationFailed);

      body.dataset.afterInterviewAiOrigin = "true";
      if (editController?.setAiText) {
        editController.setAiText(blockKey, received);
      } else {
        delete body.dataset.markdownRendered;
        renderGeneratedMarkdown(body);
      }
      if (button) {
        button.title = copy().regenerateSection;
        button.setAttribute("aria-label", copy().regenerateSection);
      }
    } catch (generationError) {
      if (!preserveManualEdit) {
        body.textContent = previousText;
        if (!previousText.trim()) {
          body.classList.add("after-interview-tab-empty");
          body.textContent = copy().unavailable;
        } else {
          delete body.dataset.markdownRendered;
          renderGeneratedMarkdown(body);
        }
      }
      error.textContent = generationError.message || copy().sectionGenerationFailed;
      error.classList.remove("d-none");
    } finally {
      if (button) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        button.innerHTML = '<i data-feather="refresh-cw"></i>';
      }
      if (window.feather) window.feather.replace();
    }
  };

  // The two navigation levels reuse the same components as the other
  // candidate views: candidate-insights-view-option and personality-view-tab.
  const makeTab = (key, label, panelId, kind = "primary") => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = kind === "report"
      ? "personality-view-tab" : "candidate-insights-view-option";
    button.dataset.afterInterviewTab = key;
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", panelId);
    button.setAttribute("aria-selected", "false");
    const icons = {
      evidence: "clipboard", overview: "layers", interview: "message-square",
      explore: "search", managerReport: "file-text",
    };
    if (kind === "report") {
      const icon = document.createElement("i");
      icon.setAttribute("data-feather", icons[key] || "file-text");
      icon.setAttribute("aria-hidden", "true");
      const text = document.createElement("span");
      text.textContent = label;
      button.append(icon, text);
    } else {
      // Same text-only markup as Teamrapport / Ledarskapsrapport /
      // Urspårningsrapport, with no icon or rounded pill styling.
      button.textContent = label;
    }
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
      /* Exact navigation styling from candidate-insight-tabs.css, used by
         Teamrapport / Ledarskapsrapport / Urspårningsrapport.
         The scoped rules prevent the assessment pill switcher from winning
         when After interview is rendered outside .candidate-insight-page. */
      __PANEL__ .candidate-insights-subnavigation {
        margin: 0 !important;
        padding: 0 1.5rem !important;
        border-bottom: 1px solid var(--talena-border, #e5dfd8) !important;
      }
      __PANEL__ .candidate-insights-subnavigation__layout {
        margin: 0 !important;
      }
      __PANEL__ .after-interview-primary-nav {
        display: flex !important;
        align-items: center !important;
        gap: 1.05rem !important;
        width: 100% !important;
        padding: 0 !important;
        border: 0 !important;
        border-radius: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
        overflow-x: auto;
        scrollbar-width: none;
      }
      __PANEL__ .after-interview-primary-nav::-webkit-scrollbar {
        display: none;
      }
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option {
        position: relative;
        flex: 0 0 auto;
        display: inline-flex;
        align-items: center;
        min-height: 45px !important;
        padding: 0 !important;
        border: 0 !important;
        border-bottom: 2px solid transparent !important;
        border-radius: 0 !important;
        background: transparent !important;
        color: var(--talena-text-muted, #766e68) !important;
        font-size: .7rem !important;
        font-weight: 550 !important;
        line-height: 1.25;
        white-space: nowrap;
        box-shadow: none !important;
      }
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option:hover:not(:disabled) {
        border-bottom-color: rgba(255, 111, 97, .28) !important;
        background: transparent !important;
        color: var(--talena-ink, #191817) !important;
      }
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option.is-active,
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option[aria-selected="true"] {
        border-bottom-color: var(--talena-coral, #ff6f61) !important;
        background: transparent !important;
        color: var(--talena-coral-strong, #ed7468) !important;
        font-weight: 550 !important;
      }
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option:disabled,
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option[aria-disabled="true"] {
        opacity: .52; cursor: not-allowed;
      }
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option:disabled:hover {
        border-bottom-color: transparent !important;
        color: var(--talena-text-muted, #766e68) !important;
      }
      __PANEL__ .after-interview-tabs__locked-hint {
        color: var(--talena-text-muted, #766e68); font-size: .73rem;
        line-height: 1.5; margin: .55rem 0 .8rem;
      }
      __PANEL__ .candidate-insights-subworkspace__panels { padding: 1.25rem 1.5rem 1.5rem; }
      __PANEL__ .after-interview-journey {
        padding: 1.15rem 1.5rem; background: #fdfcfb;
        border-bottom: 1px solid var(--talena-border, #e5dfd8);
      }
      __PANEL__ .after-interview-journey__title {
        margin: 0 0 .7rem; font-size: .81rem; font-weight: 650;
      }
      __PANEL__ .after-interview-journey__steps {
        display: grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap: .75rem;
      }
      __PANEL__ .after-interview-journey__step {
        display: flex; gap: .65rem; align-items: flex-start; min-width: 0;
        padding: .8rem .85rem; border: 1px solid var(--talena-border, #e5dfd8);
        background: #fff; border-radius: 11px;
      }
      __PANEL__ .after-interview-journey__step.is-current {
        background: #fff7f5; border-color: rgba(255,111,97,.55);
      }
      __PANEL__ .after-interview-journey__number {
        flex: 0 0 25px; width: 25px; height: 25px; display: flex;
        align-items: center; justify-content: center;
        border-radius: 50%; background: #f0edeb; color: #5d5550;
        font-size: .74rem; font-weight: 700;
      }
      __PANEL__ .after-interview-journey__step.is-current .after-interview-journey__number {
        background: var(--talena-coral, #ff6f61); color: white;
      }
      __PANEL__ .after-interview-journey__step.is-done .after-interview-journey__number {
        background: #e8f1e8; color: #315e42;
      }
      __PANEL__ .after-interview-journey__step-title {
        display: block; color: var(--talena-ink, #191817);
        font-size: .78rem; font-weight: 650; line-height: 1.45;
      }
      __PANEL__ .after-interview-journey__step-text {
        display: block; margin-top: .12rem;
        color: var(--talena-text-muted, #766e68); font-size: .72rem; line-height: 1.55;
      }
      __PANEL__ .after-interview-evidence-card {
        border: none !important; border-radius: 0 !important;
        background: transparent !important; padding: .25rem 0 0 !important;
      }
      __PANEL__ .after-interview-evidence-intro { margin-bottom: 1.25rem; }
      __PANEL__ .after-interview-evidence-intro__kicker {
        margin: 0 0 .35rem; font-size: .68rem; font-weight: 700;
        color: #d95d51; letter-spacing: .06em;
      }
      __PANEL__ .after-interview-evidence-intro__title {
        margin: 0 0 .35rem; color: var(--talena-ink, #191817);
        font-size: 1.26rem; font-weight: 700; line-height: 1.25;
      }
      __PANEL__ .after-interview-evidence-intro__description {
        max-width: 780px; margin: 0; font-size: .85rem; line-height: 1.65;
        color: var(--talena-text-muted, #766e68);
      }
      __PANEL__ .after-interview-evidence-intro__tip {
        display: flex; gap: .5rem; align-items: flex-start; margin: .8rem 0 0;
        font-size: .76rem; line-height: 1.55; color: #615954;
      }
      __PANEL__ .after-interview-evidence-intro__tip svg {
        width: 15px; height: 15px; flex: 0 0 15px; margin-top: 1px;
      }
      __PANEL__.after-interview-simplified .after-interview-evidence-card [data-interview-notes-root] {
        margin-top: 0 !important;
      }
      @media (max-width: 767px) {
        __PANEL__ .after-interview-journey { padding: 1rem; }
        __PANEL__ .after-interview-journey__steps { grid-template-columns: 1fr; gap: .5rem; }
        __PANEL__ .after-interview-journey__step { padding: .65rem .75rem; }
        __PANEL__ .after-interview-evidence-intro__title { font-size: 1.1rem; }
      }
      /* Primary navigation inherits the shared candidate-insights styles. */
      __PANEL__ .after-interview-primary-nav .candidate-insights-view-option.needs-update::after {
        content: ""; display: inline-block; width: 7px; height: 7px;
        border-radius: 50%; background: #e17d54; margin-left: .45rem;
        vertical-align: middle;
      }
      __PANEL__ .after-interview-reports { min-width: 0; }
      __PANEL__ .after-interview-reports[hidden] { display: none !important; }
      __PANEL__ .after-interview-reports__header {
        display: flex; align-items: flex-start; justify-content: space-between;
        gap: 1rem; margin: .15rem 0 1rem;
      }
      __PANEL__ .after-interview-reports__title {
        margin: 0 0 .3rem; color: var(--talena-ink, #191817);
        font-size: 1.28rem; font-weight: 750;
      }
      __PANEL__ .after-interview-reports__description {
        margin: 0; color: var(--talena-text-muted, #766e68);
        font-size: .8rem; line-height: 1.6;
      }
      __PANEL__ .after-interview-reports__refresh {
        display: inline-flex; align-items: center; justify-content: center;
        width: 38px; height: 38px; min-width: 38px; border-radius: 10px;
        border: 1px solid var(--talena-border, #e5dfd8);
        background: #fff; color: var(--talena-text-muted, #766e68);
      }
      __PANEL__ .after-interview-reports__refresh svg { width: 16px; height: 16px; }
      __PANEL__ .after-interview-reports__refresh.needs-update {
        border-color: rgba(255,111,97,.55); background: #fff5f2; color: #cb5348;
      }
      __PANEL__ .after-interview-reports__refresh:hover {
        background: #fff5f2; color: #cb5348;
      }
      __PANEL__ .after-interview-reports__refresh[disabled] { opacity: .5; cursor: not-allowed; }
      __PANEL__ .after-interview-reports__status {
        margin: 0 0 1rem; padding: .8rem 1rem; border-radius: 10px;
        background: #f8f7f5; color: #625b55; font-size: .78rem;
        line-height: 1.55;
      }
      __PANEL__ .after-interview-reports__status[hidden] { display: none !important; }
      __PANEL__ .after-interview-reports__status.needs-update {
        background: #fff5ed; color: #775438; border: 1px solid #efdacb;
      }
      __PANEL__ .after-interview-reports__status-title { font-weight: 650; }
      __PANEL__ .after-interview-reports__status-detail { display: block; margin-top: .15rem; }
      /* Nested report navigation inherits personality-view-tabs styles. */
      __PANEL__ .after-interview-report-panels { min-width: 0; }
      __PANEL__ .after-interview-report-panels > [hidden] { display: none !important; }
      __PANEL__ .after-interview-evidence-card [data-post-interview-generate][data-regenerate="true"] {
        display: none !important;
      }
      __PANEL__ .after-interview-evidence-rebuild {
        margin: 1rem 0 0; display: flex; gap: .75rem;
        align-items: center; justify-content: space-between; flex-wrap: wrap;
        padding: .9rem 1rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 11px; background: #faf9f7;
      }
      __PANEL__ .after-interview-evidence-rebuild .btn { white-space: normal; }
      __PANEL__ .after-interview-evidence-rebuild__text {
        margin: 0; color: var(--talena-text-muted, #766e68);
        font-size: .76rem; line-height: 1.5;
      }
      @media (max-width: 767px) {
        __PANEL__ .after-interview-reports__header { flex-wrap: wrap; }
        __PANEL__ .after-interview-evidence-rebuild { align-items: flex-start; }
      }
      __PANEL__ .after-interview-tab-panels { min-width: 0; }
      __PANEL__ .after-interview-tab-panel { display: grid; gap: 1rem; min-width: 0; }
      __PANEL__ .after-interview-tab-panel[hidden] { display: none !important; }
      __PANEL__ .after-interview-tab-card {
        min-width: 0; padding: 1.25rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 14px; background: #fff;
      }
      __PANEL__ .after-interview-tab-card__toolbar {
        display: flex; align-items: center; justify-content: space-between; gap: .75rem;
      }
      __PANEL__ .after-interview-tab-card__regenerate {
        flex: 0 0 auto; width: 2.25rem; height: 2.25rem; padding: .35rem;
        color: var(--talena-text-muted, #766e68); border: 1px solid var(--talena-border, #e5dfd8);
      }
      __PANEL__ .after-interview-tab-card__regenerate[aria-busy="true"] { opacity: .7; }
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
      .after-interview-manager-report__pdf-export-shell { display: none; }
      __PANEL__ .after-interview-manager-report__pdf-export-root { display: none; }
      __PANEL__ .after-interview-manager-report__header {
        display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem;
      }
      __PANEL__ .after-interview-manager-report__actions {
        display: flex; align-items: center; gap: .6rem; flex: 0 0 auto; flex-wrap: wrap;
      }
      __PANEL__ .after-interview-manager-report__personality-part-header {
        display: flex; align-items: center; justify-content: flex-start;
        flex-wrap: wrap; gap: .1rem .35rem;
      }
      __PANEL__ .after-interview-manager-report__personality-part-title {
        flex: 0 1 auto; margin-bottom: .35rem;
      }
      __PANEL__ .after-interview-manager-report__edit-controls {
        position: static; display: inline-flex; align-items: center;
        justify-content: flex-start; gap: .25rem; flex: 0 0 auto;
      }
      __PANEL__ .after-interview-manager-report__edit-controls[hidden],
      __PANEL__ .after-interview-manager-report__edit-button[hidden] { display: none !important; }
      __PANEL__ .after-interview-manager-report__edit-button {
        display: grid; place-items: center; width: 1.5rem !important;
        height: 1.5rem !important; min-width: 1.5rem !important; padding: 0 !important;
        border: 0 !important; border-radius: 6px !important;
        background: transparent !important; color: var(--talena-text-muted, #766e68) !important;
        box-shadow: none !important;
      }
      __PANEL__ .after-interview-manager-report__edit-button svg {
        width: .82rem; height: .82rem; stroke-width: 1.8;
      }
      __PANEL__ .after-interview-manager-report__edit-button:hover,
      __PANEL__ .after-interview-manager-report__edit-button:focus-visible {
        background: var(--talena-coral-soft, #fff2ee) !important;
        color: var(--talena-coral-strong, #ed7468) !important;
        outline: 2px solid var(--talena-coral, #ff6f61); outline-offset: 2px;
      }
      __PANEL__ .after-interview-manager-report__edited-badge {
        padding: .2rem .48rem; border: 1px solid #ead6c5; border-radius: 999px;
        background: #fff7ee; color: #735036; font-size: .64rem; font-weight: 700;
        line-height: 1.4; white-space: nowrap;
      }
      __PANEL__ .after-interview-manager-report__edit-dialog {
        width: min(700px, calc(100vw - 2rem)); max-height: min(90vh, 900px);
        margin: auto; padding: 1.35rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 16px; background: #fff; color: var(--talena-ink, #191817);
        box-shadow: 0 1.5rem 4rem rgba(25, 24, 23, .2);
      }
      __PANEL__ .after-interview-manager-report__edit-dialog::backdrop {
        background: rgba(25, 24, 23, .48);
      }
      __PANEL__ .after-interview-manager-report__confirm-dialog {
        width: min(480px, calc(100vw - 2rem)); max-height: min(85vh, 720px);
        margin: auto; padding: 1.5rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 20px; background: #fff; color: var(--talena-ink, #191817);
        box-shadow: 0 1.5rem 4rem rgba(25, 24, 23, .2);
      }
      __PANEL__ .after-interview-manager-report__confirm-dialog::backdrop {
        background: rgba(25, 24, 23, .48); backdrop-filter: blur(3px);
      }
      __PANEL__ .after-interview-manager-report__confirm-header {
        display: flex; align-items: center; gap: .85rem; margin-bottom: 1rem;
      }
      __PANEL__ .after-interview-manager-report__confirm-icon {
        display: grid; place-items: center; width: 2.65rem; height: 2.65rem;
        flex: 0 0 2.65rem; border-radius: 14px;
        background: #fff3e5; color: #a36b35;
      }
      __PANEL__ .after-interview-manager-report__confirm-icon svg {
        width: 1.1rem; height: 1.1rem;
      }
      __PANEL__ .after-interview-manager-report__confirm-title {
        margin: 0; font-size: 1.12rem; font-weight: 750; letter-spacing: -.02em;
      }
      __PANEL__ .after-interview-manager-report__confirm-description {
        margin: 0; color: var(--talena-text-muted, #766e68);
        font-size: .88rem; line-height: 1.65;
      }
      __PANEL__ .after-interview-manager-report__confirm-note {
        margin: 1rem 0 0; padding: .8rem .9rem; border: 1px solid #f0e4d3;
        border-radius: 11px; background: #fffaf4; color: #735036;
        font-size: .76rem; line-height: 1.55;
      }
      __PANEL__ .after-interview-manager-report__confirm-actions {
        display: flex; justify-content: flex-end; gap: .55rem; margin-top: 1.3rem;
      }
      __PANEL__ .after-interview-manager-report__edit-title {
        margin: 0 0 .5rem; font-size: 1.15rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__edit-help {
        margin: 0 0 1rem; color: var(--talena-text-muted, #766e68);
        font-size: .82rem; line-height: 1.55;
      }
      __PANEL__ .after-interview-manager-report__edit-label {
        display: block; margin-bottom: .4rem; font-size: .8rem; font-weight: 700;
      }
      __PANEL__ .after-interview-manager-report__edit-textarea {
        min-height: 16rem; max-height: 55vh; resize: vertical; line-height: 1.55;
      }
      __PANEL__ .after-interview-manager-report__edit-actions {
        display: flex; align-items: center; justify-content: flex-end; gap: .55rem; margin-top: 1rem;
      }
      @media (max-width: 575px) {
        __PANEL__ .after-interview-manager-report__edit-dialog { padding: 1rem; }
        __PANEL__ .after-interview-manager-report__confirm-dialog { padding: 1.1rem; }
        __PANEL__ .after-interview-manager-report__confirm-actions { flex-wrap: wrap; }
        __PANEL__ .after-interview-manager-report__edit-actions { flex-wrap: wrap; }
        __PANEL__ .after-interview-manager-report__edit-actions .me-auto { margin-right: 0 !important; }
      }
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
        padding: .9rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 12px; background: #fff;
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
      __PANEL__ .after-interview-manager-report__motivation {
        margin-top: 1.8rem;
      }
      __PANEL__ .after-interview-manager-report__motivation-title {
        margin: 0 0 .85rem; color: var(--talena-ink, #191817); font-size: 1.15rem; font-weight: 750;
      }
      /* Readable report rows: a factor's meaning on the left, guidance on the right. */
      __PANEL__ .after-interview-manager-report__motivation-grid {
        display: grid; grid-template-columns: minmax(0, 1fr); gap: 1rem;
      }
      __PANEL__ .after-interview-manager-report__motivator {
        display: grid; grid-template-columns: minmax(0, .9fr) minmax(0, 1.8fr);
        align-items: start; gap: 1.5rem; min-width: 0; padding: 1.3rem;
        border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 14px; background: #fff;
      }
      __PANEL__ .after-interview-manager-report__motivator-intro {
        min-width: 0;
      }
      __PANEL__ .after-interview-manager-report__motivator-name {
        margin: 0 0 .55rem; color: var(--talena-ink, #191817);
        font-size: 1rem; font-weight: 750; line-height: 1.35;
      }
      __PANEL__ .after-interview-manager-report__motivator-definition {
        margin: 0; color: var(--talena-text-muted, #766e68);
        font-size: .8rem; line-height: 1.7;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical {
        min-width: 0; border-left: 1px solid var(--talena-border, #e5dfd8);
        padding-left: 1.5rem;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-title {
        margin: 0 0 .75rem; color: var(--talena-ink, #191817);
        font-size: .8rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-grid {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .75rem;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-box {
        min-width: 0; padding: 1rem; border: 1px solid #efebe6;
        border-radius: 11px; background: #faf9f7;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-box--do {
        background: #f7f9f7;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-box-title {
        display: flex; gap: .4rem; align-items: center;
        margin: 0 0 .6rem; color: var(--talena-ink, #191817);
        font-size: .79rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-box-title svg {
        flex-shrink: 0; width: 15px; height: 15px; stroke-width: 1.9;
        color: #746c66;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-box--do svg {
        color: #56816b;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-list {
        margin: 0; padding-left: 1.1rem; color: #615a54;
        font-size: .76rem; line-height: 1.65;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-list li {
        padding-left: .1rem;
      }
      __PANEL__ .after-interview-manager-report__motivator-practical-list li + li {
        margin-top: .55rem;
      }
      @media (max-width: 1050px) {
        __PANEL__ .after-interview-manager-report__motivator {
          grid-template-columns: minmax(0, 1fr); gap: 1rem;
        }
        __PANEL__ .after-interview-manager-report__motivator-practical {
          border-left: 0; padding-left: 0; border-top: 1px solid var(--talena-border, #e5dfd8);
          padding-top: 1rem;
        }
      }
      @media (max-width: 720px) {
        __PANEL__ .after-interview-manager-report__motivator-practical-grid {
          grid-template-columns: minmax(0, 1fr);
        }
        __PANEL__ .after-interview-manager-report__motivator { padding: 1rem; }
      }
      __PANEL__ .after-interview-manager-report__motivation-empty {
        margin: 0; padding: 1rem; border: 1px dashed var(--talena-border, #e5dfd8);
        border-radius: 11px; color: var(--talena-text-muted, #766e68); font-size: .76rem;
      }
      __PANEL__ .after-interview-manager-report__personality {
        margin-top: 1.8rem;
      }
      __PANEL__ .after-interview-manager-report__personality-title {
        margin: 0 0 .85rem; color: var(--talena-ink, #191817); font-size: 1.15rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__personality-advice {
        margin-top: 1rem; padding: 1rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 12px; background: #fff;
      }
      __PANEL__ .after-interview-manager-report__wellbeing {
        margin-top: 1.8rem; padding-top: 1.35rem;
        border-top: 1px solid var(--talena-border, #e5dfd8);
      }
      __PANEL__ .after-interview-manager-report__wellbeing-title {
        margin: 0; color: var(--talena-ink, #191817);
        font-size: 1.15rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__personality-advice-header {
        display: flex; align-items: center; justify-content: flex-start;
        flex-wrap: wrap; gap: .1rem .35rem;
      }
      __PANEL__ .after-interview-manager-report__personality-advice-title {
        margin: 0; color: var(--talena-ink, #191817); font-size: .9rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__personality-advice-text {
        margin-top: .55rem; color: var(--talena-text-muted, #766e68); font-size: .78rem; line-height: 1.65;
      }
      /* Tips för trivsel is a report section, not subdued helper text. */
      __PANEL__ .after-interview-manager-report__wellbeing
      .after-interview-manager-report__personality-advice-text {
        color: #3d3834; font-size: .85rem; line-height: 1.72;
      }
      __PANEL__ .after-interview-manager-report__wellbeing
      .after-interview-rich-text__paragraph,
      __PANEL__ .after-interview-manager-report__wellbeing
      .after-interview-rich-text__list,
      __PANEL__ .after-interview-manager-report__wellbeing
      .after-interview-rich-text__list li {
        color: #3d3834;
      }
      __PANEL__ .after-interview-manager-report__wellbeing
      ol.after-interview-rich-text__list {
        list-style-type: decimal;
      }
      __PANEL__ .after-interview-manager-report__generate[aria-busy="true"] {
        opacity: .75; cursor: wait;
      }
      __PANEL__ .after-interview-manager-report__personality-theme {
        margin-bottom: .8rem; padding: 1rem; border: 1px solid var(--talena-border, #e5dfd8);
        border-radius: 12px; background: #fff;
      }
      __PANEL__ .after-interview-manager-report__personality-theme-title {
        margin: 0 0 .7rem; color: var(--talena-ink, #191817); font-size: .9rem; font-weight: 750;
      }
      __PANEL__ .after-interview-manager-report__personality-parts {
        display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .9rem;
      }
      __PANEL__ .after-interview-manager-report__personality-part + .after-interview-manager-report__personality-part {
        padding-left: .9rem; border-left: 1px solid var(--talena-border, #e5dfd8);
      }
      __PANEL__ .after-interview-manager-report__personality-part-title {
        margin: 0 0 .35rem; color: var(--talena-coral-strong, #ed7468);
        font-size: .68rem; font-weight: 750; letter-spacing: .06em; text-transform: uppercase;
      }
      __PANEL__ .after-interview-manager-report__personality-part-text {
        margin: 0; color: var(--talena-text-muted, #766e68); font-size: .74rem; line-height: 1.55;
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
        __PANEL__ .after-interview-manager-report__personality-parts { grid-template-columns: 1fr; }
        __PANEL__ .after-interview-manager-report__personality-part + .after-interview-manager-report__personality-part {
          padding-left: 0; border-left: 0;
        }
      }
      @media (max-width: 575px) {
        __PANEL__ .after-interview-manager-report__header { flex-direction: column; }
        __PANEL__ .after-interview-manager-report__levels { grid-template-columns: 1fr; }
        __PANEL__ .after-interview-manager-report__level { min-height: 0; }
      }
      @media (max-width: 767px) {
        __PANEL__ .candidate-insights-subnavigation { padding: 0 1rem; }
        __PANEL__ .candidate-insights-subworkspace__panels { padding: 1rem; }
        __PANEL__ .after-interview-tab-card { padding: 1rem; border-radius: 12px; }
      }
    `.replaceAll("__PANEL__", PANEL_SELECTOR);
    document.head.appendChild(style);
  };

  const initPanel = (panel) => {
    if (!(panel instanceof Element)) return;
    const existingTabs = panel.querySelector(
      ":scope > .final-output-card > .after-interview-tabs"
    );
    if (panel.dataset.afterInterviewTabsReady === "true" && existingTabs?.isConnected) return;
    panel.dataset.afterInterviewTabsReady = "false";

    const card = panel.querySelector(":scope > .final-output-card");
    const header = card?.querySelector(":scope > div:first-child");
    const notesRoot = card?.querySelector("[data-interview-notes-root]");
    const postSection = card?.querySelector("[data-post-interview-section]");
    // Keep the native full-compilation action in the DOM. The new Evidence
    // and Reports actions delegate to it so its existing privacy, save,
    // streaming and manual-edit confirmation protections keep working.
    const postContent = postSection?.querySelector("[data-post-interview-content]");
    const outputRoot = panel.closest("[data-final-output-root]");
    const hasPostInterviewResult =
      outputRoot?.dataset.hasPostInterviewResult === "true";
    const hasCompiledPostInterviewResult =
      hasPostInterviewResult &&
      ["completed", "outdated"].includes(outputRoot?.dataset.postInterviewStatus);
    // A refreshed candidate fragment may have kept the old URL tab selection.
    // On the first successful compilation (or a different candidate), use the
    // proper default rather than restoring the previously selected Underlag.
    const candidateIdentity = outputRoot?.dataset.refreshUrl || "";
    const candidateChanged =
      lastRenderedCandidate !== null && lastRenderedCandidate !== candidateIdentity;
    const justCompiled =
      !candidateChanged && lastRenderedCompiled === false && hasCompiledPostInterviewResult;
    lastRenderedCandidate = candidateIdentity;
    lastRenderedCompiled = hasCompiledPostInterviewResult;

    if (!card || !header || !notesRoot || !postSection) return;

    ensureStyles();
    if (hasCompiledPostInterviewResult) {
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

    const journey = document.createElement("section");
    journey.className = "after-interview-journey";
    journey.setAttribute("aria-label", copy().journeyTitle);
    const journeyHeading = document.createElement("h3");
    journeyHeading.className = "after-interview-journey__title";
    journeyHeading.textContent = copy().journeyTitle;
    const journeySteps = document.createElement("div");
    journeySteps.className = "after-interview-journey__steps";
    copy().journeySteps.forEach((step, index) => {
      const item = document.createElement("div");
      item.className = "after-interview-journey__step";
      if (index === (hasCompiledPostInterviewResult ? 2 : 0)) {
        item.classList.add("is-current");
        item.setAttribute("aria-current", "step");
      } else if (hasCompiledPostInterviewResult && index < 2) {
        item.classList.add("is-done");
      }
      const number = document.createElement("span");
      number.className = "after-interview-journey__number";
      number.textContent = String(index + 1);
      const description = document.createElement("div");
      const title = document.createElement("span");
      title.className = "after-interview-journey__step-title";
      title.textContent = step.title;
      const body = document.createElement("span");
      body.className = "after-interview-journey__step-text";
      body.textContent = step.description;
      description.append(title, body);
      item.append(number, description);
      journeySteps.appendChild(item);
    });
    journey.append(journeyHeading, journeySteps);

    const navSection = document.createElement("section");
    navSection.className = "candidate-insights-subnavigation";
    const navLayout = document.createElement("div");
    navLayout.className = "candidate-insights-subnavigation__layout mb-4";

    const primaryNav = document.createElement("div");
    primaryNav.className = "candidate-insights-view-switcher after-interview-primary-nav";
    primaryNav.setAttribute("role", "tablist");
    primaryNav.setAttribute("aria-label", copy().journeyTitle);

    const tabPanels = document.createElement("div");
    tabPanels.className = "candidate-insights-subworkspace__panels";

    // Keep the existing report keys and URL values for bookmarks, PDF actions
    // and the final-output refresh helper. Only the visual navigation changes.
    // Keep historical interview_summary data on the server, but this tab is
    // retired (#442). Old afterTab=interview URLs fall back to Helhetsbild.
    const keys = ["evidence", "overview", "explore", "managerReport"];
    const reportKeys = keys.filter((key) => key !== "evidence");
    const buttons = new Map();
    const panels = new Map();

    const evidenceButton = makeTab("evidence", copy().tabs.evidence, "after-interview-tab-panel-evidence");
    const evidencePanel = makePanel("evidence", "after-interview-tab-panel-evidence");
    buttons.set("evidence", evidenceButton);
    panels.set("evidence", evidencePanel);
    primaryNav.appendChild(evidenceButton);
    tabPanels.appendChild(evidencePanel);

    const reportsArea = document.createElement("section");
    reportsArea.id = "after-interview-reports";
    reportsArea.className = "after-interview-reports";
    reportsArea.hidden = true;

    const reportsButton = document.createElement("button");
    reportsButton.type = "button";
    reportsButton.className = "candidate-insights-view-option";
    reportsButton.dataset.afterInterviewPrimaryTab = "reports";
    reportsButton.setAttribute("role", "tab");
    reportsButton.setAttribute("aria-controls", reportsArea.id);
    reportsButton.setAttribute("aria-selected", "false");
    reportsButton.textContent = copy().tabs.reports;
    if (!hasCompiledPostInterviewResult) {
      reportsButton.disabled = true;
      reportsButton.setAttribute("aria-disabled", "true");
      reportsButton.title = copy().lockedTabsHint;
    }
    primaryNav.appendChild(reportsButton);

    const reportsHeader = document.createElement("div");
    reportsHeader.className = "after-interview-reports__header";
    const reportsHeading = document.createElement("div");
    const reportsTitle = document.createElement("h3");
    reportsTitle.className = "after-interview-reports__title";
    reportsTitle.textContent = copy().reportOverviewTitle;
    const reportsIntro = document.createElement("p");
    reportsIntro.className = "after-interview-reports__description";
    reportsIntro.textContent = copy().reportsIntro;
    reportsHeading.append(reportsTitle, reportsIntro);
    const reportsRefresh = document.createElement("button");
    reportsRefresh.type = "button";
    reportsRefresh.className = "after-interview-reports__refresh";
    reportsRefresh.dataset.afterInterviewRebuild = "reports";
    reportsRefresh.title = copy().reportRebuildShort;
    reportsRefresh.setAttribute("aria-label", copy().reportRebuildShort);
    const reportsRefreshIcon = document.createElement("i");
    reportsRefreshIcon.setAttribute("data-feather", "refresh-cw");
    reportsRefresh.appendChild(reportsRefreshIcon);
    reportsHeader.append(reportsHeading, reportsRefresh);

    const reportStatus = document.createElement("div");
    reportStatus.className = "after-interview-reports__status";
    reportStatus.setAttribute("role", "status");
    reportStatus.setAttribute("aria-live", "polite");
    const reportStatusTitle = document.createElement("span");
    reportStatusTitle.className = "after-interview-reports__status-title";
    const reportStatusDetail = document.createElement("span");
    reportStatusDetail.className = "after-interview-reports__status-detail";
    reportStatus.append(reportStatusTitle, reportStatusDetail);
    reportStatus.hidden = true;

    const reportNavWrapper = document.createElement("div");
    reportNavWrapper.className = "personality-view-controls";
    const reportNav = document.createElement("div");
    reportNav.className = "personality-view-tabs";
    reportNav.setAttribute("role", "tablist");
    reportNav.setAttribute("aria-label", copy().tabs.reports);
    const reportPanels = document.createElement("div");
    reportPanels.className = "after-interview-report-panels";

    reportKeys.forEach((key) => {
      const id = "after-interview-tab-panel-" + key;
      const button = makeTab(key, copy().tabs[key], id, "report");
      const tabPanel = makePanel(key, id);
      buttons.set(key, button);
      panels.set(key, tabPanel);
      reportNav.appendChild(button);
      reportPanels.appendChild(tabPanel);
    });
    reportNavWrapper.appendChild(reportNav);
    reportsArea.append(reportsHeader, reportStatus, reportNavWrapper, reportPanels);
    tabPanels.appendChild(reportsArea);

    navLayout.appendChild(primaryNav);
    navSection.appendChild(navLayout);
    if (!hasCompiledPostInterviewResult) {
      const lockedHint = document.createElement("p");
      lockedHint.className = "after-interview-tabs__locked-hint";
      lockedHint.textContent = copy().lockedTabsHint;
      navSection.appendChild(lockedHint);
    }
    tabs.append(journey, navSection, tabPanels);
    header.insertAdjacentElement("afterend", tabs);

    const summary = postContent?.querySelector(":scope > .purpose-fit-section:first-child");
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

    const overviewSource = sourceBlock(panel, "overall_picture");
    if (window.TalenaStructuredOverallPicture?.createCard) {
      panels.get("overview").appendChild(
        window.TalenaStructuredOverallPicture.createCard(
          panel, overviewSource, sourceContent(panel, "overall_picture"),
          copy().tabs.overview, copy().descriptions.overview, outputRoot,
        ),
      );
    } else {
      panels.get("overview").appendChild(
        makeCard(panel, "overall_picture", copy().tabs.overview, copy().descriptions.overview, summary, "overall_picture"),
      );
    }
    panels.get("explore").appendChild(
      makeCard(panel, "explore_further", copy().tabs.explore, copy().descriptions.explore, exploreFallback.childNodes.length ? exploreFallback : null, "explore_further"),
    );
    const managerReportCard = document.createElement("section");
    managerReportCard.className = "after-interview-tab-card after-interview-manager-report";
    managerReportCard.hidden = true;
    const managerReportHeader = document.createElement("div");
    managerReportHeader.className = "after-interview-manager-report__header";
    const managerReportHeading = document.createElement("h3");
    managerReportHeading.className = "after-interview-tab-card__title";
    managerReportHeading.textContent = copy().managerReportTitle;
    const managerReportActions = document.createElement("div");
    managerReportActions.className = "after-interview-manager-report__actions";
    const managerReportAiTasks = [];
    const pdfButton = document.createElement("button");
    pdfButton.type = "button";
    // Match the small PDF action used in Personality, Motivation and Skills.
    pdfButton.className = "btn btn-icon btn-light talena-report-action-button after-interview-manager-report__pdf-button";
    pdfButton.disabled = true;
    pdfButton.setAttribute("aria-label", copy().savePdf);
    pdfButton.title = copy().savePdf;
    const pdfIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    pdfIcon.setAttribute("viewBox", "0 0 24 24");
    pdfIcon.setAttribute("width", "19");
    pdfIcon.setAttribute("height", "19");
    pdfIcon.setAttribute("fill", "none");
    pdfIcon.setAttribute("stroke", "currentColor");
    pdfIcon.setAttribute("stroke-width", "1.75");
    pdfIcon.setAttribute("stroke-linecap", "round");
    pdfIcon.setAttribute("stroke-linejoin", "round");
    pdfIcon.setAttribute("aria-hidden", "true");
    pdfIcon.innerHTML = '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>' +
      '<polyline points="14 2 14 8 20 8"/>' +
      '<path d="M12 12v6m-3-3 3 3 3-3"/>';
    const pdfLabel = document.createElement("span");
    pdfLabel.className = "visually-hidden";
    pdfLabel.textContent = copy().savePdf;
    pdfButton.append(pdfIcon, pdfLabel);
    const managerReportPdfError = document.createElement("div");
    managerReportPdfError.className = "alert alert-danger d-none mt-3 mb-0";
    managerReportPdfError.setAttribute("role", "alert");
    pdfButton.addEventListener("click", () => {
      if (pdfButton.disabled) return;
      managerReportPdfError.classList.add("d-none");
      pdfButton.disabled = true;
      pdfButton.setAttribute("aria-busy", "true");
      const spinner = document.createElement("span");
      spinner.className = "spinner-border spinner-border-sm";
      spinner.setAttribute("aria-hidden", "true");
      pdfLabel.textContent = copy().creatingPdf;
      pdfButton.replaceChildren(spinner, pdfLabel);

      const exportShell = panel.cloneNode(false);
      exportShell.classList.add("after-interview-manager-report__pdf-export-shell");
      exportShell.hidden = false;
      exportShell.style.cssText =
        "display:block;position:fixed;top:0;left:-10000px;width:186mm;margin:0;padding:0;" +
        "border:0;z-index:-1;background:#fff;pointer-events:none;";
      const exportRoot = document.createElement("div");
      exportRoot.className = "after-interview-manager-report__pdf-export-root";
      exportRoot.hidden = false;
      exportRoot.style.cssText = "display:block;width:100%;margin:0;padding:0;";
      const printableReport = managerReportCard.cloneNode(true);
      printableReport.hidden = false;
      printableReport.style.cssText =
        "display:block;width:100%;max-width:none;margin:0;padding:0;border:0;" +
        "box-shadow:none;background:#fff;";
      printableReport.querySelectorAll(
        ".after-interview-manager-report__actions, " +
        ".after-interview-manager-report__edit-controls, " +
        ".after-interview-manager-report__edit-dialog, " +
        ".after-interview-manager-report__confirm-dialog, " +
        ".alert, [role='status'][aria-live='polite']"
      ).forEach((element) => element.remove());
      printableReport.querySelectorAll(".after-interview-manager-report__guide")
        .forEach((guide) => { guide.open = true; });
      [
        ".after-interview-manager-report__levels",
        ".after-interview-manager-report__guide-levels",
        ".after-interview-manager-report__motivation-grid",
        ".after-interview-manager-report__personality-parts",
      ].forEach((selector) => printableReport.querySelectorAll(selector).forEach((grid) => {
        grid.style.gridTemplateColumns = "repeat(2, minmax(0, 1fr))";
      }));
      exportRoot.appendChild(printableReport);
      exportShell.appendChild(exportRoot);
      document.body.appendChild(exportShell);

      const filename = (copy().managerReportTitle.replace(/[\\/:*?"<>|]+/g, " ").trim() || "Manager report") + ".pdf";
      window.requestAnimationFrame(async () => {
        try {
          if (!window.TalenaManagerReportPdf) throw new Error("Manager PDF metadata helper unavailable");
          const reportMetadata = await window.TalenaManagerReportPdf.prepare(outputRoot);
          window.TalenaManagerReportPdf.decorate(printableReport, reportMetadata);
          await renderElementAsPdf(printableReport, filename, outputRoot);
          try {
            await window.TalenaManagerReportPdf.recordGenerated(outputRoot, reportMetadata);
          } catch (_auditError) {
            // PDF succeeded. Audit-confirmation failure must not misreport export failure.
            console.warn("Manager report PDF generation audit could not be recorded.");
          }
        } catch (_error) {
          managerReportPdfError.textContent = copy().pdfGenerationFailed;
          managerReportPdfError.classList.remove("d-none");
        } finally {
          exportShell.remove();
          pdfButton.disabled = false;
          pdfButton.removeAttribute("aria-busy");
          pdfLabel.textContent = copy().savePdf;
          pdfButton.replaceChildren(pdfIcon, pdfLabel);
          if (window.feather) window.feather.replace();
        }
      });
    });
    managerReportActions.appendChild(pdfButton);
    managerReportHeader.append(managerReportHeading, managerReportActions);
    const managerReportIntro = document.createElement("p");
    managerReportIntro.className = "after-interview-manager-report__intro";
    managerReportIntro.textContent = copy().managerReportIntro;
    managerReportCard.append(managerReportHeader, managerReportIntro, managerReportPdfError);

    const managerSkills = document.createElement("section");
    managerSkills.className = "after-interview-manager-report__skills";
    const managerSkillsTitle = document.createElement("h4");
    managerSkillsTitle.className = "after-interview-manager-report__skills-title";
    managerSkillsTitle.textContent = copy().managerSkillsTitle;
    managerSkills.appendChild(managerSkillsTitle);

    const workspace = panel.closest("[data-candidate-insights-workspace]");
    const managerReportEditController = createManagerReportEditController(
      panel,
      outputRoot,
      workspace,
    );
    const managerReportEditsReady = managerReportEditController.load()
      .then(() => ({ ok: true }))
      .catch((error) => ({ ok: false, error }));
    const managerReportEditStatus = document.createElement("span");
    managerReportEditStatus.className = "visually-hidden";
    managerReportEditStatus.setAttribute("role", "status");
    managerReportEditStatus.setAttribute("aria-live", "polite");
    managerReportEditController.state.statusElement = managerReportEditStatus;
    managerReportCard.appendChild(managerReportEditStatus);
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

    const managerMotivation = document.createElement("section");
    managerMotivation.className = "after-interview-manager-report__motivation";
    const managerMotivationTitle = document.createElement("h4");
    managerMotivationTitle.className = "after-interview-manager-report__motivation-title";
    managerMotivationTitle.textContent = copy().managerMotivationTitle;
    managerMotivation.appendChild(managerMotivationTitle);

    const managerMotivators = [
      ...(workspace?.querySelectorAll(
        "#candidate-insights-panel-motivation [data-manager-motivation-name][data-manager-motivation-definition]"
      ) || []),
    ].slice(0, 3);
    if (managerMotivators.length) {
      const motivationGrid = document.createElement("div");
      motivationGrid.className = "after-interview-manager-report__motivation-grid";
      managerMotivators.forEach((source) => {
        const motivator = document.createElement("article");
        motivator.className = "after-interview-manager-report__motivator";
        const name = document.createElement("h5");
        name.className = "after-interview-manager-report__motivator-name";
        name.textContent = source.dataset.managerMotivationName;
        const definition = document.createElement("p");
        definition.className = "after-interview-manager-report__motivator-definition";
        definition.textContent = source.dataset.managerMotivationDefinition;
        const factorKey = source.dataset.managerMotivationKey;
        const advice = getMotivationPracticalAdvice(panel)[isSwedish() ? "sv" : "en"]?.[factorKey];
        const motivatorIntro = document.createElement("div");
        motivatorIntro.className = "after-interview-manager-report__motivator-intro";
        motivatorIntro.append(name, definition);
        motivator.appendChild(motivatorIntro);
        if (advice) {
          const practical = document.createElement("div");
          practical.className = "after-interview-manager-report__motivator-practical";
          const practicalTitle = document.createElement("h6");
          practicalTitle.className = "after-interview-manager-report__motivator-practical-title";
          practicalTitle.textContent = copy().managerMotivationPracticalTitle;
          const practicalGrid = document.createElement("div");
          practicalGrid.className = "after-interview-manager-report__motivator-practical-grid";
          [
            { title: copy().managerMotivationDoTitle, items: advice.do, type: "do" },
            { title: copy().managerMotivationAvoidTitle, items: advice.avoid, type: "avoid" },
          ].forEach((group) => {
            const box = document.createElement("section");
            box.className = "after-interview-manager-report__motivator-practical-box after-interview-manager-report__motivator-practical-box--" + group.type;
            const heading = document.createElement("h6");
            heading.className = "after-interview-manager-report__motivator-practical-box-title";
            const headingIcon = document.createElement("i");
            headingIcon.setAttribute("data-feather", group.type === "do" ? "check-circle" : "alert-circle");
            headingIcon.setAttribute("aria-hidden", "true");
            const headingText = document.createElement("span");
            headingText.textContent = group.title;
            heading.append(headingIcon, headingText);
            const list = document.createElement("ul");
            list.className = "after-interview-manager-report__motivator-practical-list";
            group.items.forEach((item) => {
              const listItem = document.createElement("li");
              listItem.textContent = item;
              list.appendChild(listItem);
            });
            box.append(heading, list);
            practicalGrid.appendChild(box);
          });
          practical.append(practicalTitle, practicalGrid);
          motivator.appendChild(practical);
        }
        motivationGrid.appendChild(motivator);
      });
      managerMotivation.appendChild(motivationGrid);
      managerReportCard.appendChild(managerMotivation);
    }

    const managerPersonality = document.createElement("section");
    managerPersonality.className = "after-interview-manager-report__personality";
    const managerPersonalityTitle = document.createElement("h4");
    managerPersonalityTitle.className = "after-interview-manager-report__personality-title";
    managerPersonalityTitle.textContent = copy().managerPersonalityTitle;

    const personalityRoot = workspace?.querySelector(
      "#candidate-insights-panel-personality [data-personality-ai-root]"
    );
    const personalityFallbacks = {
      testbild: copy().managerPersonalityTestMissing,
      candidate_describes: copy().managerPersonalityInterviewMissing,
    };
    const datasetKeyFor = (theme, part) => {
      const pascal = (value) => value.split("_")
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join("");
      return "managerPersonality" + pascal(theme) + pascal(part);
    };
    let managerAdviceHasGeneratedText = Boolean(
      sourceBlock(panel, "wellbeing_tips")?.textContent?.trim()
    );
    let managerReportGenerateButton = null;
    let managerReportGenerateError = null;
    let managerReportGenerateLabel = null;
    let managerReportGenerateIcon = null;

    const updateManagerReportGenerateLabel = () => {
      if (
        !managerReportGenerateButton ||
        !managerReportGenerateLabel ||
        managerReportGenerateButton.getAttribute("aria-busy") === "true"
      ) return;
      const hasPersonalityText = personalityRoot && copy().managerPersonalityThemes.some((theme) =>
        ["testbild", "candidate_describes"].some((part) =>
          String(personalityRoot.dataset[datasetKeyFor(theme.key, part)] || "").trim()
        )
      );
      const hasGeneratedText = managerAdviceHasGeneratedText || hasPersonalityText;
      const label = hasGeneratedText
        ? copy().regenerateManagerReport
        : copy().generateManagerReport;
      managerReportGenerateLabel.textContent = label;
      managerReportGenerateButton.title = label;
      managerReportGenerateButton.setAttribute("aria-label", label);
    };

    managerReportGenerateButton = document.createElement("button");
    managerReportGenerateButton.type = "button";
    managerReportGenerateButton.className = "btn btn-icon btn-light talena-report-action-button after-interview-manager-report__generate";
    managerReportGenerateButton.dataset.postInterviewGenerate = "";
    managerReportGenerateIcon = document.createElement("i");
    managerReportGenerateIcon.setAttribute("data-feather", "refresh-cw");
    managerReportGenerateIcon.setAttribute("aria-hidden", "true");
    managerReportGenerateLabel = document.createElement("span");
    managerReportGenerateLabel.className = "visually-hidden";
    managerReportGenerateButton.append(managerReportGenerateIcon, managerReportGenerateLabel);
    // Consistent action order throughout Talena: PDF, then regenerate.
    managerReportActions.appendChild(managerReportGenerateButton);

    managerReportGenerateError = document.createElement("div");
    managerReportGenerateError.className = "alert alert-danger d-none mt-3 mb-3";
    managerReportGenerateError.setAttribute("role", "alert");
    managerReportIntro.insertAdjacentElement("afterend", managerReportGenerateError);

    if (personalityRoot) {
      managerReportAiTasks.push(async () => {
        const regenerateButton = personalityRoot.querySelector("[data-personality-ai-regenerate]");
        if (
          !regenerateButton ||
          !personalityRoot.dataset.regenerateUrl ||
          !personalityRoot.dataset.streamUrl
        ) {
          throw new Error(copy().sectionGenerationFailed);
        }

        const existingError = personalityRoot.querySelector("[data-personality-ai-error]");
        existingError?.classList.add("d-none");

        if (!regenerateButton.disabled) regenerateButton.click();

        let sawGeneration = regenerateButton.disabled;
        const deadline = Date.now() + 180000;
        while (Date.now() < deadline) {
          await new Promise((resolve) => window.setTimeout(resolve, 200));
          if (regenerateButton.disabled) sawGeneration = true;
          if (sawGeneration && !regenerateButton.disabled) break;
        }

        if (!sawGeneration || regenerateButton.disabled) {
          throw new Error(copy().sectionGenerationFailed);
        }

        const currentError = personalityRoot.querySelector("[data-personality-ai-error]");
        if (
          personalityRoot.dataset.status !== "completed" ||
          (currentError && !currentError.classList.contains("d-none"))
        ) {
          throw new Error(currentError?.textContent?.trim() || copy().sectionGenerationFailed);
        }
      });
    }

    managerReportGenerateButton.addEventListener("click", async () => {
      if (managerReportGenerateButton.disabled) return;
      managerReportGenerateError.classList.add("d-none");
      managerReportGenerateButton.disabled = true;
      managerReportGenerateButton.setAttribute("aria-busy", "true");
      const spinner = document.createElement("span");
      spinner.className = "spinner-border spinner-border-sm";
      spinner.setAttribute("role", "status");
      spinner.setAttribute("aria-hidden", "true");
      const generatingLabel = copy().generatingManagerReport;
      managerReportGenerateLabel.textContent = generatingLabel;
      managerReportGenerateButton.title = generatingLabel;
      managerReportGenerateButton.setAttribute("aria-label", generatingLabel);
      managerReportGenerateButton.replaceChildren(spinner, managerReportGenerateLabel);

      try {
        const failures = [];
        managerReportEditController.state.managerReportGenerating = true;
        try {
          for (const task of managerReportAiTasks) {
            try {
              await task();
            } catch (taskError) {
              failures.push(taskError.message || copy().sectionGenerationFailed);
            }
          }
        } finally {
          managerReportEditController.state.managerReportGenerating = false;
        }
        if (failures.length) throw new Error(failures.join(" "));
        managerAdviceHasGeneratedText = true;
      } catch (generationError) {
        managerReportGenerateError.textContent =
          generationError.message || copy().sectionGenerationFailed;
        managerReportGenerateError.classList.remove("d-none");
      } finally {
        managerReportGenerateButton.disabled = false;
        managerReportGenerateButton.removeAttribute("aria-busy");
        managerReportGenerateButton.replaceChildren(
          managerReportGenerateIcon,
          managerReportGenerateLabel,
        );
        updateManagerReportGenerateLabel();
        if (window.feather) window.feather.replace();
      }
    });

    updateManagerReportGenerateLabel();
    managerPersonality.appendChild(managerPersonalityTitle);
    const renderPersonalityText = (theme, part, text) => {
      const key = "personality:" + theme + ":" + part;
      managerReportEditController.setAiText(key, text || "");
      updateManagerReportGenerateLabel();
    };

    copy().managerPersonalityThemes.forEach((theme) => {
      const themeCard = document.createElement("article");
      themeCard.className = "after-interview-manager-report__personality-theme";
      themeCard.dataset.personalityTheme = theme.key;
      const themeTitle = document.createElement("h5");
      themeTitle.className = "after-interview-manager-report__personality-theme-title";
      themeTitle.textContent = theme.title;
      const parts = document.createElement("div");
      parts.className = "after-interview-manager-report__personality-parts";
      [
        { key: "testbild", title: copy().managerPersonalityTestbild },
        { key: "candidate_describes", title: copy().managerPersonalityCandidateDescribes },
      ].forEach((part) => {
        const content = document.createElement("div");
        content.className = "after-interview-manager-report__personality-part";
        const heading = document.createElement("h6");
        heading.className = "after-interview-manager-report__personality-part-title";
        heading.textContent = part.title;
        const text = document.createElement("p");
        text.className = "after-interview-manager-report__personality-part-text";
        text.dataset.managerPersonalityText = theme.key + ":" + part.key;
        const aiText = String(
          personalityRoot?.dataset[datasetKeyFor(theme.key, part.key)] || ""
        );
        text.textContent = aiText || personalityFallbacks[part.key];
        const editControls = managerReportEditController.register(
          text,
          "personality:" + theme.key + ":" + part.key,
          {
            aiText,
            fallback: personalityFallbacks[part.key],
            label: theme.title + " · " + part.title,
          },
        );
        const contentHeader = document.createElement("div");
        contentHeader.className = "after-interview-manager-report__personality-part-header";
        contentHeader.append(heading, editControls);
        content.append(contentHeader, text);
        parts.appendChild(content);
      });
      themeCard.append(themeTitle, parts);
      managerPersonality.appendChild(themeCard);
    });

    const managerAdvice = document.createElement("section");
    managerAdvice.className = "after-interview-manager-report__wellbeing";
    const managerAdviceHeader = document.createElement("div");
    managerAdviceHeader.className = "after-interview-manager-report__personality-advice-header";
    const managerAdviceTitle = document.createElement("h4");
    managerAdviceTitle.className = "after-interview-manager-report__wellbeing-title";
    managerAdviceTitle.textContent = copy().managerPersonalityAdviceTitle;
    const managerAdviceBody =
      sourceContent(panel, "wellbeing_tips") || document.createElement("div");
    const hasManagerAdviceText = Boolean(managerAdviceBody.textContent?.trim());
    managerAdviceBody.classList.add("after-interview-manager-report__personality-advice-text");
    if (!hasManagerAdviceText) {
      managerAdviceBody.classList.add("after-interview-tab-empty");
      managerAdviceBody.textContent = copy().unavailable;
    }
    const managerAdviceError = document.createElement("div");
    managerAdviceError.className = "alert alert-danger d-none mt-3 mb-0";
    managerAdviceError.setAttribute("role", "alert");
    const managerAdviceEditControls = managerReportEditController.register(
      managerAdviceBody,
      "wellbeing_tips",
      {
        label: copy().managerPersonalityAdviceTitle,
        aiText: hasManagerAdviceText
          ? String(managerAdviceBody.dataset.markdownSource || managerAdviceBody.textContent || "")
          : "",
        fallback: hasManagerAdviceText ? "" : copy().unavailable,
        markdown: true,
      },
    );
    managerAdviceHeader.append(managerAdviceTitle, managerAdviceEditControls);
    managerAdvice.append(managerAdviceHeader, managerAdviceBody, managerAdviceError);
    // Render the existing wellbeing_tips block only once, as its own section.

    managerReportAiTasks.push(async () => {
      await generateContentBlock(
        panel,
        "wellbeing_tips",
        managerAdviceBody,
        managerAdviceError,
      );
      if (!managerAdviceError.classList.contains("d-none")) {
        throw new Error(
          managerAdviceError.textContent?.trim() || copy().sectionGenerationFailed,
        );
      }
      managerAdviceHasGeneratedText = true;
      updateManagerReportGenerateLabel();
    });

    document.addEventListener("talena:manager-personality-updated", (event) => {
      const detail = event.detail || {};
      if (detail.theme && detail.part) {
        renderPersonalityText(detail.theme, detail.part, detail.text || "");
      }
    });

    if (personalityRoot) {
      managerReportCard.appendChild(managerPersonality);
    }
    managerReportCard.appendChild(managerAdvice);

    // Audit is supplementary report metadata, so it follows all content and
    // the decision-support disclaimer instead of interrupting the report top.
    const managerReportAudit = document.createElement("div");
    managerReportAudit.dataset.managerReportActivityPanel = "";
    managerReportAudit.dataset.managerReportActivityUrl = outputRoot?.dataset.managerReportActivityUrl || "";
    managerReportCard.appendChild(managerReportAudit);

    const managerReportEditsLoading = document.createElement("div");
    managerReportEditsLoading.className = "text-center text-muted py-4";
    managerReportEditsLoading.setAttribute("role", "status");
    managerReportEditsLoading.setAttribute("aria-live", "polite");
    const managerReportEditsLoadingText = document.createElement("p");
    managerReportEditsLoadingText.className = "mb-2";
    managerReportEditsLoadingText.textContent = copy().loadingReportEdits;
    const managerReportEditsRetry = document.createElement("button");
    managerReportEditsRetry.type = "button";
    managerReportEditsRetry.className = "btn btn-outline-secondary btn-sm";
    managerReportEditsRetry.textContent = copy().retryReportEdits;
    managerReportEditsRetry.hidden = true;
    managerReportEditsLoading.append(managerReportEditsLoadingText, managerReportEditsRetry);
    panels.get("managerReport").append(managerReportEditsLoading, managerReportCard);
    // Mount after the report card is connected so the initial API response is
    // not discarded by the history component's disconnected-node guard.
    window.TalenaManagerReportActivity?.mount(managerReportAudit);

    const revealManagerReport = () => {
      managerReportEditController.applyAll();
      managerReportEditsLoading.hidden = true;
      managerReportCard.hidden = false;
      pdfButton.disabled = false;
      if (window.feather) window.feather.replace();
    };
    const showManagerReportLoadError = () => {
      managerReportEditsLoadingText.textContent = copy().reportEditsLoadFailed;
      managerReportEditsRetry.hidden = false;
      managerReportEditsRetry.disabled = false;
    };
    managerReportEditsReady.then((result) => {
      if (result.ok) revealManagerReport();
      else showManagerReportLoadError();
    });
    managerReportEditsRetry.addEventListener("click", async () => {
      managerReportEditsRetry.disabled = true;
      managerReportEditsLoadingText.textContent = copy().loadingReportEdits;
      try {
        await managerReportEditController.load();
        revealManagerReport();
      } catch (_error) {
        showManagerReportLoadError();
      }
    });

    const evidenceCard = document.createElement("section");
    evidenceCard.className = "after-interview-tab-card after-interview-evidence-card";
    const evidenceIntro = document.createElement("div");
    evidenceIntro.className = "after-interview-evidence-intro";
    const evidenceKicker = document.createElement("p");
    evidenceKicker.className = "after-interview-evidence-intro__kicker";
    evidenceKicker.textContent = copy().evidenceKicker;
    const evidenceHeading = document.createElement("h3");
    evidenceHeading.className = "after-interview-evidence-intro__title";
    evidenceHeading.textContent = hasCompiledPostInterviewResult
      ? copy().evidenceHeadingReady : copy().evidenceHeading;
    const evidenceLead = document.createElement("p");
    evidenceLead.className = "after-interview-evidence-intro__description";
    evidenceLead.textContent = hasCompiledPostInterviewResult
      ? copy().evidenceLeadReady : copy().evidenceLead;
    const evidenceTip = document.createElement("p");
    evidenceTip.className = "after-interview-evidence-intro__tip";
    const tipIcon = document.createElement("i");
    tipIcon.setAttribute("data-feather", "info");
    tipIcon.setAttribute("aria-hidden", "true");
    const tipText = document.createElement("span");
    tipText.textContent = copy().evidenceTip;
    evidenceTip.append(tipIcon, tipText);
    evidenceIntro.append(evidenceKicker, evidenceHeading, evidenceLead, evidenceTip);
    evidenceCard.append(evidenceIntro, notesRoot, postSection);
    if (hasCompiledPostInterviewResult) {
      // The original section must stay in the DOM for its native regeneration
      // handler, but should not render another heading, status or spinner.
      // The single visible "new compilation" action is immediately below.
      postSection.classList.add("d-none");
      postSection.setAttribute("aria-hidden", "true");
      const rebuildRow = document.createElement("div");
      rebuildRow.className = "after-interview-evidence-rebuild";
      const rebuildDescription = document.createElement("p");
      rebuildDescription.className = "after-interview-evidence-rebuild__text";
      rebuildDescription.textContent = copy().evidenceRebuildHint;
      const rebuildButton = document.createElement("button");
      rebuildButton.type = "button";
      rebuildButton.className = "btn btn-primary";
      rebuildButton.dataset.afterInterviewRebuild = "evidence";
      rebuildButton.textContent = copy().reportRebuild;
      rebuildRow.append(rebuildDescription, rebuildButton);
      evidenceCard.appendChild(rebuildRow);
    }
    panels.get("evidence").appendChild(evidenceCard);

    if (contextNote?.isConnected) panels.get("overview").appendChild(contextNote);
    if (postContent) {
      postContent.classList.add("after-interview-content-source");
      postContent.replaceChildren();
    }

    const notesInput = notesRoot.querySelector("[data-interview-notes-input]");
    const originalSavedNotes = notesInput?.value || "";
    const updateReportStatus = () => {
      if (!hasCompiledPostInterviewResult) return;
      const hasUnsavedNotes = Boolean(notesInput && notesInput.value !== originalSavedNotes);
      const isOutdated = outputRoot?.dataset.postInterviewStatus === "outdated";
      const needsUpdate = hasUnsavedNotes || isOutdated;
      const currentJourneyStep = needsUpdate ? 1 : 2;
      journeySteps.querySelectorAll(".after-interview-journey__step").forEach((step, index) => {
        step.classList.toggle("is-current", index === currentJourneyStep);
        step.classList.toggle("is-done", index < currentJourneyStep);
        if (index === currentJourneyStep) step.setAttribute("aria-current", "step");
        else step.removeAttribute("aria-current");
      });
      // Keep the status box out of view while reports are current.
      // Changed input still displays its existing actionable warning.
      reportStatus.hidden = !needsUpdate;
      reportStatus.classList.toggle("needs-update", needsUpdate);
      reportsRefresh.classList.toggle("needs-update", needsUpdate);
      reportsButton.classList.toggle("needs-update", needsUpdate);
      reportsButton.title = needsUpdate ? copy().reportStatusOutdated : "";
      reportsButton.setAttribute("aria-label", needsUpdate
        ? copy().tabs.reports + ". " + copy().reportStatusOutdated
        : copy().tabs.reports);
      reportStatusTitle.textContent = hasUnsavedNotes
        ? copy().reportStatusUnsaved : needsUpdate ? copy().reportStatusOutdated : "";
      reportStatusDetail.textContent = needsUpdate ? copy().reportStatusDetail : "";
      reportStatusDetail.hidden = !needsUpdate;
      reportsRefresh.title = needsUpdate ? copy().reportRebuildShort : copy().reportRebuild;
      reportsRefresh.setAttribute("aria-label", reportsRefresh.title);
    };
    updateReportStatus();
    notesInput?.addEventListener("input", updateReportStatus);
    document.addEventListener("candidate-interview-question-note-updated", (event) => {
      if (!outputRoot.isConnected) return;
      const changedNotesUrl = event.detail?.notesUrl || "";
      const ownNotesUrl = outputRoot.dataset.questionEvidenceNotesUrl || "";
      if (changedNotesUrl && ownNotesUrl && changedNotesUrl !== ownNotesUrl) return;
      updateReportStatus();
    });

    const runFullCompilation = (trigger) => {
      const nativeButton = postSection.querySelector(
        '[data-post-interview-generate][data-regenerate="true"]'
      );
      if (!nativeButton || nativeButton.disabled) {
        if (trigger.dataset.afterInterviewRebuild === "reports") {
          reportStatus.hidden = false;
          reportStatusTitle.textContent = copy().reportGenerateUnavailable;
          reportStatusDetail.textContent = "";
        } else {
          const error = postSection.querySelector("[data-post-interview-error]");
          if (error) {
            error.textContent = copy().reportGenerateUnavailable;
            error.classList.remove("d-none");
          }
        }
        return;
      }
      trigger.disabled = true;
      trigger.setAttribute("aria-busy", "true");
      const previousContents = [...trigger.childNodes];
      const spinner = document.createElement("span");
      spinner.className = "spinner-border spinner-border-sm";
      spinner.setAttribute("role", "status");
      spinner.setAttribute("aria-label", copy().reportGenerating);
      trigger.replaceChildren(spinner);
      const restoreTrigger = () => {
        trigger.disabled = false;
        trigger.removeAttribute("aria-busy");
        trigger.replaceChildren(...previousContents);
      };
      // Native generation still saves the interview notes and runs the
      // manager report manual-edit confirmation before it begins.
      nativeButton.click();
      // The native stream swaps this entire fragment on success. On an error,
      // it restores its thinking state, so restore our action as well.
      const thinking = postSection.querySelector("[data-post-interview-thinking]");
      if (!thinking) {
        restoreTrigger();
        return;
      }
      let started = !thinking.classList.contains("d-none");
      const watcher = new MutationObserver(() => {
        if (!outputRoot.isConnected) {
          watcher.disconnect();
          return;
        }
        if (!thinking.classList.contains("d-none")) {
          started = true;
        } else if (started) {
          restoreTrigger();
          watcher.disconnect();
          const error = postSection.querySelector("[data-post-interview-error]");
          if (error && !error.classList.contains("d-none")) {
            reportStatus.hidden = false;
            reportStatus.classList.add("needs-update");
            reportStatusTitle.textContent = error.textContent.trim() || copy().reportError;
            reportStatusDetail.textContent = copy().reportStatusDetail;
          } else {
            updateReportStatus();
          }
        }
      });
      watcher.observe(thinking, { attributes: true, attributeFilter: ["class"] });
      // A confirmation dialog may delay the original click. Do not retain a
      // disabled proxy while the user is deciding whether to regenerate.
      if (!started) {
        restoreTrigger();
        watcher.disconnect();
      }
    };
    tabs.querySelectorAll("[data-after-interview-rebuild]").forEach((trigger) => {
      trigger.addEventListener("click", () => runFullCompilation(trigger));
    });

    let activeReportKey = "overview";
    const activate = (key, updateUrl = true) => {
      const activeKey = keys.includes(key) &&
        (hasCompiledPostInterviewResult || key === "evidence")
        ? key : "evidence";
      const reportsActive = activeKey !== "evidence";
      if (reportsActive) activeReportKey = activeKey;
      evidenceButton.classList.toggle("is-active", !reportsActive);
      evidenceButton.setAttribute("aria-selected", String(!reportsActive));
      reportsButton.classList.toggle("is-active", reportsActive);
      reportsButton.setAttribute("aria-selected", String(reportsActive));
      evidencePanel.hidden = reportsActive;
      reportsArea.hidden = !reportsActive;
      reportKeys.forEach((reportKey) => {
        const button = buttons.get(reportKey);
        const active = reportsActive && reportKey === activeKey;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
        panels.get(reportKey).hidden = !active;
      });
      updateReportStatus();
      if (updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set(URL_PARAM, activeKey);
        window.history.replaceState({}, "", url);
      }
    };

    primaryNav.addEventListener("click", (event) => {
      const target = event.target.closest("[data-after-interview-primary-tab], [data-after-interview-tab]");
      if (!target || target.disabled) return;
      if (target.dataset.afterInterviewPrimaryTab === "reports") {
        activate(activeReportKey);
      } else if (target.dataset.afterInterviewTab === "evidence") {
        activate("evidence");
      }
    });
    reportNav.addEventListener("click", (event) => {
      const button = event.target.closest("[data-after-interview-tab]");
      if (button && !button.disabled) activate(button.dataset.afterInterviewTab);
    });

    const url = new URL(window.location.href);
    const requested = url.searchParams.get(URL_PARAM);
    const restoreRequested =
      !candidateChanged && !justCompiled &&
      keys.includes(requested) &&
      (hasCompiledPostInterviewResult || requested === "evidence");
    const initial = restoreRequested
      ? requested
      : hasCompiledPostInterviewResult ? "overview" : "evidence";
    activate(initial, false);
    if ((requested && requested !== initial) || url.searchParams.has("afterTestTab")) {
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
  window.initAfterInterviewTabs = scan;

  // The outer insights panel can be reactivated after an async root refresh.
  // Re-scan after the tab switch so a panel whose markup arrived late is initialized.
  document.addEventListener("click", (event) => {
    if (event.target.closest?.("[data-insights-tab]")) {
      window.requestAnimationFrame(() => scan(document));
    }
  });

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
