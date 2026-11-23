/* Make the synchronous role-context save feel responsive while OpenAI chooses
 * eight shared project traits. The server remains authoritative for success,
 * errors, permissions and saving. Do not intercept or replace its POST.
 */
(() => {
  "use strict";

  function init() {
    const form = document.querySelector("[data-role-context-form]");
    const overlay = document.querySelector("[data-role-context-saving-overlay]");
    if (!form || !overlay || form.dataset.roleContextProgressBound === "true") return;
    const field = form.querySelector('textarea[name="context_text"]');
    const card = overlay.querySelector("[data-role-context-saving-card]");
    const hint = overlay.querySelector("[data-role-context-saving-hint]");
    const longHint = overlay.querySelector("[data-role-context-saving-long-hint]");
    if (!field || !card) return;

    form.dataset.roleContextProgressBound = "true";
    // DOM defaultValue is the text originally rendered by Django. Compare
    // trimmed values, just as ProcessRoleContextForm.clean_context_text does.
    const savedText = field.defaultValue.trim();
    let submitting = false;
    let longerMessageTimer = null;

    function reset() {
      submitting = false;
      delete form.dataset.roleContextSubmitting;
      form.removeAttribute("aria-busy");
      overlay.hidden = true;
      if (hint) hint.hidden = false;
      if (longHint) longHint.hidden = true;
      if (longerMessageTimer != null) {
        clearTimeout(longerMessageTimer);
        longerMessageTimer = null;
      }
    }

    form.addEventListener("submit", (event) => {
      if (submitting) {
        event.preventDefault(); // Protect against repeated AI calls.
        return;
      }
      const currentText = field.value.trim();
      const contextChanged = currentText !== savedText;
      const manualSelection = event.submitter?.name === "save_personality_traits";
      const selectedTraits = form.querySelectorAll(
        'input[name="personality_question_traits"]:checked'
      ).length;

      // The backend selects new traits when context changes via the normal
      // Save button, or when the selection modal switches to Talena's mode.
      // Neither an unchanged text save nor an explicit eight-trait manual
      // selection needs the AI progress overlay.
      const awaitingTalena = Boolean(currentText) && (
        (!manualSelection && contextChanged) ||
        (manualSelection && selectedTraits === 0)
      );
      submitting = true;
      form.dataset.roleContextSubmitting = "true";
      if (!awaitingTalena) return;

      overlay.hidden = false;
      form.setAttribute("aria-busy", "true");
      card.focus({ preventScroll: true });
      longerMessageTimer = window.setTimeout(() => {
        if (hint) hint.hidden = true;
        if (longHint) longHint.hidden = false;
      }, 18000);

      // Do not call preventDefault, disable form controls or remove the
      // submitter: all original CSRF and save_personality_traits POST fields
      // must reach the existing Django view unchanged.
    });

    // If the page is restored from the back-forward cache after a POST,
    // never leave a stale loading overlay on top of an editable form.
    window.addEventListener("pageshow", reset);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
