/* Regenerate question sets from the only visible home: Prepare for interview.
 * Reuse the three established handlers (and their existing permissions,
 * CSRF tokens and streaming). Do not touch saved interview evidence.
 * The combined root is AJAX-replaced after each successful area refresh.
 */
(function () {
  "use strict";

  if (window.talenaPreInterviewRefreshBound) return;
  window.talenaPreInterviewRefreshBound = true;

  const definitions = [
    {
      root: "[data-personality-questions-root]",
      action: "[data-personality-questions-regenerate]",
      initialized: "personalityQuestionsInitialised",
      sv: "Personlighet",
      en: "Personality",
    },
    {
      root: "[data-motivation-questions-root]",
      action: "[data-motivation-questions-regenerate]",
      initialized: "motivationQuestionsInitialised",
      sv: "Motivation",
      en: "Motivation",
    },
    {
      root: "[data-cognitive-questions-root]",
      action: "[data-cognitive-questions-regenerate]",
      initialized: "cognitiveQuestionsInitialised",
      sv: "Färdighet",
      en: "Skills",
    },
  ];

  const swedish = () => (
    (document.documentElement.lang || "sv").toLowerCase().startsWith("sv")
  );

  function workspaceFor(button) {
    return button.closest("[data-candidate-insights-workspace]");
  }

  function renderState(workspace, busy, message, error) {
    const root = workspace.querySelector("[data-combined-questions-root]");
    if (!root) return;
    const button = root.querySelector("[data-pre-interview-questions-regenerate]");
    const status = root.querySelector("[data-pre-interview-questions-refresh-status]");
    if (button) {
      button.disabled = busy;
      if (busy) button.setAttribute("aria-busy", "true");
      else button.removeAttribute("aria-busy");
    }
    if (status) {
      if (status.textContent !== message) status.textContent = message;
      status.hidden = !message;
      status.classList.toggle("text-danger", Boolean(error));
      status.classList.toggle("text-muted", !error);
    }
  }

  function eligibleSources(workspace) {
    return definitions.map(definition => {
      const root = workspace.querySelector(definition.root);
      const button = root?.querySelector(definition.action);
      return { ...definition, root, button };
    }).filter(item =>
      item.root &&
      item.button &&
      item.root.dataset[item.initialized] === "true" &&
      item.root.dataset.regenerateUrl &&
      !item.button.disabled
    );
  }

  // The existing generator signals success on its source root, and re-enables
  // the source refresh button when the attempt finishes (including on error).
  // This allows the new header action to report genuine per-area outcomes.
  function regenerateOne(item) {
    return new Promise(resolve => {
      const root = item.root;
      const action = item.button;
      let settled = false;
      const observer = new MutationObserver(() => {
        if (!action.disabled) finish(false);
      });
      function finish(success) {
        if (settled) return;
        settled = true;
        observer.disconnect();
        root.removeEventListener("candidate-ai-content-updated", onSuccess);
        resolve(success);
      }
      function onSuccess(event) {
        if (event.target === root) finish(true);
      }
      root.addEventListener("candidate-ai-content-updated", onSuccess);
      observer.observe(action, { attributes: true, attributeFilter: ["disabled"] });
      action.click(); // uses the existing CSRF-protected POST and streaming code
      if (!action.disabled) finish(false);
    });
  }

  // Native <dialog> provides focus management, Escape-to-cancel and an
  // accessible backdrop, without the browser's unstyled confirm alert.
  // The dialog lives inside the candidate sheet so Bootstrap's offcanvas
  // focus trap can still recognize the focused controls.
  function confirmQuestionReplacement(workspace, trigger) {
    const dialog = workspace.querySelector("[data-pre-interview-refresh-dialog]");
    if (!dialog || typeof dialog.showModal !== "function") {
      // Do not regenerate without informed consent if the dialog is absent.
      return Promise.resolve(false);
    }

    const accept = dialog.querySelector("[data-pre-interview-refresh-confirm]");
    const cancel = dialog.querySelector("[data-pre-interview-refresh-cancel]");
    if (!accept || !cancel) return Promise.resolve(false);

    return new Promise(resolve => {
      const onAccept = () => dialog.close("confirm");
      const onCancel = () => dialog.close("cancel");
      const onBackdropClick = event => {
        if (event.target !== dialog) return;
        const bounds = dialog.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom) {
          dialog.close("cancel");
        }
      };
      const onClose = () => {
        accept.removeEventListener("click", onAccept);
        cancel.removeEventListener("click", onCancel);
        dialog.removeEventListener("click", onBackdropClick);
        // The original button still exists until generation begins.
        if (trigger.isConnected) trigger.focus({ preventScroll: true });
        resolve(dialog.returnValue === "confirm");
      };
      dialog.addEventListener("close", onClose, { once: true });
      accept.addEventListener("click", onAccept);
      cancel.addEventListener("click", onCancel);
      dialog.addEventListener("click", onBackdropClick);
      dialog.returnValue = "cancel";
      dialog.showModal();
    });
  }

  document.addEventListener("click", async event => {
    const trigger = event.target.closest?.("[data-pre-interview-questions-regenerate]");
    if (!trigger || trigger.disabled) return;

    const workspace = workspaceFor(trigger);
    if (!workspace || workspace.dataset.preInterviewQuestionsUpdating === "true") return;
    if (workspace.querySelector('[data-is-historical="true"]')) return;

    const sv = swedish();
    const copy = sv ? {
      none: "Inga tillgängliga testfrågor att uppdatera. Kontrollera att testresultat och rollkontext finns.",
      unsaved: "Spara först dina ändringar i intervjuanteckningarna innan du uppdaterar frågorna.",
      progress: "Uppdaterar intervjufrågor…",
      success: "Intervjufrågorna har uppdaterats.",
      partial: "Vissa intervjufrågor kunde inte uppdateras:",
    } : {
      none: "No available assessment questions to regenerate. Check that results and role context are present.",
      unsaved: "Save any unsaved changes to interview notes before regenerating the questions.",
      progress: "Regenerating interview questions…",
      success: "Interview questions have been updated.",
      partial: "Some interview questions could not be updated:",
    };

    const dirtyNotes = Array.from(
      workspace.querySelectorAll("[data-interview-question-note-field] textarea")
    ).some(field => field.value.trim() !== (field.dataset.savedValue || "").trim());
    if (dirtyNotes) {
      renderState(workspace, false, copy.unsaved, true);
      return;
    }

    const items = eligibleSources(workspace);
    if (!items.length) {
      renderState(workspace, false, copy.none, true);
      return;
    }
    if (items.some(item => item.root.dataset.hasResult === "true")) {
      const confirmed = await confirmQuestionReplacement(workspace, trigger);
      if (!confirmed) return;
    }

    workspace.dataset.preInterviewQuestionsUpdating = "true";
    let label = copy.progress;
    let error = false;
    // Re-apply progress state if the combined questions section is replaced
    // while generation is running. Keep the action disabled throughout.
    const observer = new MutationObserver(() => {
      renderState(workspace, true, label, error);
    });
    observer.observe(workspace, { childList: true, subtree: true });
    renderState(workspace, true, label, false);

    const failed = [];
    try {
      for (const item of items) {
        const area = sv ? item.sv : item.en;
        label = copy.progress + " " + area;
        renderState(workspace, true, label, false);
        if (!await regenerateOne(item)) failed.push(area);
      }
      // Show the updated combined list immediately after the last source
      // completes instead of waiting for the regular delayed sync.
      if (typeof window.refreshCandidateCombinedQuestions === "function") {
        await window.refreshCandidateCombinedQuestions(workspace);
      }
      error = failed.length > 0;
      label = failed.length
        ? copy.partial + " " + failed.join(", ")
        : copy.success;
    } catch (cause) {
      console.error("Interview question regeneration failed:", cause);
      error = true;
      label = copy.partial;
    } finally {
      observer.disconnect();
      delete workspace.dataset.preInterviewQuestionsUpdating;
      renderState(workspace, false, label, error);
    }
  });
})();
