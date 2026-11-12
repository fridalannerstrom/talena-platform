(function () {
  "use strict";

  const modal = document.getElementById("addCandidateModal");
  if (!modal) return;
  const modalDialog = modal.querySelector(".modal-dialog");
  if (modalDialog) modalDialog.classList.add("add-candidate-modal--chooser");

  function refreshIcons() {
    if (window.feather) window.feather.replace();
  }

  function rowsRoot(form, mode) {
    return form.querySelector('[data-candidate-rows="' + mode + '"]');
  }

  function updateRows(form, mode) {
    const root = rowsRoot(form, mode);
    if (!root) return;
    const rows = [...root.querySelectorAll("[data-candidate-row]")];
    rows.forEach((row, index) => {
      const rowTitle = row.dataset.rowLabel.replace("{n}", String(index + 1));
      row.querySelector("[data-row-label]").textContent = rowTitle;
      row.querySelector("legend").textContent = rowTitle;
      const remove = row.querySelector("[data-remove-candidate-row]");
      remove.disabled = rows.length === 1;
      remove.hidden = rows.length === 1;
      row.dataset.rowIndex = String(index + 1);
    });
  }

  function makeRow(form, mode, values = {}, errors = [], sourceRow = null) {
    const root = rowsRoot(form, mode);
    form._candidateRowTemplates = form._candidateRowTemplates || {};
    const fallback = root.querySelector("[data-candidate-row]") ||
      rowsRoot(form, "manual").querySelector("[data-candidate-row]");
    const template = form._candidateRowTemplates[mode] || fallback;
    if (!template) return null;
    form._candidateRowTemplates[mode] = template.cloneNode(true);

    const row = form._candidateRowTemplates[mode].cloneNode(true);
    row.dataset.rowMode = mode;
    row.classList.remove("has-error");
    row.querySelectorAll("input").forEach((input) => {
      input.value = "";
      input.disabled = false;
      input.removeAttribute("id");
      input.removeAttribute("aria-describedby");
      input.setCustomValidity("");
    });
    row.querySelector("[data-row-error]").textContent = "";
    row.dataset.rowLabel = form.dataset.candidateLabel;
    row.querySelector("[data-row-label]").textContent = "";
    row.querySelector('[name="first_name[]"]').value = values.first_name || "";
    row.querySelector('[name="last_name[]"]').value = values.last_name || "";
    row.querySelector('[name="email[]"]').value = values.email || "";
    if (sourceRow) row.dataset.sourceRow = String(sourceRow);
    if (errors.length) {
      row.classList.add("has-error");
      row.querySelector("[data-row-error]").textContent = errors.join(" ");
    }
    root.appendChild(row);
    updateRows(form, mode);
    refreshIcons();
    return row;
  }

  function setMode(form, mode) {
    form.dataset.activeMode = mode;
    modalDialog?.classList.remove("add-candidate-modal--chooser");
    form.querySelector("[data-mode-chooser]").hidden = true;
    form.querySelector("[data-candidate-footer]").hidden = false;
    form.querySelector("[data-candidate-feedback]").hidden = true;
    const addRowButton = form.querySelector("[data-add-candidate-row]");
    const excelPreview = form.querySelector("[data-excel-preview]");
    if (addRowButton) addRowButton.hidden = mode === "excel" && excelPreview.hidden;

    form.querySelectorAll("[data-mode-panel]").forEach((panel) => {
      const active = panel.dataset.modePanel === mode;
      panel.hidden = !active;
      panel.querySelectorAll("input, button").forEach((control) => {
        control.disabled = !active;
      });
    });
    updateRows(form, mode);
  }

  function showChooser(form) {
    form.dataset.activeMode = "";
    modalDialog?.classList.add("add-candidate-modal--chooser");
    form.querySelector("[data-mode-chooser]").hidden = false;
    form.querySelector("[data-candidate-footer]").hidden = true;
    const feedback = form.querySelector("[data-candidate-feedback]");
    feedback.textContent = "";
    feedback.hidden = true;
    form.querySelectorAll("[data-mode-panel]").forEach((panel) => {
      panel.hidden = true;
      panel.querySelectorAll("input, button").forEach((control) => {
        control.disabled = true;
      });
    });
  }

  document.addEventListener("click", (event) => {
    const choice = event.target.closest("[data-candidate-mode]");
    if (choice) {
      const form = choice.closest("#addCandidatesForm");
      if (form) setMode(form, choice.dataset.candidateMode);
      return;
    }

    const back = event.target.closest("[data-back-to-chooser]");
    if (back) {
      const form = back.closest("#addCandidatesForm");
      if (form) showChooser(form);
      return;
    }

    const add = event.target.closest("[data-add-candidate-row]");
    if (add) {
      const form = add.closest("#addCandidatesForm");
      if (!form || !form.dataset.activeMode) return;
      const mode = form.dataset.activeMode;
      const row = makeRow(form, mode);
      row?.querySelector("input")?.focus();
      return;
    }

    const remove = event.target.closest("[data-remove-candidate-row]");
    if (remove) {
      const form = remove.closest("#addCandidatesForm");
      const row = remove.closest("[data-candidate-row]");
      if (!form || !row || remove.disabled) return;
      const mode = row.dataset.rowMode;
      row.remove();
      updateRows(form, mode);
    }
  });

  document.addEventListener("change", async (event) => {
    if (!event.target.matches("#candidateExcelFile")) return;
    const form = event.target.closest("#addCandidatesForm");
    if (!form || !event.target.files.length) return;
    setMode(form, "excel");

    const status = form.querySelector("[data-import-status]");
    const preview = form.querySelector("[data-excel-preview]");
    const root = rowsRoot(form, "excel");
    const payload = new FormData();
    payload.append("candidate_file", event.target.files[0]);
    payload.append("action", "preview_excel");
    payload.append("csrfmiddlewaretoken", form.querySelector('[name="csrfmiddlewaretoken"]').value);
    status.classList.remove("is-success");
    status.textContent = form.dataset.importing;

    try {
      const response = await fetch(form.dataset.previewUrl, {
        method: "POST",
        body: payload,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        status.textContent = (data.errors || [form.dataset.importFailed]).join(" ");
        return;
      }

      root.replaceChildren();
      preview.hidden = false;
      const addRowButton = form.querySelector("[data-add-candidate-row]");
      if (addRowButton) addRowButton.hidden = false;
      if (!data.rows.length) {
        status.textContent = form.dataset.noImportRows;
        return;
      }

      data.rows.forEach((item) => makeRow(form, "excel", item, item.errors || [], item.row));
      const invalid = data.rows.filter((item) => item.errors && item.errors.length).length;
      status.classList.toggle("is-success", invalid === 0);
      status.textContent = invalid
        ? form.dataset.importSummary.replace("{valid}", String(data.rows.length - invalid)).replace("{invalid}", String(invalid))
        : form.dataset.importSuccess.replace("{count}", String(data.rows.length));
    } catch (error) {
      status.textContent = form.dataset.importFailed;
    } finally {
      event.target.value = "";
    }
  });

  modal.addEventListener("submit", async (event) => {
    const form = event.target.closest("#addCandidatesForm");
    if (!form) return;

    event.preventDefault();
    event.stopImmediatePropagation();
    const mode = form.dataset.activeMode;
    if (!mode) return;

    const submit = form.querySelector("[data-submit-candidates]");
    const rows = [...rowsRoot(form, mode).querySelectorAll("[data-candidate-row]")];
    rows.forEach((row) => {
      row.classList.remove("has-error");
      row.querySelector("[data-row-error]").textContent = "";
    });
    submit.disabled = true;

    try {
      const response = await fetch(form.getAttribute("action"), {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        const feedback = form.querySelector("[data-candidate-feedback]");
        feedback.hidden = false;
        feedback.textContent = (data.errors || [form.dataset.submitFailed]).join(" ");
        return;
      }

      const failed = new Map((data.errors || []).map((item) => [Number(item.row), item.message]));
      const added = new Set(data.added_rows || []);
      rows.forEach((row, index) => {
        const number = index + 1;
        if (added.has(number)) row.remove();
        else if (failed.has(number)) {
          row.classList.add("has-error");
          row.querySelector("[data-row-error]").textContent = failed.get(number);
        }
      });
      updateRows(form, mode);

      const feedback = form.querySelector("[data-candidate-feedback]");
      if (data.added_count && !failed.size) {
        feedback.hidden = false;
        feedback.classList.add("is-success");
        feedback.textContent = form.dataset.addedSummary.replace("{count}", String(data.added_count));
        setTimeout(() => {
          bootstrap.Modal.getOrCreateInstance(modal).hide();
          window.location.href = data.redirect_url || window.location.href;
        }, 650);
      } else if (data.added_count) {
        feedback.hidden = false;
        feedback.classList.add("is-success");
        feedback.textContent = form.dataset.partialSummary.replace("{count}", String(data.added_count));
      } else if (!failed.size) {
        feedback.hidden = false;
        feedback.textContent = form.dataset.noCandidates;
      } else {
        feedback.textContent = "";
      }
    } catch (error) {
      const feedback = form.querySelector("[data-candidate-feedback]");
      feedback.hidden = false;
      feedback.textContent = form.dataset.submitFailed;
    } finally {
      submit.disabled = false;
      refreshIcons();
    }
  }, true);

  document.addEventListener("input", (event) => {
    const row = event.target.closest("[data-candidate-row]");
    if (!row) return;
    row.classList.remove("has-error");
    row.querySelector("[data-row-error]").textContent = "";
  });
})();
