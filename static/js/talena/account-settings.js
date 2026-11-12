document.addEventListener("DOMContentLoaded", function () {
  document
    .querySelectorAll(".talena-settings-page input[type='password']")
    .forEach(function (element) {
      element.classList.add("form-control");
    });

  const input = document.getElementById("id_avatar_image");
  const form = document.getElementById("avatarForm");
  const preview = document.getElementById("avatarPreview");

  if (!input || !form || !preview) {
    return;
  }

  input.addEventListener("change", function () {
    const file = input.files && input.files[0];

    if (!file) {
      return;
    }

    const url = URL.createObjectURL(file);
    preview.src = url;
    form.submit();
  });
});
