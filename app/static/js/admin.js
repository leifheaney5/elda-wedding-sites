document.addEventListener("DOMContentLoaded", () => {
  const confirmLinks = document.querySelectorAll("[data-confirm]");
  confirmLinks.forEach((item) => {
    item.addEventListener("click", (event) => {
      const msg = item.getAttribute("data-confirm");
      if (msg && !window.confirm(msg)) {
        event.preventDefault();
      }
    });
  });
});
