(function () {
  "use strict";

  function getI18n() {
    return window.TALENA_PROCESS_I18N || {};
  }

  function setButtonFeedback(buttonEl, text) {
    if (!buttonEl) return;

    const originalText = buttonEl.dataset.originalCopyText || buttonEl.textContent.trim();
    buttonEl.dataset.originalCopyText = originalText;
    buttonEl.textContent = text;

    window.setTimeout(() => {
      if (buttonEl.isConnected) {
        buttonEl.textContent = originalText;
      }
    }, 1400);
  }

  function fallbackCopyText(value) {
    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.top = "0";

    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();

    let copied = false;

    try {
      copied = document.execCommand("copy");
    } catch (error) {
      copied = false;
    }

    textarea.remove();
    return copied;
  }

  async function copyCandidateAssessmentUrl(buttonEl) {
    const panel = buttonEl?.closest(".candidate-link-panel") || document;
    const input = panel.querySelector("#candidateAssessmentUrl") || document.getElementById("candidateAssessmentUrl");

    if (!input || !input.value) return;

    const value = input.value.trim();
    const i18n = getI18n();
    let copied = false;

    if (navigator.clipboard && window.isSecureContext) {
      try {
        await navigator.clipboard.writeText(value);
        copied = true;
      } catch (error) {
        copied = fallbackCopyText(value);
      }
    } else {
      copied = fallbackCopyText(value);
    }

    setButtonFeedback(
      buttonEl,
      copied
        ? (i18n.copied || "Copied!")
        : (i18n.couldNotCopy || "Could not copy.")
    );
  }

  window.copyCandidateAssessmentUrl = copyCandidateAssessmentUrl;

  // Kept for compatibility with the older inline candidate-sheet implementation.
  window.fallbackCopyCandidateUrl = function (input, buttonEl) {
    const i18n = getI18n();
    const copied = Boolean(input?.value) && fallbackCopyText(input.value.trim());

    setButtonFeedback(
      buttonEl,
      copied
        ? (i18n.copied || "Copied!")
        : (i18n.couldNotCopy || "Could not copy.")
    );
  };
})();
