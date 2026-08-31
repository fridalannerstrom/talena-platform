(function () {
  "use strict";

  function restoreWizardValidationStep() {
    const form = document.getElementById("processCreateWizardForm");
    if (!form) {
      return;
    }

    const candidateLanguageErrors = form.querySelector(
      '.candidate-language-section .text-danger'
    );

    if (!candidateLanguageErrors) {
      return;
    }

    const stepThreeButton = document.querySelector(
      '[data-step-target="3"]'
    );

    if (!stepThreeButton) {
      return;
    }

    // The wizard's own DOMContentLoaded handler restores its normal initial
    // step first. Run on the next frame so server-side language validation
    // cannot leave the actual error hidden on step 3.
    window.requestAnimationFrame(function () {
      stepThreeButton.click();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      restoreWizardValidationStep,
      { once: true }
    );
  } else {
    restoreWizardValidationStep();
  }
})();
