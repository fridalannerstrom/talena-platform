(function () {
  "use strict";

  function prepareFields() {
    const fields = [
      ["input[name='username']", "username"],
      ["input[name='password']", "current-password"],
      ["input[name='first_name']", "given-name"],
      ["input[name='last_name']", "family-name"],
      ["input[name='email']", "email"],
    ];

    fields.forEach(function ([selector, autocomplete]) {
      const element = document.querySelector(selector);

      if (!element) {
        return;
      }

      element.classList.add("input");
      element.setAttribute("autocomplete", autocomplete);
    });
  }

  function initLanguageDropdown() {
    const dropdown = document.querySelector(
      "[data-registration-language-dropdown]"
    );

    if (!dropdown) {
      return;
    }

    const trigger = dropdown.querySelector(
      "[data-registration-language-trigger]"
    );

    const menu = dropdown.querySelector(
      "[data-registration-language-menu]"
    );

    if (!trigger || !menu) {
      return;
    }

    function openDropdown() {
      menu.hidden = false;
      trigger.setAttribute("aria-expanded", "true");
    }

    function closeDropdown() {
      menu.hidden = true;
      trigger.setAttribute("aria-expanded", "false");
    }

    function toggleDropdown() {
      const isOpen = trigger.getAttribute("aria-expanded") === "true";

      if (isOpen) {
        closeDropdown();
      } else {
        openDropdown();
      }
    }

    trigger.addEventListener("click", function (event) {
      event.stopPropagation();
      toggleDropdown();
    });

    menu.addEventListener("click", function (event) {
      event.stopPropagation();
    });

    document.addEventListener("click", closeDropdown);

    document.addEventListener("keydown", function (event) {
      if (event.key !== "Escape") {
        return;
      }

      closeDropdown();
      trigger.focus();
    });
  }

  prepareFields();
  initLanguageDropdown();
})();
