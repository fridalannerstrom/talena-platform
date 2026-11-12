(function () {
  "use strict";
  const root = document.querySelector("[data-report-branding]");
  if (!root) return;

  const picker = root.querySelector("[data-branding-picker]");
  const hex = root.querySelector("#id_primary_color");
  const focus = root.querySelector("#id_cover_focus_y");
  const focusLabel = root.querySelector("[data-branding-focus-value]");
  const cover = root.querySelector("[data-branding-cover]");
  const photo = root.querySelector("[data-branding-cover-photo]");
  const logo = root.querySelector("[data-branding-logo]");
  const logoFile = root.querySelector("#id_logo");
  const coverFile = root.querySelector("#id_cover_image");
  const removeLogo = root.querySelector("#id_remove_logo");
  const removeCover = root.querySelector("#id_remove_cover_image");
  const company = logo.querySelector("span")?.textContent || cover.querySelector(".company-branding-cover-company")?.textContent || "Talena";
  const originalLogo = root.dataset.logoUrl || "";
  const originalCover = root.dataset.coverUrl || "";
  let temporaryLogo = null;
  let temporaryCover = null;

  function rgb(color) {
    return [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16));
  }
  function mix(hexValue, destination, amount) {
    return "#" + rgb(hexValue).map((x, i) =>
      Math.round(x * (1 - amount) + destination[i] * amount).toString(16).padStart(2, "0")
    ).join("").toUpperCase();
  }
  function luminance(color) {
    const linear = rgb(color).map(x => {
      const c = x / 255;
      return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return .2126 * linear[0] + .7152 * linear[1] + .0722 * linear[2];
  }
  function contrast(a, b) {
    const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (values[0] + .05) / (values[1] + .05);
  }
  function updateColor(value) {
    if (!/^#[0-9A-Fa-f]{6}$/.test(value)) return;
    const normalized = value.toUpperCase();
    cover.style.setProperty("--branding-primary", normalized);
    cover.style.setProperty(
      "--branding-foreground",
      contrast(normalized, "#141414") >= contrast(normalized, "#FFFFFF") ? "#141414" : "#FFFFFF"
    );
    const shades = {
      primary: normalized, medium: mix(normalized, [255, 255, 255], .62),
      light: mix(normalized, [255, 255, 255], .91),
      dark: mix(normalized, [0, 0, 0], .27)
    };
    Object.entries(shades).forEach(([key, val]) => {
      const node = root.querySelector('[data-swatch="' + key + '"]');
      if (node) node.style.backgroundColor = val;
    });
  }
  picker.addEventListener("input", () => {
    hex.value = picker.value.toUpperCase();
    updateColor(hex.value);
  });
  hex.addEventListener("input", () => {
    updateColor(hex.value);
    if (/^#[0-9A-Fa-f]{6}$/.test(hex.value)) picker.value = hex.value;
  });

  function updateFocus() {
    const value = Math.max(0, Math.min(100, Number(focus.value) || 0));
    cover.style.setProperty("--branding-focus", value + "%");
    focusLabel.textContent = value + "%";
  }
  focus.addEventListener("input", updateFocus);
  updateFocus();

  function displayLogo(url) {
    logo.replaceChildren();
    if (url) {
      const image = document.createElement("img");
      image.src = url;
      image.alt = company;
      logo.append(image);
    } else {
      const label = document.createElement("span");
      label.textContent = company;
      logo.append(label);
    }
  }
  function displayCover(url) {
    photo.style.backgroundImage = url ? 'url("' + url.replace(/"/g, "%22") + '")' : "";
  }
  function previewFile(file, kind) {
    if (kind === "logo" && temporaryLogo) URL.revokeObjectURL(temporaryLogo);
    if (kind === "cover" && temporaryCover) URL.revokeObjectURL(temporaryCover);
    const url = file ? URL.createObjectURL(file) : null;
    if (kind === "logo") {
      temporaryLogo = url;
      displayLogo(url || (removeLogo?.checked ? "" : originalLogo));
    } else {
      temporaryCover = url;
      displayCover(url || (removeCover?.checked ? "" : originalCover));
    }
  }
  logoFile.addEventListener("change", () => previewFile(logoFile.files?.[0], "logo"));
  coverFile.addEventListener("change", () => previewFile(coverFile.files?.[0], "cover"));
  removeLogo?.addEventListener("change", () => {
    if (removeLogo.checked) logoFile.value = "";
    previewFile(logoFile.files?.[0], "logo");
  });
  removeCover?.addEventListener("change", () => {
    if (removeCover.checked) coverFile.value = "";
    previewFile(coverFile.files?.[0], "cover");
  });
  window.addEventListener("pagehide", () => {
    if (temporaryLogo) URL.revokeObjectURL(temporaryLogo);
    if (temporaryCover) URL.revokeObjectURL(temporaryCover);
  }, { once: true });
})();
