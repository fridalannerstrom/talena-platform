(function () {
  "use strict";

  const modal = document.getElementById("addCandidateModal");
  const body = document.getElementById("addCandidateModalBody");
  if (!modal || !body) return;

  function refreshIcons() {
    if (window.feather) window.feather.replace();
  }

  function rowsRoot(form) {
    return form.querySelector("[data-candidate-rows]");
  }

  function updateRows(form) {
    const rows = [...rowsRoot(form).querySelectorAll("[data-candidate-row]")];
    rows.forEach((row, index) => {
      row.querySelector("[data-row-label]").textContent =
        row.dataset.rowLabel.replace("{n}", String(index + 1));
      const remove = row.querySelector("[data-remove-candidate-row]");
      remove.disabled = rows.length === 1;
      row.dataset.rowIndex = String(index + 1);
    });
  }

  function makeRow(form, values = {}, errors = [], sourceRow = null) {
    const root = rowsRoot(form);
    const template = form._candidateRowTemplate || root.querySelector("[data-candidate-row]");
    if (!template) return null;
    form._candidateRowTemplate = template.cloneNode(true);
    const row = form._candidateRowTemplate.cloneNode(true);
    row.classList.remove("has-error");
    row.querySelectorAll("input").forEach((input) => {
      input.value = "";
      input.removeAttribute("id");
      input.removeAttribute("aria-describedby");
      input.setCustomValidity("");
    });
    row.querySelector("[data-row-error]").textContent = "";
    row.dataset.rowLabel = form.dataset.candidateLabel.replace("{n}", "{n}");
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
    updateRows(form);
    refreshIcons();
    return row;
  }

  document.addEventListener("click", (event) => {
    const add = event.target.closest("[data-add-candidate-row]");
    if (add) {
      const form = add.closest("#addCandidatesForm");
      if (!form) return;
      makeRow(form);
      rowsRoot(form).lastElementChild.querySelector("input").focus();
      return;
    }

    const remove = event.target.closest("[data-remove-candidate-row]");
    if (remove) {
      const form = remove.closest("#addCandidatesForm");
      const row = remove.closest("[data-candidate-row]");
      if (!form || !row || remove.disabled) return;
      row.remove();
      updateRows(form);
    }
  });

  document.addEventListener("change", async (event) => {
    if (!event.target.matches("#candidateExcelFile")) return;
    const form = event.target.closest("#addCandidatesForm");
    if (!form || !event.target.files.length) return;

    const status = form.querySelector("[data-import-status]");
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

      const root = rowsRoot(form);
      root.replaceChildren();
      if (!data.rows.length) {
        status.textContent = form.dataset.noImportRows;
        makeRow(form);
        return;
      }

      data.rows.forEach((item) => {
        makeRow(form, item, item.errors || [], item.row);
      });
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
    const submit = form.querySelector("[data-submit-candidates]");
    const rows = [...rowsRoot(form).querySelectorAll("[data-candidate-row]")];
    rows.forEach((row) => {
      row.classList.remove("has-error");
      row.querySelector("[data-row-error]").textContent = "";
    });
    submit.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        const status = form.querySelector("[data-import-status]");
        status.textContent = (data.errors || [form.dataset.submitFailed]).join(" ");
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
      updateRows(form);

      const status = form.querySelector("[data-import-status]");
      if (data.added_count && !failed.size) {
        status.classList.add("is-success");
        status.textContent = form.dataset.addedSummary.replace("{count}", String(data.added_count));
        setTimeout(() => {
          bootstrap.Modal.getOrCreateInstance(modal).hide();
          window.location.href = data.redirect_url || window.location.href;
        }, 650);
      } else if (data.added_count) {
        status.classList.add("is-success");
        status.textContent = form.dataset.partialSummary.replace("{count}", String(data.added_count));
      } else if (!failed.size) {
        status.textContent = form.dataset.noCandidates;
      }
    } catch (error) {
      form.querySelector("[data-import-status]").textContent = form.dataset.submitFailed;
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
