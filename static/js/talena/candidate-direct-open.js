document.addEventListener("DOMContentLoaded", function () {
  const root = document.querySelector("[data-candidate-direct-open]");

  if (!root) {
    return;
  }

  const targetUrl = root.dataset.targetUrl;

  if (!targetUrl) {
    return;
  }

  window.requestAnimationFrame(function () {
    window.location.replace(targetUrl);
  });
});
