(function () {
  function initDeadlinePicker(control) {
    const input = control.querySelector('input[type="datetime-local"]');
    const display = control.querySelector("[data-deadline-picker-display]");
    if (!input || !display) return;

    function renderValue() {
      if (!input.value) {
        display.textContent = control.dataset.placeholder || "Choose date and time";
        display.classList.add("is-placeholder");
        return;
      }

      const parts = input.value.split("T");
      const dateParts = (parts[0] || "").split("-").map(Number);
      const timeParts = (parts[1] || "00:00").split(":").map(Number);
      const selected = new Date(
        dateParts[0],
        (dateParts[1] || 1) - 1,
        dateParts[2] || 1,
        timeParts[0] || 0,
        timeParts[1] || 0
      );
      display.textContent = new Intl.DateTimeFormat(
        document.documentElement.lang || navigator.language,
        { dateStyle: "medium", timeStyle: "short" }
      ).format(selected);
      display.classList.remove("is-placeholder");
    }

    input.addEventListener("input", renderValue);
    input.addEventListener("change", renderValue);
    renderValue();
  }

  document.querySelectorAll("[data-deadline-picker-control]").forEach(initDeadlinePicker);
})();
