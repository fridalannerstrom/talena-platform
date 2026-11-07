/* Talena account invitations: keep editable subject and message in sync with
 * the chosen email language. Defaults come from the Django form fields, not
 * duplicated JS copy, so the preview and sent mail use identical text.
 */
(() => {
  "use strict";

  const LANGUAGE_SELECTOR = 'select[name="invite_language"]';
  const FIELDS = ['invite_subject', 'invite_message'];

  function syncInvitationDefaults(languageSelect) {
    const form = languageSelect.closest("form");
    if (!form) return;

    const language = languageSelect.value === "sv" ? "sv" : "en";
    FIELDS.forEach((fieldName) => {
      const field = form.querySelector('[name="' + fieldName + '"]');
      if (!field) return;

      const english = field.dataset.inviteDefaultEn;
      const swedish = field.dataset.inviteDefaultSv;
      if (typeof english !== "string" || typeof swedish !== "string") return;

      // Only translate standard copy. Preserve personal edits in either
      // language, including for the preview and the eventual email.
      if (!field.value || field.value === english || field.value === swedish) {
        const next = language === "sv" ? swedish : english;
        if (field.value !== next) {
          field.value = next;
          field.dispatchEvent(new Event("input", { bubbles: true }));
        }
      }
    });
  }

  // Delegated handler also works when an invitation modal is inserted later.
  document.addEventListener("change", (event) => {
    if (event.target?.matches?.(LANGUAGE_SELECTOR)) {
      syncInvitationDefaults(event.target);
    }
  });

  function initialize() {
    document.querySelectorAll(LANGUAGE_SELECTOR).forEach(syncInvitationDefaults);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize, { once: true });
  } else {
    initialize();
  }
})();
