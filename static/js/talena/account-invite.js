document.addEventListener("DOMContentLoaded", function () {
  const passwordFields = [
    document.getElementById("id_new_password1"),
    document.getElementById("id_new_password2")
  ];

  passwordFields.forEach(function (field) {
    if (!field) return;
    field.classList.add("input");
    field.setAttribute("autocomplete", "new-password");
  });

  const dropdown = document.querySelector(
    "[data-registration-language-dropdown]"
  );

  if (!dropdown) return;

  const trigger = dropdown.querySelector(
    "[data-registration-language-trigger]"
  );
  const menu = dropdown.querySelector(
    "[data-registration-language-menu]"
  );

  if (!trigger || !menu) return;

  function closeDropdown() {
    menu.hidden = true;
    trigger.setAttribute("aria-expanded", "false");
  }

  trigger.addEventListener("click", function (event) {
    event.stopPropagation();

    const isOpen = trigger.getAttribute("aria-expanded") === "true";
    menu.hidden = isOpen;
    trigger.setAttribute("aria-expanded", isOpen ? "false" : "true");
  });

  menu.addEventListener("click", function (event) {
    event.stopPropagation();
  });

  document.addEventListener("click", closeDropdown);

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    closeDropdown();
    trigger.focus();
  });
});
