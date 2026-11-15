(function () {
  "use strict";

  function initProcessSettings() {
    const root = document.querySelector(".process-settings-page");

    if (!root || root.dataset.processSettingsInitialised === "true") {
      return;
    }

    root.dataset.processSettingsInitialised = "true";

    const templateLocked =
      root.dataset.templateLocked === "true";

    // Settings copy follows the project's candidate language, not the
    // logged-in user's UI language. Update instantly when it is changed.
    const candidateLanguageRadios = root.querySelectorAll(
      'input[name="candidate_language"]'
    );
    const projectLanguageCopies = root.querySelectorAll(
      "[data-project-language]"
    );

    function syncProjectLanguageCopy() {
      const selected = root.querySelector(
        'input[name="candidate_language"]:checked'
      );
      const language = selected && selected.value === "en" ? "en" : "sv";

      projectLanguageCopies.forEach((element) => {
        element.hidden = element.dataset.projectLanguage !== language;
      });
    }

    candidateLanguageRadios.forEach((radio) => {
      radio.addEventListener("change", syncProjectLanguageCopy);
    });
    syncProjectLanguageCopy();

    const purposeRadios = root.querySelectorAll(
      ".js-purpose-radio"
    );

    const testCheckboxes = root.querySelectorAll(
      ".js-test-checkbox"
    );

    purposeRadios.forEach((radio) => {
      radio.addEventListener("change", () => {
        if (!radio.checked || templateLocked) {
          return;
        }

        const recommended = (
          radio.dataset.recommendedTests || ""
        )
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean);

        if (!recommended.length) {
          return;
        }

        testCheckboxes.forEach((checkbox) => {
          checkbox.checked = recommended.includes(
            checkbox.value
          );
        });

        if (window.feather) {
          window.feather.replace();
        }
      });
    });

    if (window.feather) {
      window.feather.replace();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      initProcessSettings
    );
  } else {
    initProcessSettings();
  }
})();
