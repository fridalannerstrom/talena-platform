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
      };
    }

    return {
      generate: "Generate post-interview decision support",
      refresh: "Generate updated post-interview decision support",
      ready: (
        "Interview evidence has been saved. Generate a synthesis to compare " +
        "it with the assessment indications and identify remaining uncertainties."
      ),
    };
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
    questionNotes = [],
  ) => {
    const hasQuestionNotes = Array.isArray(questionNotes)
      ? questionNotes.some(
          (item) => Boolean(
            String(item?.note || "").trim(),
          ),
        )
      : false;

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

  const initialiseRoot = (root) => {
    if (!root) return;

    // This runs before the page-specific decision-support script. Creating
    // the button synchronously here means the existing generation handler can
    // attach to it exactly as if Django had rendered it originally.
    createGenerateButton(root);
    loadQuestionEvidence(root);
  };

  const initialise = (root = document) => {
    finalRootsWithin(root).forEach(
      initialiseRoot,
    );
  };

  // The customer-base script is loaded after the page markup but before the
  // process page's inline Decision Support JS, so initialise immediately.
  initialise(document);

  document.addEventListener(
    "DOMContentLoaded",
    () => initialise(document),
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
