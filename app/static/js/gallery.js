document.addEventListener("DOMContentLoaded", () => {
  const items = document.querySelectorAll("[data-gallery-item]");
  const filters = document.querySelectorAll(".gallery-filter");
  const modal = document.getElementById("gallery-modal");
  const modalImage = document.getElementById("gallery-modal-image");
  const modalCaption = document.getElementById("gallery-modal-caption");
  const closeBtn = document.getElementById("gallery-close");

  items.forEach((item, index) => {
    item.style.animationDelay = `${index * 45}ms`;
    item.classList.add("opacity-0");
    requestAnimationFrame(() => {
      item.classList.remove("opacity-0");
      item.classList.add("transition-opacity", "duration-500", "opacity-100");
    });
  });

  filters.forEach((button) => {
    button.addEventListener("click", () => {
      const filter = button.dataset.filter;

      filters.forEach((f) => {
        f.classList.remove("bg-bbb-navy", "text-white");
        f.classList.add("border", "border-bbb-navy", "text-bbb-navy");
      });
      button.classList.add("bg-bbb-navy", "text-white");
      button.classList.remove("border", "border-bbb-navy", "text-bbb-navy");

      items.forEach((item) => {
        const category = item.dataset.category;
        const match = filter === "all" || category === filter;
        item.style.display = match ? "block" : "none";
      });
    });
  });

  document.querySelectorAll(".gallery-image").forEach((img) => {
    img.addEventListener("click", () => {
      if (!modal || !modalImage || !modalCaption) return;
      modalImage.src = img.src;
      modalCaption.textContent = img.dataset.caption || "";
      modal.classList.remove("hidden");
      modal.classList.add("flex");
    });
  });

  const closeModal = () => {
    if (!modal) return;
    modal.classList.add("hidden");
    modal.classList.remove("flex");
    if (modalImage) modalImage.src = "";
  };

  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (modal) {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) closeModal();
    });
  }
});
