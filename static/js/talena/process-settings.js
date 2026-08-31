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
