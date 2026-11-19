(() => {
  const language = (document.documentElement.lang || "sv").toLowerCase();
  const isSwedish = language.startsWith("sv");

  const copy = isSwedish
    ? {
        title: "Automatisk testinbjudan",
        description:
          "Välj om nya kandidater ska få sin testinbjudan direkt när de läggs till i projektet.",
        label: "Skicka testinbjudan automatiskt",
        createHelp:
          "När inställningen är på skickas testerna direkt efter att kandidaten lagts till. Du kan ändra detta senare under Inställningar.",
        settingsHelp:
          "Ändringen gäller kandidater som läggs till efter att du sparat. Befintliga inbjudningar påverkas inte.",
      }
    : {
        title: "Automatic assessment invitation",
        description:
          "Choose whether new candidates should receive their assessment invitation as soon as they are added to the project.",
        label: "Send assessment invitation automatically",
        createHelp:
          "When enabled, assessments are sent immediately after the candidate is added. You can change this later in Settings.",
        settingsHelp:
          "The change applies to candidates added after you save. Existing invitations are not affected.",
      };

  function buildSetting({ checked = false, helpText = "" } = {}) {
    // Match the existing project-settings cards; keep the presence marker
    // to avoid overwriting a saved value if the settings fetch fails.
    const card = document.createElement("div");
    card.className = "process-preference-card automatic-invitation-setting";
    card.dataset.automaticInvitationSetting = "true";

    const marker = document.createElement("input");
    marker.type = "hidden";
    marker.name = "automatic_invitation_setting_present";
    marker.value = "1";

    const copyWrap = document.createElement("div");
    copyWrap.className = "process-preference-copy";

    const label = document.createElement("label");
    label.className = "process-preference-title";
    label.htmlFor = "automaticInvitationEnabled";
    label.textContent = copy.label;

    const description = document.createElement("p");
    description.className = "process-preference-description";
    description.id = "automaticInvitationHelp";
    description.textContent = copy.description;

    copyWrap.append(label, description);

    if (helpText) {
      const note = document.createElement("p");
      note.className = "process-preference-description process-preference-note";
      note.textContent = helpText;
      copyWrap.appendChild(note);
    }

    const control = document.createElement("div");
    control.className = "process-preference-switch";

    const input = document.createElement("input");
    input.className = "form-check-input";
    input.type = "checkbox";
    input.role = "switch";
    input.name = "automatic_invitation_enabled";
    input.id = "automaticInvitationEnabled";
    input.setAttribute("aria-describedby", description.id);
    input.checked = Boolean(checked);

    control.appendChild(input);
    card.append(marker, copyWrap, control);
    return card;
  }

  function buildCreateSetting({ checked = false } = {}) {
    // Use the same compact setting-row layout as Results and Integrity Guard.
    // Preserve the hidden presence marker so missing JS cannot alter saved data.
    const row = document.createElement("div");
    row.className = "automatic-invitation-setting wizard-setting-row";
    row.dataset.automaticInvitationSetting = "true";

    const marker = document.createElement("input");
    marker.type = "hidden";
    marker.name = "automatic_invitation_setting_present";
    marker.value = "1";

    const copyWrap = document.createElement("div");
    copyWrap.className = "wizard-setting-copy";

    const label = document.createElement("label");
    label.className = "wizard-setting-label";
    label.htmlFor = "automaticInvitationEnabled";
    label.textContent = copy.label;

    const description = document.createElement("p");
    description.className = "wizard-setting-description";
    description.textContent = copy.description;
    copyWrap.append(label, description);

    const control = document.createElement("div");
    control.className = "form-check form-switch wizard-setting-switch";

    const input = document.createElement("input");
    input.className = "form-check-input";
    input.type = "checkbox";
    input.role = "switch";
    input.name = "automatic_invitation_enabled";
    input.id = "automaticInvitationEnabled";
    input.checked = Boolean(checked);

    control.append(input);
    row.append(marker, copyWrap, control);
    return row;
  }

  function mountCreateSetting() {
    const form = document.querySelector("#processCreateWizardForm");
    const anchor = form?.querySelector("[data-wizard-automatic-invitation]");

    if (!form || !anchor || form.querySelector("[data-automatic-invitation-setting]")) {
      return false;
    }

    // When the wizard is re-rendered after a validation error, keep the choice.
    // It still persists only when the project is successfully created.
    const checked = anchor.dataset.initialEnabled === "true";
    anchor.appendChild(buildCreateSetting({ checked }));
    return true;
  }

  async function mountSettingsSetting() {
    const page = document.querySelector(".process-settings-page");
    const form = page?.querySelector('form[method="post"]');

    if (!page || !form || form.querySelector("[data-automatic-invitation-setting]")) {
      return false;
    }

    const anchor = form.querySelector("[data-process-automatic-invitation]");
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

      // After a validation error, retain the value the user attempted to save.
      // Otherwise use the persisted value from the settings endpoint.
      const checked = anchor.dataset.posted === "true"
        ? anchor.dataset.postedEnabled === "true"
        : Boolean(data.enabled);
      anchor.appendChild(
        buildSetting({ checked, helpText: copy.settingsHelp }),
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
