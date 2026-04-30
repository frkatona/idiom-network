(function () {
  function closeHelpOnEscape(event) {
    if (event.key !== "Escape") {
      return;
    }

    var modal = document.getElementById("help-modal");
    if (!modal || !modal.classList.contains("is-open")) {
      return;
    }

    var signal = document.getElementById("help-escape-signal");
    if (signal) {
      signal.click();
    }
  }

  document.addEventListener("keydown", closeHelpOnEscape);
})();
