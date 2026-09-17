(() => {
  "use strict";

  const isSwedish = () =>
    (document.documentElement.lang || "")
      .toLowerCase()
      .startsWith("sv");

  const copy = () => {
    if (isSwedish()) {
      return {
        generate: "Generera beslutsstöd efter intervju",
        refresh: "Generera uppdaterat beslutsstöd efter intervju",
        ready: (
          "Intervjuunderlag har sparats. Generera en syntes för att jämföra " +
          "det med testresultaten och identifiera kvarstående osäkerheter."
        ),
        generating: "Genererar…",
        error: "Beslutsstödet efter intervjun kunde inte genereras.",
      };
    }

    return {
      generate: "Generate post-interview decision support",
      refresh: "Generate updated post-interview decision support",
      ready: (
        "Interview evidence has been saved. Generate a synthesis to compare " +
        "it with the assessment indications and identify remaining uncertainties."
      ),
      generating: "Generating…",
      error: "The post-interview decision support could not be generated.",
    };
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

  const finalRootsWithin = (root = document) => {
    const roots = [];

    if (
      root instanceof Element &&
      root.matches("[data-final-output-root]")
    ) {
      roots.push(root);
    }

    if (root?.querySelectorAll) {
      roots.push(
        ...root.querySelectorAll(
          "[data-final-output-root]"
        ),
      );
    }

    return roots;
  };

  const questionNotesUrlForRoot = (root) => {
    const rawUrl =
      root.dataset.refreshUrl ||
      root.dataset.postInterviewStreamUrl ||
      "";

    if (!rawUrl) return "";

    let parsed;

    try {
      parsed = new URL(rawUrl, window.location.origin);
    } catch (_error) {
      return "";
    }

    const match = parsed.pathname.match(
      /^(.*\/)(\d+)\/candidates?\/(\d+)\//,
    );

    if (!match) return "";

    const [, prefix, processId, candidateId] = match;

    return (
      `${parsed.origin}${prefix}${processId}/candidates/${candidateId}/` +
      "interview-question-notes/"
    );
  };

  const hasSavedGeneralNotes = (root) => {
    if (!("savedGeneralInterviewEvidence" in root.dataset)) {
      const input = root.querySelector(
        "[data-interview-notes-input]",
      );

      root.dataset.savedGeneralInterviewEvidence =
        String(Boolean((input?.value || "").trim()));
    }

    return (
      root.dataset.savedGeneralInterviewEvidence ===
      "true"
    );
  };

  const createGenerateButton = (root) => {
    const section = root.querySelector(
      "[data-post-interview-section]",
    );

    if (!section) return null;

    const existing = section.querySelector(
      "[data-post-interview-generate]",
    );

    if (existing) return existing;

    const strings = copy();
    const hasResult =
      root.dataset.hasPostInterviewResult ===
      "true";

    const button = document.createElement("button");
    button.type = "button";
    button.dataset.postInterviewGenerate = "";
    button.dataset.regenerate = hasResult ? "true" : "false";
    button.dataset.questionEvidenceInjected = "true";
    button.disabled = true;
    button.classList.add("d-none");

    if (hasResult) {
      button.className = "btn btn-icon btn-light d-none";
      button.title = strings.refresh;
      button.setAttribute("aria-label", strings.refresh);
      button.innerHTML = '<i data-feather="refresh-cw"></i>';

      const statusBadge = section.querySelector(
        "[data-post-interview-status-badge]",
      );

      const actions = statusBadge?.parentElement;
      actions?.appendChild(button);
    } else {
      button.className = "btn btn-primary d-none";
      button.textContent = strings.generate;

      const emptyState = section.querySelector(
        "[data-post-interview-empty]",
      );

      if (!emptyState) return null;

      const actions = document.createElement("div");
      actions.className = "d-flex justify-content-center mt-4";
      actions.dataset.questionEvidenceGenerateActions = "";
      actions.appendChild(button);
      emptyState.appendChild(actions);
    }

    if (window.feather) {
      window.feather.replace();
    }

    return button;
  };

  const updateEmptyStateCopy = (
    root,
    hasEvidence,
  ) => {
    if (
      root.dataset.hasPostInterviewResult ===
      "true"
    ) {
      return;
    }

    const emptyState = root.querySelector(
      "[data-post-interview-empty]",
    );

    const paragraph = emptyState?.querySelector("p");

    if (!paragraph) return;

    if (!("originalEvidenceCopy" in paragraph.dataset)) {
      paragraph.dataset.originalEvidenceCopy =
        paragraph.textContent.trim();
    }

    paragraph.textContent = hasEvidence
      ? copy().ready
      : paragraph.dataset.originalEvidenceCopy;
  };

  const updateAvailability = (
    root,
    questionNotes,
  ) => {
    const hasQuestionNotes = Array.isArray(questionNotes)
      ? questionNotes.some(
          (item) => Boolean(
            String(item?.note || "").trim(),
          ),
        )
      : root.dataset.hasQuestionInterviewEvidence ===
        "true";

    const hasGeneralNotes =
      hasSavedGeneralNotes(root);

    const hasEvidence = Boolean(
      hasGeneralNotes || hasQuestionNotes,
    );

    root.dataset.hasInterviewEvidence =
      String(hasEvidence);
    root.dataset.hasQuestionInterviewEvidence =
      String(hasQuestionNotes);

    const button = createGenerateButton(root);

    if (
      button &&
      button.dataset.questionEvidenceInjected ===
        "true"
    ) {
      button.disabled = !hasEvidence;
      button.classList.toggle(
        "d-none",
        !hasEvidence,
      );
    }

    updateEmptyStateCopy(
      root,
      hasEvidence,
    );

    if (window.feather) {
      window.feather.replace();
    }
  };

  const loadQuestionEvidence = async (root) => {
    const notesUrl =
      questionNotesUrlForRoot(root);

    if (!notesUrl) {
      updateAvailability(root, []);
      return;
    }

    root.dataset.questionEvidenceNotesUrl =
      notesUrl;

    try {
      const response = await fetch(
        notesUrl,
        {
          method: "GET",
          headers: {
            "X-Requested-With":
              "XMLHttpRequest",
          },
          credentials: "same-origin",
        },
      );

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.error ||
          "Could not load interview question notes.",
        );
      }

      updateAvailability(
        root,
        payload.notes || [],
      );
    } catch (_error) {
      // Keep the server-rendered general-notes behaviour when the
      // question-note lookup is temporarily unavailable.
      updateAvailability(root, []);
    }
  };

  const refreshFinalOutput = async (root) => {
    const refreshUrl = root.dataset.refreshUrl || "";

    if (!refreshUrl) {
      window.location.reload();
      return;
    }

    const workspace = root.closest(
      "[data-candidate-insights-workspace]",
    );

    const activeInsightsTab =
      workspace
        ?.querySelector("[data-insights-tab].is-active")
        ?.dataset
        ?.insightsTab || "after-interview";

    // Prefer the existing Talena refresh helper when it is available so all
    // normal candidate-insights initialisers keep running as before.
    if (typeof window.refreshCandidateFinalOutput === "function") {
      await window.refreshCandidateFinalOutput(document);
    } else {
      const response = await fetch(
        refreshUrl,
        {
          headers: {
            "X-Requested-With": "XMLHttpRequest",
          },
          credentials: "same-origin",
        },
      );

      if (!response.ok) {
        throw new Error(copy().error);
      }

      const html = await response.text();
      const template = document.createElement("template");
      template.innerHTML = html.trim();
      const replacement = template.content.firstElementChild;

      if (!replacement) {
        throw new Error(copy().error);
      }

      root.replaceWith(replacement);
    }

    const currentWorkspace =
      workspace ||
      document.querySelector("[data-candidate-insights-workspace]");

    const targetTab = currentWorkspace?.querySelector(
      `[data-insights-tab="${activeInsightsTab}"]`,
    );

    targetTab?.click();

    if (window.feather) {
      window.feather.replace();
    }
  };

  const drainPostInterviewStream = async (url) => {
    const response = await fetch(
      url,
      {
        method: "GET",
        headers: {
          "Accept": "application/x-ndjson",
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      },
    );

    if (!response.ok) {
      let message = copy().error;

      try {
        const payload = await response.json();
        if (payload.error) message = payload.error;
      } catch (_error) {
        // Keep fallback message.
      }

      throw new Error(message);
    }

    if (!response.body) {
      throw new Error(copy().error);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    const handleLine = (rawLine) => {
      const line = rawLine.trim();
      if (!line) return;

      const event = JSON.parse(line);

      if (event.type === "prompt_debug") {
        console.info(
          "[Talena] After interview prompt diagnostics:",
          event.data,
        );
        return;
      }

      if (event.type === "result_debug") {
        console.info(
          "[Talena] After interview generated-content diagnostics:",
          event.data,
        );
        return;
      }

      if (event.type === "error") {
        throw new Error(event.message || copy().error);
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
  };

  const generateFromInjectedButton = async (button) => {
    if (
      button.disabled ||
      button.dataset.questionEvidenceBusy === "true"
    ) {
      return;
    }

    const root = button.closest("[data-final-output-root]");
    if (!root) return;

    const streamUrl = root.dataset.postInterviewStreamUrl || "";
    const regenerateUrl = root.dataset.postInterviewRegenerateUrl || "";
    const shouldRegenerate = button.dataset.regenerate === "true";
    const errorBox = root.querySelector("[data-post-interview-error]");
    const thinking = root.querySelector("[data-post-interview-thinking]");
    const emptyState = root.querySelector("[data-post-interview-empty]");
    const originalHtml = button.innerHTML;

    button.dataset.questionEvidenceBusy = "true";
    button.disabled = true;
    button.innerHTML = `
      <span
        class="spinner-border spinner-border-sm"
        role="status"
        aria-hidden="true"
      ></span>
      ${copy().generating}
    `;

    errorBox?.classList.add("d-none");
    thinking?.classList.remove("d-none");
    emptyState?.classList.add("d-none");

    try {
      if (
        typeof window.saveCandidateInterviewNotes ===
        "function"
      ) {
        await window.saveCandidateInterviewNotes(root);
      }

      let targetStreamUrl = streamUrl;

      if (shouldRegenerate) {
        const response = await fetch(
          regenerateUrl,
          {
            method: "POST",
            headers: {
              "X-CSRFToken": getCookie("csrftoken"),
              "X-Requested-With": "XMLHttpRequest",
              "Content-Type": "application/json",
            },
            credentials: "same-origin",
            body: JSON.stringify({}),
          },
        );

        let payload = {};
        try {
          payload = await response.json();
        } catch (_error) {
          // Keep empty payload.
        }

        if (!response.ok) {
          throw new Error(payload.error || copy().error);
        }

        targetStreamUrl = payload.stream_url || streamUrl;
      }

      if (!targetStreamUrl) {
        throw new Error(copy().error);
      }

      await drainPostInterviewStream(targetStreamUrl);
      await refreshFinalOutput(root);
    } catch (error) {
      console.error(
        "Post-interview question-evidence generation error:",
        error,
      );

      thinking?.classList.add("d-none");
      errorBox?.classList.remove("d-none");
      if (errorBox) {
        errorBox.textContent = error.message || copy().error;
      }

      button.disabled = false;
      button.innerHTML = originalHtml;
      button.dataset.questionEvidenceBusy = "false";

      if (window.feather) {
        window.feather.replace();
      }
    }
  };

  const initialiseRoot = (root) => {
    if (!root) return;

    const input = root.querySelector(
      "[data-interview-notes-input]",
    );

    if (
      input &&
      input.dataset.interviewEvidenceAvailabilityBound !==
        "true"
    ) {
      input.dataset.interviewEvidenceAvailabilityBound =
        "true";

      input.addEventListener("input", () => {
        // Treat the current textarea value as available evidence. The
        // generation handler persists it before opening the AI stream.
        root.dataset.savedGeneralInterviewEvidence =
          String(Boolean(input.value.trim()));

        updateAvailability(root);
      });
    }

    // The process page's large inline Decision Support script executes before
    // this shared customer-base module. Therefore a button created here cannot
    // rely on that script having attached a direct click handler. Injected
    // buttons are handled by the delegated listener below instead.
    createGenerateButton(root);
    loadQuestionEvidence(root);
  };

  const initialise = (root = document) => {
    finalRootsWithin(root).forEach(
      initialiseRoot,
    );
  };

  initialise(document);

  document.addEventListener(
    "DOMContentLoaded",
    () => initialise(document),
  );

  // Capture injected buttons before any older direct handler can run. This is
  // intentionally limited to buttons created by this module, so normal
  // server-rendered post-interview buttons keep their existing Talena logic.
  document.addEventListener(
    "click",
    (event) => {
      const button = event.target.closest?.(
        "[data-post-interview-generate][data-question-evidence-injected='true']",
      );

      if (!button) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      generateFromInjectedButton(button);
    },
    true,
  );

  document.addEventListener(
    "candidate-interview-question-note-updated",
    (event) => {
      const notesUrl =
        event.detail?.notesUrl || "";

      finalRootsWithin(document).forEach(
        (root) => {
          if (
            notesUrl &&
            root.dataset.questionEvidenceNotesUrl &&
            root.dataset.questionEvidenceNotesUrl !== notesUrl
          ) {
            return;
          }

          loadQuestionEvidence(root);
        },
      );
    },
  );

  const observer = new MutationObserver(
    (mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (!(node instanceof Element)) continue;
          initialise(node);
        }
      }
    },
  );

  observer.observe(
    document.documentElement,
    {
      childList: true,
      subtree: true,
    },
  );
})();
