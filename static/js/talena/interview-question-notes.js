(() => {
  "use strict";

  const saveTimers = new WeakMap();
  const notesCache = new Map();
  const pendingLoads = new Map();

  const isSwedish = () =>
    (document.documentElement.lang || "").toLowerCase().startsWith("sv");

  const text = (key) => {
    const sv = {
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
    };

    const en = {
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

  const setStatus = (field, state) => {
    const root = field.closest("[data-interview-question-note-field]");
    const status = root?.querySelector("[data-interview-question-note-status]");
    if (!status) return;

    status.classList.remove("is-saving", "is-saved", "is-error");

    if (!state) {
      status.textContent = "";
      return;
    }

    status.classList.add(`is-${state}`);
    status.textContent = text(state);
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
        if (markSaved) setStatus(field, "saved");
      }
    });
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
          article.dataset.questionSource = item.source || "";
          article.dataset.questionText = item.question || "";

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

          article.append(meta, question, note);
          list.appendChild(article);
        });
      });
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

      if (!matching && !field.dataset.savedValue) {
        field.dataset.savedValue = field.value || "";
      }
    });

    renderSummary(url);
  };

  const loadNotes = async (url) => {
    if (!url) return [];
    if (notesCache.has(url)) return notesCache.get(url);
    if (pendingLoads.has(url)) return pendingLoads.get(url);

    const promise = fetch(url, {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
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
      .finally(() => {
        pendingLoads.delete(url);
      });

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

    if (!updateUrl || !notesUrl || !source || !question) return;
    if ((field.dataset.savedValue || "") === note) return;

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
    } catch (error) {
      setStatus(field, "error");
    }
  };

  const queueSave = (field, delay = 700) => {
    const existingTimer = saveTimers.get(field);
    if (existingTimer) window.clearTimeout(existingTimer);

    const timer = window.setTimeout(() => {
      saveTimers.delete(field);
      saveField(field);
    }, delay);

    saveTimers.set(field, timer);
  };

  const initialise = (root = document) => {
    const urls = new Set();

    root.querySelectorAll?.("[data-interview-question-note]").forEach((field) => {
      if (!field.dataset.savedValue) field.dataset.savedValue = field.value || "";
      if (field.dataset.notesUrl) urls.add(field.dataset.notesUrl);
    });

    root
      .querySelectorAll?.("[data-interview-question-notes-summary]")
      .forEach((summary) => {
        if (summary.dataset.notesUrl) urls.add(summary.dataset.notesUrl);
      });

    urls.forEach((url) => {
      if (notesCache.has(url)) applyNotes(url, notesCache.get(url));
      else loadNotes(url);
    });
  };

  document.addEventListener("input", (event) => {
    const field = event.target.closest?.("[data-interview-question-note]");
    if (!field) return;
    setStatus(field, "");
    queueSave(field);
  });

  document.addEventListener(
    "blur",
    (event) => {
      const field = event.target.closest?.("[data-interview-question-note]");
      if (!field) return;
      queueSave(field, 0);
    },
    true,
  );

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
