(() => {
  "use strict";

  const notesCache = new Map();
  const pendingLoads = new Map();

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const text = (key) => {
    const sv = {
      answerNotes: "Svar / anteckningar",
      hint: "Skriv din anteckning och klicka på Spara. Sparade svar finns tillgängliga i hela kandidatvyn.",
      placeholder: "Lägg till kandidatens svar, exempel eller dina intervjuanteckningar…",
      save: "Spara",
      saving: "Sparar…",
      saved: "Sparat",
      error: "Kunde inte spara",
      summaryTitle: "Sparade svar från intervjufrågor",
      summaryIntro:
        "Svar och anteckningar som sparats direkt på intervjufrågorna samlas här automatiskt.",
      empty: "Inga svar har sparats på intervjufrågorna ännu.",
      personality: "Personlighet",
      motivation: "Motivation",
      cognitive: "Kognitivt",
      edit: "Redigera",
      saveChanges: "Spara ändringar",
      cancel: "Avbryt",
      delete: "Ta bort",
      deleting: "Tar bort…",
      deleteConfirm: "Vill du ta bort det här sparade svaret?",
    };

    const en = {
      answerNotes: "Answer / notes",
      hint: "Write your note and click Save. Saved answers are available across the candidate view.",
      placeholder: "Add the candidate's answer, examples or your interview notes…",
      save: "Save",
      saving: "Saving…",
      saved: "Saved",
      error: "Could not save",
      summaryTitle: "Saved answers from interview questions",
      summaryIntro:
        "Answers and notes saved directly on interview questions are collected here automatically.",
      empty: "No answers have been saved on interview questions yet.",
      personality: "Personality",
      motivation: "Motivation",
      cognitive: "Cognitive",
      edit: "Edit",
      saveChanges: "Save changes",
      cancel: "Cancel",
      delete: "Delete",
      deleting: "Deleting…",
      deleteConfirm: "Do you want to remove this saved answer?",
    };

    return (isSwedish() ? sv : en)[key] || key;
  };

  const getCookie = (name) => {
    const cookies = document.cookie ? document.cookie.split(";") : [];

    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(`${name}=`)) {
        return decodeURIComponent(trimmed.slice(name.length + 1));
      }
    }

    return "";
  };

  const noteIdentity = (source, question) => `${source}\u0000${question}`;

  const selectWithin = (root, selector) => {
    const matches = [];
    if (root instanceof Element && root.matches(selector)) matches.push(root);
    if (root?.querySelectorAll) matches.push(...root.querySelectorAll(selector));
    return matches;
  };

  const routeUrlsFromRoot = (root) => {
    if (!root) return null;

    const rawUrl =
      root.dataset.streamUrl ||
      root.dataset.refreshUrl ||
      root.dataset.regenerateUrl ||
      "";

    if (!rawUrl) return null;

    let parsed;
    try {
      parsed = new URL(rawUrl, window.location.origin);
    } catch (_error) {
      return null;
    }

    const match = parsed.pathname.match(/^(.*\/)(\d+)\/candidates?\/(\d+)\//);
    if (!match) return null;

    const [, prefix, processId, candidateId] = match;
    const base = `${prefix}${processId}/candidates/${candidateId}/interview-question-notes/`;

    return {
      notesUrl: `${parsed.origin}${base}`,
      updateUrl: `${parsed.origin}${base}update/`,
    };
  };

  const questionTextForCard = (card) =>
    (card.querySelector(".personality-question-card__text")?.textContent || "")
      .replace(/\s+/g, " ")
      .trim();

  const sourceFromIndividualCard = (card) => {
    if (card.closest("[data-personality-questions-root]")) return "personality";
    if (card.closest("[data-motivation-questions-root]")) return "motivation";
    if (card.closest("[data-cognitive-questions-root]")) return "cognitive";
    return "";
  };

  const sourceFromKnownQuestion = (question) => {
    const selectors = [
      ["[data-personality-questions-root]", "personality"],
      ["[data-motivation-questions-root]", "motivation"],
      ["[data-cognitive-questions-root]", "cognitive"],
    ];

    for (const [selector, source] of selectors) {
      const cards = document.querySelectorAll(`${selector} .personality-question-card`);
      for (const card of cards) {
        if (questionTextForCard(card) === question) return source;
      }
    }

    return "";
  };

  const sourceFromCombinedSection = (card) => {
    const section = card.closest(".combined-question-sections > section");
    const heading = (
      section?.querySelector(".personality-questions-section-title")?.textContent || ""
    )
      .toLowerCase()
      .trim();

    if (heading.includes("person")) return "personality";
    if (heading.includes("motivat")) return "motivation";
    if (heading.includes("cogn") || heading.includes("kogn")) return "cognitive";
    return "";
  };

  const questionContextForCard = (card) => {
    const question = questionTextForCard(card);
    if (!question) return null;

    let source = sourceFromIndividualCard(card);

    const root =
      card.closest("[data-personality-questions-root]") ||
      card.closest("[data-motivation-questions-root]") ||
      card.closest("[data-cognitive-questions-root]") ||
      card.closest("[data-combined-questions-root]");

    if (!source && card.closest("[data-combined-questions-root]")) {
      source = sourceFromKnownQuestion(question) || sourceFromCombinedSection(card);
    }

    const urls = routeUrlsFromRoot(root);
    if (!source || !urls) return null;

    return { question, source, ...urls };
  };

  const buttonForField = (field) =>
    field
      .closest("[data-interview-question-note-field]")
      ?.querySelector("[data-interview-question-note-save]") || null;

  const setDirtyState = (field) => {
    const button = buttonForField(field);
    if (!button) return;

    const dirty = field.value.trim() !== (field.dataset.savedValue || "");
    button.disabled = !dirty;
    button.classList.toggle("is-dirty", dirty);
  };

  const setStatus = (field, state) => {
    const root = field.closest("[data-interview-question-note-field]");
    const status = root?.querySelector("[data-interview-question-note-status]");
    const button = buttonForField(field);

    if (status) {
      status.classList.remove("is-saving", "is-saved", "is-error");

      if (!state) {
        status.textContent = "";
      } else {
        status.classList.add(`is-${state}`);
        status.textContent = text(state);
      }
    }

    if (button) {
      if (state === "saving") {
        button.disabled = true;
        button.classList.add("is-saving");
        button.textContent = text("saving");
      } else {
        button.classList.remove("is-saving");
        button.textContent = text("save");
        setDirtyState(field);
      }
    }
  };

  const createQuestionNoteField = (context) => {
    const wrapper = document.createElement("div");
    wrapper.className = "interview-question-note";
    wrapper.dataset.interviewQuestionNoteField = "";

    const header = document.createElement("div");
    header.className = "interview-question-note__header";

    const label = document.createElement("label");
    label.className = "interview-question-note__label";

    const icon = document.createElement("i");
    icon.dataset.feather = "message-square";
    icon.setAttribute("aria-hidden", "true");

    const labelText = document.createElement("span");
    labelText.textContent = text("answerNotes");
    label.append(icon, labelText);

    const status = document.createElement("span");
    status.className = "interview-question-note__status";
    status.dataset.interviewQuestionNoteStatus = "";
    status.setAttribute("aria-live", "polite");

    header.append(label, status);

    const field = document.createElement("textarea");
    field.className = "form-control interview-question-note__input";
    field.rows = 2;
    field.maxLength = 5000;
    field.placeholder = text("placeholder");
    field.dataset.interviewQuestionNote = "";
    field.dataset.questionSource = context.source;
    field.dataset.questionText = context.question;
    field.dataset.notesUrl = context.notesUrl;
    field.dataset.updateUrl = context.updateUrl;
    field.dataset.savedValue = "";

    const footer = document.createElement("div");
    footer.className = "interview-question-note__footer";

    const hint = document.createElement("div");
    hint.className = "interview-question-note__hint";
    hint.textContent = text("hint");

    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "interview-question-note__save";
    saveButton.dataset.interviewQuestionNoteSave = "";
    saveButton.textContent = text("save");
    saveButton.disabled = true;

    footer.append(hint, saveButton);
    wrapper.append(header, field, footer);
    return wrapper;
  };

  const ensureQuestionFields = (root = document) => {
    selectWithin(root, ".personality-question-card").forEach((card) => {
      if (card.querySelector("[data-interview-question-note-field]")) return;

      const context = questionContextForCard(card);
      if (!context) return;

      card.appendChild(createQuestionNoteField(context));
    });

    if (window.feather) window.feather.replace();
  };

  const ensureSummary = (root = document) => {
    const notesRoot =
      (root instanceof Element && root.matches("[data-interview-notes-root]")
        ? root
        : root.querySelector?.("[data-interview-notes-root]")) || null;

    if (!notesRoot || notesRoot.querySelector("[data-interview-question-notes-summary]")) {
      return;
    }

    const finalRoot = notesRoot.closest("[data-final-output-root]");
    const urls = routeUrlsFromRoot(finalRoot);
    if (!urls) return;

    const summary = document.createElement("section");
    summary.className = "interview-question-notes-summary";
    summary.dataset.interviewQuestionNotesSummary = "";
    summary.dataset.notesUrl = urls.notesUrl;
    summary.dataset.updateUrl = urls.updateUrl;

    const title = document.createElement("div");
    title.className = "purpose-fit-section-title mb-1";
    title.textContent = text("summaryTitle");

    const intro = document.createElement("div");
    intro.className = "interview-question-notes-summary__intro";
    intro.textContent = text("summaryIntro");

    const list = document.createElement("div");
    list.className = "interview-question-notes-summary__list";
    list.dataset.interviewQuestionNotesSummaryList = "";

    const empty = document.createElement("div");
    empty.className = "small text-muted";
    empty.dataset.interviewQuestionNotesSummaryEmpty = "";
    empty.textContent = text("empty");

    summary.append(title, intro, list, empty);
    notesRoot.appendChild(summary);
  };

  const sourceLabel = (source, backendLabel = "") => {
    if (source === "personality") return text("personality");
    if (source === "motivation") return text("motivation");
    if (source === "cognitive") return text("cognitive");
    return backendLabel || source;
  };

  const syncFields = (url, source, question, note, markSaved = false) => {
    document.querySelectorAll("[data-interview-question-note]").forEach((field) => {
      if (
        field.dataset.notesUrl === url &&
        field.dataset.questionSource === source &&
        field.dataset.questionText === question
      ) {
        if (field.value !== note) field.value = note;
        field.dataset.savedValue = note;
        setDirtyState(field);
        if (markSaved) setStatus(field, "saved");
      }
    });
  };

  const createSummaryActionButton = (labelKey, dataKey, className) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.dataset[dataKey] = "";
    button.textContent = text(labelKey);
    return button;
  };

  const createSummaryEditor = (url, item) => {
    const editor = createQuestionNoteField({
      source: item.source || "",
      question: item.question || "",
      notesUrl: url,
      updateUrl: item.updateUrl || "",
    });
    editor.classList.add("interview-question-note--summary");

    const field = editor.querySelector("[data-interview-question-note]");
    if (field) {
      field.value = item.note || "";
      field.dataset.savedValue = item.note || "";
    }

    const saveButton = editor.querySelector("[data-interview-question-note-save]");
    if (saveButton) saveButton.textContent = text("saveChanges");

    return editor;
  };

  const createSummaryMutationField = (url, article, note) => {
    const wrapper = document.createElement("div");
    wrapper.dataset.interviewQuestionNoteField = "";

    const field = document.createElement("textarea");
    field.dataset.interviewQuestionNote = "";
    field.dataset.questionSource = article.dataset.questionSource || "";
    field.dataset.questionText = article.dataset.questionText || "";
    field.dataset.notesUrl = url;
    field.dataset.updateUrl = article.dataset.updateUrl || `${url}update/`;
    field.dataset.savedValue = article.dataset.noteValue || "";
    field.value = note;

    wrapper.appendChild(field);
    return field;
  };

  const showSummaryError = (article, message = text("error")) => {
    if (!article) return;

    let error = article.querySelector(
      "[data-interview-question-notes-summary-error]",
    );
    if (!error) {
      error = document.createElement("div");
      error.className = "interview-question-notes-summary__error";
      error.dataset.interviewQuestionNotesSummaryError = "";
      article.appendChild(error);
    }
    error.textContent = message;
  };

  const renderSummary = (url) => {
    const notes = notesCache.get(url) || [];

    document
      .querySelectorAll("[data-interview-question-notes-summary]")
      .forEach((root) => {
        if (root.dataset.notesUrl !== url) return;

        const list = root.querySelector("[data-interview-question-notes-summary-list]");
        const empty = root.querySelector("[data-interview-question-notes-summary-empty]");
        if (!list || !empty) return;

        list.replaceChildren();

        const visibleNotes = notes.filter((item) => (item.note || "").trim());
        empty.classList.toggle("d-none", visibleNotes.length > 0);

        visibleNotes.forEach((item) => {
          const article = document.createElement("article");
          article.className = "interview-question-notes-summary__item";
          article.dataset.interviewQuestionNotesSummaryItem = "";
          article.dataset.notesUrl = url;
          article.dataset.updateUrl = root.dataset.updateUrl || `${url}update/`;
          article.dataset.questionSource = item.source || "";
          article.dataset.questionText = item.question || "";
          article.dataset.noteValue = item.note || "";

          const meta = document.createElement("div");
          meta.className = "interview-question-notes-summary__meta";

          const source = document.createElement("span");
          source.className = "interview-question-notes-summary__source";
          source.textContent = sourceLabel(item.source, item.source_label);
          meta.appendChild(source);

          const question = document.createElement("div");
          question.className = "interview-question-notes-summary__question";
          question.textContent = item.question || "";

          const note = document.createElement("div");
          note.className = "interview-question-notes-summary__note";
          note.textContent = item.note || "";

          const actions = document.createElement("div");
          actions.className = "interview-question-notes-summary__actions";

          const edit = createSummaryActionButton(
            "edit",
            "interviewQuestionNotesSummaryEdit",
            "interview-question-notes-summary__action interview-question-notes-summary__action--edit",
          );
          const remove = createSummaryActionButton(
            "delete",
            "interviewQuestionNotesSummaryDelete",
            "interview-question-notes-summary__action interview-question-notes-summary__action--delete",
          );

          edit.addEventListener("click", () => enterSummaryEdit(article));
          remove.addEventListener("click", () => deleteSummaryItem(article));

          actions.append(edit, remove);
          article.append(meta, question, note, actions);
          list.appendChild(article);
        });
      });
  };

  const enterSummaryEdit = (article) => {
    if (!article || article.dataset.editing === "true") return;

    const url = article.dataset.notesUrl || "";
    const note = article.querySelector(".interview-question-notes-summary__note");
    if (!url || !note) return;

    const editor = createSummaryEditor(url, {
      source: article.dataset.questionSource || "",
      question: article.dataset.questionText || "",
      note: article.dataset.noteValue || note.textContent || "",
      updateUrl: article.dataset.updateUrl || `${url}update/`,
    });
    note.replaceWith(editor);
    article.dataset.editing = "true";

    const edit = article.querySelector("[data-interview-question-notes-summary-edit]");
    if (edit) {
      edit.removeAttribute("data-interview-question-notes-summary-edit");
      edit.textContent = text("cancel");
      edit.addEventListener("click", () => {
        const currentUrl = article.dataset.notesUrl || "";
        if (currentUrl) renderSummary(currentUrl);
      }, { once: true });
    }

    const field = editor.querySelector("[data-interview-question-note]");
    field?.focus();
    field?.setSelectionRange(field.value.length, field.value.length);
  };

  const deleteSummaryItem = async (article) => {
    if (!article || article.dataset.deleting === "true") return;
    if (!window.confirm(text("deleteConfirm"))) return;

    const url = article.dataset.notesUrl || "";
    const button = article.querySelector("[data-interview-question-notes-summary-delete]");
    if (!url || !button) return;

    article.dataset.deleting = "true";
    button.disabled = true;
    button.textContent = text("deleting");

    const field = createSummaryMutationField(url, article, "");
    const deleted = await saveField(field);

    if (!deleted && article.isConnected) {
      article.dataset.deleting = "false";
      button.disabled = false;
      button.textContent = text("delete");
      showSummaryError(article);
    }
  };

  const applyNotes = (url, notes) => {
    notesCache.set(url, Array.isArray(notes) ? notes : []);

    (notesCache.get(url) || []).forEach((item) => {
      syncFields(
        url,
        item.source || "",
        item.question || "",
        item.note || "",
        false,
      );
    });

    document.querySelectorAll("[data-interview-question-note]").forEach((field) => {
      if (field.dataset.notesUrl !== url) return;

      const identity = noteIdentity(
        field.dataset.questionSource || "",
        field.dataset.questionText || "",
      );

      const matching = (notesCache.get(url) || []).find(
        (item) => noteIdentity(item.source || "", item.question || "") === identity,
      );

      if (!matching) {
        field.dataset.savedValue = field.value || "";
        setDirtyState(field);
      }
    });

    renderSummary(url);
  };

  const loadNotes = async (url) => {
    if (!url) return [];
    if (notesCache.has(url)) {
      applyNotes(url, notesCache.get(url));
      return notesCache.get(url);
    }
    if (pendingLoads.has(url)) return pendingLoads.get(url);

    const promise = fetch(url, {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Could not load notes.");
        applyNotes(url, payload.notes || []);
        return payload.notes || [];
      })
      .catch(() => {
        notesCache.set(url, []);
        return [];
      })
      .finally(() => pendingLoads.delete(url));

    pendingLoads.set(url, promise);
    return promise;
  };

  const updateCache = (url, savedNote) => {
    const notes = [...(notesCache.get(url) || [])];
    const identity = noteIdentity(savedNote.source || "", savedNote.question || "");
    const index = notes.findIndex(
      (item) => noteIdentity(item.source || "", item.question || "") === identity,
    );

    if ((savedNote.note || "").trim()) {
      if (index >= 0) notes[index] = savedNote;
      else notes.push(savedNote);
    } else if (index >= 0) {
      notes.splice(index, 1);
    }

    notesCache.set(url, notes);
    renderSummary(url);
  };

  const markPostInterviewOutdated = (status) => {
    if (status !== "outdated") return;

    document.querySelectorAll("[data-post-interview-status-badge]").forEach((badge) => {
      badge.classList.remove("d-none");
    });

    document.querySelectorAll("[data-post-interview-outdated]").forEach((warning) => {
      warning.classList.remove("d-none");
    });

    const root = document.querySelector("[data-final-output-root]");
    if (root) root.dataset.postInterviewStatus = "outdated";
  };

  const saveField = async (field) => {
    const updateUrl = field.dataset.updateUrl || "";
    const notesUrl = field.dataset.notesUrl || "";
    const source = field.dataset.questionSource || "";
    const question = field.dataset.questionText || "";
    const note = field.value.trim();

    if (!updateUrl || !notesUrl || !source || !question) return false;
    if ((field.dataset.savedValue || "") === note) {
      setDirtyState(field);
      return false;
    }

    setStatus(field, "saving");

    try {
      const response = await fetch(updateUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
        body: JSON.stringify({ source, question, note }),
      });

      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Could not save note.");

      const savedNote = {
        ...(payload.note || {}),
        source,
        question,
        note,
      };

      syncFields(notesUrl, source, question, note, true);
      updateCache(notesUrl, savedNote);
      markPostInterviewOutdated(payload.post_interview_status);

      document.dispatchEvent(
        new CustomEvent("candidate-interview-question-note-updated", {
          detail: { source, question, note, notesUrl },
        }),
      );
      return true;
    } catch (error) {
      console.error("Interview question note update failed:", error);
      setStatus(field, "error");
      return false;
    }
  };

  const initialise = (root = document) => {
    ensureQuestionFields(root);
    ensureSummary(root);

    const urls = new Set();

    selectWithin(root, "[data-interview-question-note]").forEach((field) => {
      if (field.dataset.notesUrl) urls.add(field.dataset.notesUrl);
    });

    selectWithin(root, "[data-interview-question-notes-summary]").forEach((summary) => {
      if (summary.dataset.notesUrl) urls.add(summary.dataset.notesUrl);
    });

    urls.forEach((url) => loadNotes(url));
  };

  document.addEventListener("input", (event) => {
    const field = event.target.closest?.("[data-interview-question-note]");
    if (!field) return;

    setStatus(field, "");
    setDirtyState(field);
  });

  document.addEventListener("click", (event) => {
    const button = event.target.closest?.("[data-interview-question-note-save]");
    if (!button) return;

    const root = button.closest("[data-interview-question-note-field]");
    const field = root?.querySelector("[data-interview-question-note]");
    if (!field || button.disabled) return;

    saveField(field);
  });

  document.addEventListener("DOMContentLoaded", () => initialise(document));

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (!(node instanceof Element)) continue;
        initialise(node);
      }
    }
  });

  observer.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
