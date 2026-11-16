/* Ticket #353: passive, read-only Talena admin mirror of the customer sheet.
 *
 * The customer presentation is rendered by the same Django partial. In admin
 * we only initialise navigation and passive UI, never AI generation routines.
 */
(function () {
  "use strict";

  const navigationSelectors = [
    ".candidate-tab[data-tab-target]",
    "[data-insights-tab]",
    "[data-insights-subtab]",
    "[data-decision-tab]",
    "[data-after-interview-tab]",
    "[data-after-interview-primary-tab]",
    "[data-bs-toggle='collapse']",
    "[data-bs-toggle='tab']",
    "[data-bs-toggle='modal']",
    "[data-bs-toggle='dropdown']",
    "button[aria-expanded][aria-controls]",
    ".js-open-email-modal",
    "[data-copy-candidate-url]"
  ].join(", ");

  function activateItems(root, button, tabKey, panelKey) {
    const target = button.dataset[tabKey];
    if (!target) return;
    const tabs = Array.from(root.querySelectorAll("[data-" + tabKey.replace(/[A-Z]/g, c => "-" + c.toLowerCase()) + "]"));
    const panels = Array.from(root.querySelectorAll("[data-" + panelKey.replace(/[A-Z]/g, c => "-" + c.toLowerCase()) + "]"));
    tabs.forEach(tab => {
      const active = tab.dataset[tabKey] === target;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
    });
    panels.forEach(panel => {
      const active = panel.dataset[panelKey] === target;
      panel.classList.toggle("is-active", active);
      panel.hidden = !active;
    });
    if (panelKey === "insightsSubpanel") {
      root.querySelectorAll("[data-insights-panel-shell]").forEach(shell => {
        shell.hidden = !Boolean(shell.querySelector("[data-insights-subpanel='" + CSS.escape(target) + "']"));
      });
    }
  }

  function passiveTabClick(control, mirror) {
    if (control.matches(".candidate-tab[data-tab-target]")) {
      const group = control.dataset.tabGroup;
      const target = control.dataset.tabTarget;
      const scope = control.closest(".candidate-profile-shell") || mirror;
      const tabs = scope.querySelectorAll("[data-tab-group='" + group + "'][data-tab-target]");
      const panels = scope.querySelectorAll("[data-tab-group='" + group + "'][data-tab-panel]");
      tabs.forEach(tab => {
        const active = tab === control;
        tab.classList.toggle("is-active", active);
        tab.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach(panel => {
        const active = panel.dataset.tabPanel === target;
        panel.classList.toggle("is-active", active);
        panel.hidden = !active;
      });
    } else if (control.matches("[data-insights-subtab]")) {
      activateItems(control.closest("[data-candidate-insights-subtabs]") || mirror,
        control, "insightsSubtab", "insightsSubpanel");
    } else if (control.matches("[data-insights-tab]")) {
      activateItems(control.closest("[data-candidate-insights-workspace]") || mirror,
        control, "insightsTab", "insightsPanel");
    } else if (control.matches("[data-decision-tab]")) {
      activateItems(control.closest("[data-decision-support-root]") || mirror,
        control, "decisionTab", "decisionPanel");
    }
  }

  function prepareMirrors(scope) {
    const mirrors = [
      ...(scope.matches?.("[data-admin-candidate-mirror]") ? [scope] : []),
      ...scope.querySelectorAll("[data-admin-candidate-mirror]")
    ];
    mirrors.forEach(mirror => {
      if (mirror.dataset.readOnlyPrepared === "true") return;
      mirror.dataset.readOnlyPrepared = "true";
      mirror.querySelectorAll("button").forEach(button => {
        if (!button.matches(navigationSelectors)) {
          // Keep the customer's current text/empty state, but stop mutations.
          button.disabled = true;
          button.setAttribute("aria-disabled", "true");
          button.title = button.title || "Read-only customer view";
        }
      });
    });
  }

  // The old admin route has no customer page script defining switchTabs.
  // Keep the standard customer inline tab handler working there as well.
  if (typeof window.switchTabs !== "function") {
    window.switchTabs = function (button) {
      const mirror = button.closest("[data-admin-candidate-mirror]");
      if (mirror) passiveTabClick(button, mirror);
    };
  }

  document.addEventListener("click", function (event) {
    const mirror = event.target.closest?.("[data-admin-candidate-mirror]");
    if (!mirror) return;
    const control = event.target.closest("button, a, [role='button'], input[type='submit']");
    if (!control) return;
    if (control.matches(navigationSelectors)) {
      passiveTabClick(control, mirror);
      return;
    }
    // Links that navigate to a separate view are allowed. Actions that mutate
    // or call AI on the customer sheet are not.
    if (control.tagName === "A" && !control.hasAttribute("data-action")) {
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
  }, true);

  document.addEventListener("submit", function (event) {
    if (event.target.closest("[data-admin-candidate-mirror]")) {
      event.preventDefault();
      event.stopImmediatePropagation();
    }
  }, true);

  document.addEventListener("DOMContentLoaded", function () {
    prepareMirrors(document);
    const sheet = document.getElementById("candidateSheetBody");
    if (sheet) {
      const observer = new MutationObserver(() => prepareMirrors(sheet));
      observer.observe(sheet, { childList: true, subtree: false });
    }
  });
})();
