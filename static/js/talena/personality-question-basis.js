(function () {
  "use strict";

  const ROOT_SELECTOR = "[data-personality-questions-root]";
  const COMPETENCY_PREFIX = "competency::";
  const MAX_SELECTION = 6;

  function roots(container) {
    const result = [];
    if (container && container.matches && container.matches(ROOT_SELECTOR)) {
      result.push(container);
    }
    if (container && container.querySelectorAll) {
      container.querySelectorAll(ROOT_SELECTOR).forEach((root) => result.push(root));
    }
    return result;
  }

  function optionBasis(checkbox) {
    return checkbox.dataset.questionBasisOption ||
      (String(checkbox.value || "").startsWith(COMPETENCY_PREFIX)
        ? "competencies"
        : "traits");
  }

  function optionCheckboxes(root) {
    return Array.from(
      root.querySelectorAll("[data-personality-trait-checkbox]")
    );
  }

  function checkedOptions(root, mode) {
    return optionCheckboxes(root).filter((checkbox) => {
      return checkbox.checked && (!mode || optionBasis(checkbox) === mode);
    });
  }

  function unlockOptionInputs(root) {
    optionCheckboxes(root).forEach((checkbox) => {
      checkbox.disabled = false;
    });
  }

  function isSwedish() {
    return String(document.documentElement.lang || "sv")
      .toLowerCase()
      .startsWith("sv");
  }

  function updateQuestionsIntro(root) {
    const intro = root.querySelector(
      ".personality-questions-header p.text-muted.small"
    );

    if (!intro) {
      return;
    }

    intro.textContent = isSwedish()
      ? "Utforska relevanta beteenden genom praktiska, syftesanpassade intervjufrågor."
      : "Explore relevant behaviours through practical, purpose-aware interview questions.";
  }

  function focusLabelMap(root) {
    const labelMap = new Map();

    root.querySelectorAll("[data-personality-trait-checkbox]").forEach((checkbox) => {
      const explicitLabel = checkbox.dataset.questionFocusLabel;
      if (explicitLabel) {
        labelMap.set(String(checkbox.value || "").trim(), explicitLabel);
      }
    });

    return labelMap;
  }

  function localiseRenderedFocusLabels(root) {
    const labelMap = focusLabelMap(root);

    root.querySelectorAll(
      "[data-personality-selected-traits] .personality-trait-pill, " +
      ".personality-question-card__traits span"
    ).forEach((element) => {
      const rawValue = String(element.textContent || "").trim();
      const label = labelMap.get(rawValue);
      if (label && element.textContent !== label) {
        element.textContent = label;
      }
    });
  }

  function activeMode(root) {
    return root.dataset.questionBasis === "competencies"
      ? "competencies"
      : "traits";
  }

  function selectedMode(root) {
    const checked = Array.from(
      root.querySelectorAll("[data-personality-trait-checkbox]:checked")
    );

    return checked.some((checkbox) => optionBasis(checkbox) === "competencies")
      ? "competencies"
      : "traits";
  }

  function modeButton(root, mode) {
    return root.querySelector(
      `[data-question-basis-tab="${mode}"]`
    );
  }

  function updateSelectionLimitState(root) {
    if (!root) {
      return;
    }

    // The legacy personality-question JS disables every remaining option as
    // soon as six are selected. Native disabled controls can disturb the
    // dialog's scroll/focus behaviour, so keep all options interactive and
    // enforce the limit before a seventh option can be checked instead.
    unlockOptionInputs(root);

    const mode = activeMode(root);
    const count = checkedOptions(root, mode).length;
    const countElement = root.querySelector("[data-personality-traits-count]");

    if (countElement && mode === "competencies" && count === 0) {
      countElement.textContent = isSwedish() ? "0 valda" : "0 selected";
    }

    root.classList.toggle(
      "personality-question-basis-at-limit",
      count >= MAX_SELECTION
    );
  }

  function updateModeCopy(root, mode) {
    const button = modeButton(root, mode);
    if (!button) {
      return;
    }

    const summaryTitle = root.querySelector("[data-question-basis-summary-title]");
    const summaryDescription = root.querySelector("[data-question-basis-summary-description]");
    const editLabel = root.querySelector("[data-question-basis-edit-label]");
    const dialogTitle = root.querySelector("[data-question-basis-dialog-title]");
    const dialogDescription = root.querySelector("[data-question-basis-dialog-description]");
    const statusLabel = root.querySelector("[data-question-basis-status-label]");
    const emptyError = root.querySelector("[data-question-basis-empty-error]");

    if (summaryTitle && button.dataset.summaryTitle) {
      summaryTitle.textContent = button.dataset.summaryTitle;
    }
    if (summaryDescription && button.dataset.summaryDescription) {
      summaryDescription.textContent = button.dataset.summaryDescription;
    }
    if (editLabel && button.dataset.editLabel) {
      editLabel.textContent = button.dataset.editLabel;
    }
    if (dialogTitle && button.dataset.dialogTitle) {
      dialogTitle.textContent = button.dataset.dialogTitle;
    }
    if (dialogDescription && button.dataset.dialogDescription) {
      dialogDescription.textContent = button.dataset.dialogDescription;
    }
    if (statusLabel && button.dataset.statusLabel) {
      statusLabel.textContent = button.dataset.statusLabel;
    }
    if (emptyError) {
      emptyError.hidden = true;
    }
  }

  function setMode(root, mode, clearOtherMode) {
    if (!root || !["traits", "competencies"].includes(mode)) {
      return;
    }

    root.dataset.questionBasis = mode;

    root.querySelectorAll("[data-question-basis-tab]").forEach((button) => {
      const isActive = button.dataset.questionBasisTab === mode;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
    });

    root.querySelectorAll("[data-question-basis-panel]").forEach((panel) => {
      panel.hidden = panel.dataset.questionBasisPanel !== mode;
    });

    if (clearOtherMode) {
      root.querySelectorAll("[data-personality-trait-checkbox]").forEach((checkbox) => {
        if (optionBasis(checkbox) === mode || !checkbox.checked) {
          return;
        }

        checkbox.checked = false;
        checkbox.dispatchEvent(new Event("change", { bubbles: true }));
      });
    }

    updateModeCopy(root, mode);
    updateSelectionLimitState(root);
    localiseRenderedFocusLabels(root);
  }

  function syncModeToSavedSelection(root) {
    if (!root) {
      return;
    }

    setMode(root, selectedMode(root), false);
    updateSelectionLimitState(root);
  }

  function initialiseRoot(root) {
    if (!root || root.dataset.questionBasisUiInitialised === "true") {
      return;
    }

    root.dataset.questionBasisUiInitialised = "true";
    setMode(root, activeMode(root), false);
    updateQuestionsIntro(root);
    updateSelectionLimitState(root);

    const observer = new MutationObserver(() => {
      localiseRenderedFocusLabels(root);
    });

    observer.observe(root, {
      childList: true,
      subtree: true,
    });

    localiseRenderedFocusLabels(root);
  }

  function initialiseWithin(container) {
    roots(container).forEach(initialiseRoot);
  }

  // Enforce the six-item product limit without disabling/hiding all remaining
  // choices. A seventh click is simply ignored, while the existing six stay
  // editable and the scrollable dialog keeps its geometry.
  document.addEventListener("click", function (event) {
    const option = event.target.closest(".personality-trait-option");
    const checkbox = option
      ? option.querySelector("[data-personality-trait-checkbox]")
      : event.target.closest("[data-personality-trait-checkbox]");

    if (!checkbox || checkbox.checked) {
      return;
    }

    const root = checkbox.closest(ROOT_SELECTOR);
    if (!root) {
      return;
    }

    const mode = optionBasis(checkbox);
    if (mode !== activeMode(root)) {
      return;
    }

    if (checkedOptions(root, mode).length < MAX_SELECTION) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();
    unlockOptionInputs(root);
  }, true);

  document.addEventListener("click", function (event) {
    const tab = event.target.closest("[data-question-basis-tab]");
    if (tab) {
      const root = tab.closest(ROOT_SELECTOR);
      const mode = tab.dataset.questionBasisTab;
      setMode(root, mode, true);
      return;
    }

    const editorAction = event.target.closest(
      "[data-personality-traits-edit], [data-personality-traits-cancel]"
    );

    if (editorAction) {
      const root = editorAction.closest(ROOT_SELECTOR);
      // Existing Talena JS restores the saved checkbox selection in the
      // target click handler. Run after that handler so the visible mode,
      // option availability and copy follow the saved selection as well.
      window.setTimeout(() => {
        syncModeToSavedSelection(root);
        updateSelectionLimitState(root);
      }, 0);
    }
  });

  // Capture the click before the existing personality-question save handler.
  // Competency mode requires an explicit competency selection, while trait mode
  // keeps the existing "Talena may choose" behaviour when nothing is checked.
  document.addEventListener("click", function (event) {
    const saveButton = event.target.closest("[data-personality-traits-save]");
    if (!saveButton) {
      return;
    }

    const root = saveButton.closest(ROOT_SELECTOR);
    if (!root || activeMode(root) !== "competencies") {
      return;
    }

    const selectedCompetencies = Array.from(
      root.querySelectorAll("[data-personality-trait-checkbox]:checked")
    ).filter((checkbox) => optionBasis(checkbox) === "competencies");

    if (selectedCompetencies.length) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    const emptyError = root.querySelector("[data-question-basis-empty-error]");
    if (emptyError) {
      emptyError.hidden = false;
      emptyError.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, true);

  document.addEventListener("change", function (event) {
    const checkbox = event.target.closest("[data-personality-trait-checkbox]");
    if (!checkbox) {
      return;
    }

    const root = checkbox.closest(ROOT_SELECTOR);
    if (!root) {
      return;
    }

    const mode = optionBasis(checkbox);
    if (checkbox.checked && activeMode(root) !== mode) {
      setMode(root, mode, true);
    }

    const emptyError = root.querySelector("[data-question-basis-empty-error]");
    if (emptyError && checkbox.checked) {
      emptyError.hidden = true;
    }

    // Runs after the existing checkbox change listener, undoing its blanket
    // disabled state while keeping its selected-count copy intact.
    updateSelectionLimitState(root);
  });

  document.addEventListener("DOMContentLoaded", function () {
    initialiseWithin(document);
  });

  const documentObserver = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === Node.ELEMENT_NODE) {
          initialiseWithin(node);
        }
      });
    });
  });

  documentObserver.observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
