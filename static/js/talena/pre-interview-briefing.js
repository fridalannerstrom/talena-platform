(() => {
  "use strict";

  const initialisedRoots = new WeakSet();
  const loadingRoots = new WeakSet();

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const copy = () =>
    isSwedish()
      ? {
          briefingKicker: "Kandidatspecifik briefing",
          summaryTitle: "Kandidatbild inför intervjun",
          focusTitle: "Viktigaste indikationerna",
          focusIntro:
            "De här mönstren framträder som mest relevanta i kandidatens testunderlag och den tillgängliga processkontexten.",
          validateTitle: "Hypoteser att validera",
          validateIntro:
            "Använd intervjun för att bekräfta, nyansera eller utmana dessa indikationer.",
          cautionReason: "Varför det behöver valideras",
          approachTitle: "Så når du fram i samtalet",
          approachIntro:
            "Hur du kan anpassa ton, direkthet, tempo och uppföljning för att få fram en så rättvis och nyanserad bild som möjligt.",
          approachSectionTitle: "Kommunikationsstrategi",
        }
      : {
          briefingKicker: "Candidate-specific briefing",
          summaryTitle: "Candidate briefing before the interview",
          focusTitle: "Key indications",
          focusIntro:
            "These patterns emerge as most relevant in the candidate's assessment evidence and available process context.",
          validateTitle: "Hypotheses to validate",
          validateIntro:
            "Use the interview to confirm, nuance or challenge these indications.",
          cautionReason: "Why this needs validation",
          approachTitle: "How to reach this candidate in conversation",
          approachIntro:
            "How to adapt tone, directness, pace and follow-up to obtain the fairest and most nuanced picture possible.",
          approachSectionTitle: "Communication strategy",
        };

  const safeArray = (value) => (Array.isArray(value) ? value : []);

  const parseEventLine = (rawLine) => {
    let line = String(rawLine || "").trim();
    if (!line || line.startsWith("event:")) return null;
    if (line.startsWith("data:")) line = line.slice(5).trim();
    if (!line || line === "[DONE]") return null;

    try {
      const parsed = JSON.parse(line);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_error) {
      return null;
    }
  };

  const applyEvent = (draft, event) => {
    if (!event) return draft;

    switch (event.type) {
      case "saved_result":
        return {
          ...draft,
          ...(event.data && typeof event.data === "object" ? event.data : {}),
        };

      case "overall_synthesis_delta":
        draft.overall_synthesis =
          (draft.overall_synthesis || "") + String(event.text || "");
        break;

      case "purpose_relevant_indications":
        draft.purpose_relevant_indications = safeArray(event.items);
        break;

      case "cautious_interpretations":
        draft.cautious_interpretations = safeArray(event.items);
        break;

      case "discussion_guidance":
        draft.discussion_guidance = {
          feedback_approach: safeArray(event.feedback_approach),
          interview_focus: safeArray(event.interview_focus),
        };
        break;

      case "evidence_gaps":
        draft.evidence_gaps = safeArray(event.items);
        break;

      default:
        break;
    }

    return draft;
  };

  const readSavedBriefing = async (root) => {
    const streamUrl = root.dataset.preInterviewStreamUrl || "";
    if (!streamUrl) return null;

    const response = await fetch(streamUrl, {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/x-ndjson, application/json, text/plain",
      },
      credentials: "same-origin",
    });

    if (!response.ok) return null;

    const body = await response.text();
    let draft = {
      overall_synthesis: "",
      purpose_relevant_indications: [],
      cautious_interpretations: [],
      discussion_guidance: {
        feedback_approach: [],
        interview_focus: [],
      },
      evidence_gaps: [],
    };

    body.split(/\r?\n/).forEach((line) => {
      draft = applyEvent(draft, parseEventLine(line));
    });

    return draft;
  };

  const makeIcon = (name) => {
    const icon = document.createElement("i");
    icon.dataset.feather = name;
    icon.setAttribute("aria-hidden", "true");
    return icon;
  };

  const makeSectionHeader = (title, intro, iconName) => {
    const header = document.createElement("div");
    header.className = "pre-interview-briefing-card__header";

    const icon = document.createElement("span");
    icon.className = "pre-interview-briefing-card__icon";
    icon.appendChild(makeIcon(iconName));

    const text = document.createElement("div");

    const heading = document.createElement("div");
    heading.className = "pre-interview-briefing-card__title";
    heading.textContent = title;

    const description = document.createElement("div");
    description.className = "pre-interview-briefing-card__intro";
    description.textContent = intro;

    text.append(heading, description);
    header.append(icon, text);
    return header;
  };

  const buildFocusCard = (items) => {
    const indications = safeArray(items)
      .map((item) => {
        if (item && typeof item === "object") {
          return {
            title: String(item.title || "").trim(),
            interpretation: String(item.interpretation || "").trim(),
          };
        }

        return {
          title: "",
          interpretation: String(item || "").trim(),
        };
      })
      .filter((item) => item.title || item.interpretation);

    if (!indications.length) return null;

    const labels = copy();
    const card = document.createElement("section");
    card.className = "pre-interview-briefing-card pre-interview-briefing-card--focus";
    card.appendChild(makeSectionHeader(labels.focusTitle, labels.focusIntro, "target"));

    const list = document.createElement("div");
    list.className = "pre-interview-validation-list";

    indications.forEach((item) => {
      const article = document.createElement("article");
      article.className = "pre-interview-validation-item";

      if (item.title) {
        const heading = document.createElement("div");
        heading.className = "pre-interview-validation-item__title";
        heading.textContent = item.title;
        article.appendChild(heading);
      }

      if (item.interpretation) {
        const body = document.createElement("div");
        body.className = "pre-interview-validation-item__text";
        body.textContent = item.interpretation;
        article.appendChild(body);
      }

      if (article.childElementCount) list.appendChild(article);
    });

    if (!list.childElementCount) return null;
    card.appendChild(list);
    return card;
  };

  const buildValidationCard = (items) => {
    const hypotheses = safeArray(items).filter(
      (item) => item && typeof item === "object",
    );

    if (!hypotheses.length) return null;

    const labels = copy();
    const card = document.createElement("section");
    card.className = "pre-interview-briefing-card pre-interview-briefing-card--validate";
    card.appendChild(
      makeSectionHeader(labels.validateTitle, labels.validateIntro, "search"),
    );

    const list = document.createElement("div");
    list.className = "pre-interview-validation-list";

    hypotheses.forEach((item) => {
      const article = document.createElement("article");
      article.className = "pre-interview-validation-item";

      const title = String(item.title || "").trim();
      if (title) {
        const heading = document.createElement("div");
        heading.className = "pre-interview-validation-item__title";
        heading.textContent = title;
        article.appendChild(heading);
      }

      const interpretation = String(item.interpretation || "").trim();
      if (interpretation) {
        const body = document.createElement("div");
        body.className = "pre-interview-validation-item__text";
        body.textContent = interpretation;
        article.appendChild(body);
      }

      const reason = String(item.reason_for_caution || "").trim();
      if (reason) {
        const reasonWrap = document.createElement("div");
        reasonWrap.className = "pre-interview-validation-item__reason";

        const reasonLabel = document.createElement("span");
        reasonLabel.className = "pre-interview-validation-item__reason-label";
        reasonLabel.textContent = `${labels.cautionReason}:`;

        const reasonText = document.createElement("span");
        reasonText.textContent = reason;

        reasonWrap.append(reasonLabel, document.createTextNode(" "), reasonText);
        article.appendChild(reasonWrap);
      }

      if (article.childElementCount) list.appendChild(article);
    });

    if (!list.childElementCount) return null;
    card.appendChild(list);
    return card;
  };

  const renderConversationApproach = (responseSection, items) => {
    if (!responseSection) return;

    const strings = safeArray(items)
      .map((item) => String(item || "").trim())
      .filter(Boolean);

    const content = responseSection.querySelector(
      "[data-response-style-interview-content]",
    );
    const approachSection = responseSection.querySelector(
      "[data-response-style-interview-approach-section]",
    );
    const approach = responseSection.querySelector(
      "[data-response-style-interview-approach]",
    );

    if (!strings.length || !approach) {
      responseSection.hidden = true;
      return;
    }

    responseSection.hidden = false;
    if (content) content.hidden = false;
    if (approachSection) approachSection.hidden = false;

    approach.replaceChildren();

    const list = document.createElement("ul");
    list.className = "purpose-fit-list mt-0";
    list.dataset.preInterviewConversationPlan = "";

    strings.forEach((item) => {
      const li = document.createElement("li");

      const icon = document.createElement("span");
      icon.className = "purpose-fit-list-icon";
      icon.appendChild(makeIcon("message-circle"));

      const text = document.createElement("span");
      text.textContent = item;

      li.append(icon, text);
      list.appendChild(li);
    });

    approach.appendChild(list);
  };

  const polishExistingContent = (root) => {
    const labels = copy();
    const content = root.querySelector("[data-pre-interview-content]");
    if (!content) return null;

    const summary = content.querySelector("[data-pre-interview-overall-synthesis]");
    const summarySection = summary?.closest(".purpose-fit-section");

    if (summarySection) {
      summarySection.classList.add("pre-interview-briefing-summary");
      const heading = summarySection.querySelector(".purpose-fit-section-title");
      if (heading) heading.textContent = labels.summaryTitle;

      if (!summarySection.querySelector("[data-pre-interview-briefing-kicker]")) {
        const kicker = document.createElement("div");
        kicker.className = "pre-interview-briefing-kicker";
        kicker.dataset.preInterviewBriefingKicker = "";
        kicker.textContent = labels.briefingKicker;
        summarySection.insertBefore(kicker, heading || summarySection.firstChild);
      }
    }

    const responseSection = content.querySelector(
      "[data-response-style-interview-guidance]",
    );
    const responseQuestions = content.querySelector(
      "[data-response-style-interview-questions-section]",
    );

    if (responseQuestions) responseQuestions.hidden = true;

    if (responseSection) {
      const title = responseSection.querySelector(".insight-summary-title");
      if (title) title.textContent = labels.approachTitle;

      const subtitle = responseSection.querySelector(
        ":scope > div:first-child .text-muted.small",
      );
      if (subtitle) subtitle.textContent = labels.approachIntro;

      const approachTitle = responseSection.querySelector(
        "[data-response-style-interview-approach-section] .purpose-fit-section-title",
      );
      if (approachTitle) approachTitle.textContent = labels.approachSectionTitle;

      // The legacy response-style-only paragraph is intentionally hidden until
      // the candidate-specific communication approach is loaded.
      responseSection.hidden = true;
    }

    return { content, summarySection, responseSection };
  };

  const renderBriefing = (root, data) => {
    const pieces = polishExistingContent(root);
    if (!pieces || !data) return;

    pieces.content
      .querySelectorAll("[data-pre-interview-briefing-grid]")
      .forEach((node) => node.remove());

    const approachItems = safeArray(data.discussion_guidance?.feedback_approach);
    const purposeIndications = safeArray(data.purpose_relevant_indications);
    const fallbackFocusItems = safeArray(data.discussion_guidance?.interview_focus);
    const focusItems = purposeIndications.length
      ? purposeIndications
      : fallbackFocusItems;
    const validationItems = safeArray(data.cautious_interpretations);

    renderConversationApproach(pieces.responseSection, approachItems);

    const focusCard = buildFocusCard(focusItems);
    const validationCard = buildValidationCard(validationItems);

    if (focusCard || validationCard) {
      const grid = document.createElement("div");
      grid.className = "pre-interview-briefing-grid";
      grid.dataset.preInterviewBriefingGrid = "";

      if (focusCard) grid.appendChild(focusCard);
      if (validationCard) grid.appendChild(validationCard);

      const anchor = pieces.responseSection || pieces.summarySection?.nextSibling || null;
      pieces.content.insertBefore(grid, anchor);
    }

    if (window.feather) window.feather.replace();
  };

  const initialiseRoot = async (root) => {
    if (!(root instanceof Element)) return;
    if (initialisedRoots.has(root) || loadingRoots.has(root)) return;

    polishExistingContent(root);

    if (root.dataset.hasPreInterviewResult !== "true") {
      initialisedRoots.add(root);
      return;
    }

    loadingRoots.add(root);

    try {
      const data = await readSavedBriefing(root);
      if (data) renderBriefing(root, data);
    } catch (_error) {
      // Progressive enhancement only. Existing interview preparation remains usable.
    } finally {
      loadingRoots.delete(root);
      initialisedRoots.add(root);
    }
  };

  const initialise = (root = document) => {
    if (root instanceof Element && root.matches("[data-decision-support-root]")) {
      initialiseRoot(root);
    }

    root.querySelectorAll?.("[data-decision-support-root]").forEach(initialiseRoot);
  };

  document.addEventListener("DOMContentLoaded", () => initialise(document));

  document.addEventListener("candidate-ai-content-updated", () => {
    document.querySelectorAll("[data-decision-support-root]").forEach((root) => {
      initialisedRoots.delete(root);
      initialiseRoot(root);
    });
  });

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node instanceof Element) initialise(node);
      });
    });
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
