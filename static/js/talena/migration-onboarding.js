(function () {
  "use strict";

  function showMigrationOnboarding() {
    const modalElement = document.getElementById(
      "migrationOnboardingModal"
    );

    if (!modalElement || !window.bootstrap) {
      return;
    }

    const modal = bootstrap.Modal.getOrCreateInstance(
      modalElement,
      {
        backdrop: "static",
        keyboard: false,
      }
    );

    modal.show();
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      showMigrationOnboarding
    );
  } else {
    showMigrationOnboarding();
  }
})();
