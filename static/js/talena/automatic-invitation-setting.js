(() => {
  const language = (document.documentElement.lang || "sv").toLowerCase();
  const isSwedish = language.startsWith("sv");

  const copy = isSwedish
    ? {
        title: "Automatisk testinbjudan",
        description:
          "Välj om nya kandidater ska få sin testinbjudan direkt när de läggs till i processen.",
        label: "Skicka testinbjudan automatiskt",
        createHelp:
          "När inställningen är på skickas testerna direkt efter att kandidaten lagts till. Du kan ändra detta senare under Inställningar.",
        settingsHelp:
          "Ändringen gäller kandidater som läggs till efter att du sparat. Befintliga inbjudningar påverkas inte.",
      }
    : {
        title: "Automatic assessment invitation",
        description:
          "Choose whether new candidates should receive their assessment invitation as soon as they are added to the process.",
        label: "Send assessment invitation automatically",
        createHelp:
          "When enabled, assessments are sent immediately after the candidate is added. You can change this later in Settings.",
        settingsHelp:
          "The change applies to candidates added after you save. Existing invitations are not affected.",
      };

  function buildSetting({ checked = false, helpText = "" } = {}) {
    const section = document.createElement("div");
    section.className = "automatic-invitation-setting border-top pt-4 mt-4";
    section.dataset.automaticInvitationSetting = "true";

    const marker = document.createElement("input");
    marker.type = "hidden";
    marker.name = "automatic_invitation_setting_present";
    marker.value = "1";

    const header = document.createElement("div");
    header.className = "mb-3";

    const title = document.createElement("div");
    title.className = "fw-semibold";
    title.textContent = copy.title;

    const description = document.createElement("div");
    description.className = "text-muted small mt-1";
    description.textContent = copy.description;

    header.append(title, description);

    const control = document.createElement("div");
    control.className = "form-check form-switch mb-2";

    const input = document.createElement("input");
    input.className = "form-check-input";
    input.type = "checkbox";
    input.role = "switch";
    input.name = "automatic_invitation_enabled";
    input.id = "automaticInvitationEnabled";
    input.checked = Boolean(checked);

    const label = document.createElement("label");
    label.className = "form-check-label fw-semibold";
    label.htmlFor = input.id;
    label.textContent = copy.label;

    control.append(input, label);

    const help = document.createElement("div");
    help.className = "form-text";
    help.textContent = helpText;

    section.append(marker, header, control, help);
    return section;
  }

  function mountCreateSetting() {
    const form = document.querySelector("#processCreateWizardForm");
    const anchor = form?.querySelector(".candidate-language-section");

    if (!form || !anchor || form.querySelector("[data-automatic-invitation-setting]")) {
      return false;
    }

    anchor.insertAdjacentElement(
      "afterend",
      buildSetting({ checked: false, helpText: copy.createHelp }),
    );

    return true;
  }

  async function mountSettingsSetting() {
    const page = document.querySelector(".process-settings-page");
    const form = page?.querySelector('form[method="post"]');

    if (!page || !form || form.querySelector("[data-automatic-invitation-setting]")) {
      return false;
    }

    const languageInput = form.querySelector('input[name="candidate_language"]');
    const anchor = languageInput?.closest(".mb-4");

    if (!anchor) {
      return false;
    }

    const pathname = window.location.pathname;
    const endpoint = pathname.replace(
      /\/edit\/?$/,
      "/automatic-invitation-setting/",
    );

    if (endpoint === pathname) {
      return false;
    }

    try {
      const response = await fetch(endpoint, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      anchor.insertAdjacentElement(
        "afterend",
        buildSetting({
          checked: Boolean(data.enabled),
          helpText: copy.settingsHelp,
        }),
      );

      return true;
    } catch (error) {
      // Do not render an unchecked fallback. That could accidentally overwrite
      // an enabled saved value if the user saves the rest of the Settings form.
      console.error("Could not load automatic invitation setting", error);
      return false;
    }
  }

  function mount() {
    mountCreateSetting();
    mountSettingsSetting();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount, { once: true });
  } else {
    mount();
  }
})();
