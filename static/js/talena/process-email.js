document.addEventListener("DOMContentLoaded", function () {
  const root = document.querySelector("[data-email-template-page]");

  if (!root) {
    return;
  }

  const status = root.querySelector("[data-copy-status]");
  const copiedPrefix = root.dataset.copiedPrefix || "Copied:";
  const copyFailedMessage =
    root.dataset.copyFailedMessage ||
    "Could not copy. Please select and copy manually.";

  function setStatus(text) {
    if (status) {
      status.textContent = text;
    }
  }

  async function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(value);
      return;
    }

    const textarea = document.createElement("textarea");
    textarea.value = value;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();

    const copied = document.execCommand("copy");
    textarea.remove();

    if (!copied) {
      throw new Error("Clipboard fallback failed");
    }
  }

  root.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", async function () {
      const value = button.dataset.copy || "";

      if (!value) {
        return;
      }

      try {
        await copyText(value);
        button.classList.add("is-copied");
        setStatus(`${copiedPrefix} ${value}`);

        window.setTimeout(function () {
          button.classList.remove("is-copied");
        }, 900);

        button.blur();
      } catch (error) {
        console.error("[PROCESS EMAIL] Copy failed:", error);
        setStatus(copyFailedMessage);
      }
    });
  });
});
