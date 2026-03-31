document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector("nav");
  if (nav) {
    const onScroll = () => {
      if (window.scrollY > 24) {
        nav.classList.add("shadow");
      } else {
        nav.classList.remove("shadow");
      }
    };

    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  const mobileMenu = document.getElementById("mobile-menu");
  const mobileBackdrop = document.querySelector("[data-mobile-menu-backdrop]");
  const mobileToggles = Array.from(document.querySelectorAll("[data-mobile-menu-toggle]"));
  const mobileCloseButtons = Array.from(document.querySelectorAll("[data-mobile-menu-close]"));
  const openIcon = document.querySelector(".js-menu-icon-open");
  const closeIcon = document.querySelector(".js-menu-icon-close");
  const body = document.body;
  if (mobileMenu && mobileToggles.length) {
    const closeMobileSections = () => {
      document.querySelectorAll("[data-mobile-section-toggle]").forEach((toggle) => {
        toggle.setAttribute("aria-expanded", "false");
        const indicator = toggle.querySelector("span");
        if (indicator) indicator.textContent = "+";
      });
      document.querySelectorAll("[data-mobile-section]").forEach((section) => {
        section.classList.add("hidden");
      });
    };

    const setMenuState = (open) => {
      mobileMenu.classList.toggle("hidden", !open);
      if (mobileBackdrop) mobileBackdrop.classList.toggle("hidden", !open);
      if (openIcon) openIcon.classList.toggle("hidden", open);
      if (closeIcon) closeIcon.classList.toggle("hidden", !open);
      body.classList.toggle("menu-open", open);
      mobileToggles.forEach((toggle) => {
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
      });
      if (!open) closeMobileSections();
    };

    mobileToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const isOpen = toggle.getAttribute("aria-expanded") === "true";
        setMenuState(!isOpen);
      });
    });
    mobileCloseButtons.forEach((button) => {
      button.addEventListener("click", () => setMenuState(false));
    });
    if (mobileBackdrop) {
      mobileBackdrop.addEventListener("click", () => setMenuState(false));
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") setMenuState(false);
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth >= 1024) {
        setMenuState(false);
      }
    });

    const sectionToggles = Array.from(document.querySelectorAll("[data-mobile-section-toggle]"));
    sectionToggles.forEach((toggle) => {
      toggle.addEventListener("click", () => {
        const sectionId = toggle.getAttribute("aria-controls");
        if (!sectionId) return;
        const section = document.getElementById(sectionId);
        if (!section) return;

        const willOpen = toggle.getAttribute("aria-expanded") !== "true";
        sectionToggles.forEach((otherToggle) => {
          const otherId = otherToggle.getAttribute("aria-controls");
          const otherSection = otherId ? document.getElementById(otherId) : null;
          otherToggle.setAttribute("aria-expanded", "false");
          const otherIndicator = otherToggle.querySelector("span");
          if (otherIndicator) otherIndicator.textContent = "+";
          if (otherSection) otherSection.classList.add("hidden");
        });

        toggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
        const indicator = toggle.querySelector("span");
        if (indicator) indicator.textContent = willOpen ? "\u2212" : "+";
        section.classList.toggle("hidden", !willOpen);
      });
    });

    document.querySelectorAll("#mobile-menu a[href]").forEach((link) => {
      link.addEventListener("click", () => setMenuState(false));
    });
  }

  const desktopMenus = Array.from(document.querySelectorAll("[data-desktop-menu]"));
  let desktopCloseTimer = null;
  const clearDesktopCloseTimer = () => {
    if (desktopCloseTimer) {
      window.clearTimeout(desktopCloseTimer);
      desktopCloseTimer = null;
    }
  };
  const scheduleDesktopClose = () => {
    clearDesktopCloseTimer();
    desktopCloseTimer = window.setTimeout(() => {
      closeDesktopMenus();
    }, 120);
  };
  const closeDesktopMenus = () => {
    clearDesktopCloseTimer();
    desktopMenus.forEach((menu) => {
      const dropdown = menu.querySelector("[data-desktop-dropdown]");
      if (!dropdown) return;
      dropdown.classList.add("hidden");
      dropdown.classList.remove("block");
    });
  };
  const openDesktopMenu = (menu) => {
    clearDesktopCloseTimer();
    closeDesktopMenus();
    const dropdown = menu.querySelector("[data-desktop-dropdown]");
    if (!dropdown) return;
    dropdown.classList.remove("hidden");
    dropdown.classList.add("block");
  };
  if (desktopMenus.length) {
    closeDesktopMenus();
    desktopMenus.forEach((menu) => {
      menu.addEventListener("mouseenter", () => {
        if (window.innerWidth >= 1024) openDesktopMenu(menu);
      });
      menu.addEventListener("mouseleave", () => {
        if (window.innerWidth >= 1024) scheduleDesktopClose();
      });
      menu.addEventListener("focusin", () => {
        if (window.innerWidth >= 1024) openDesktopMenu(menu);
      });
      menu.addEventListener("focusout", (event) => {
        if (window.innerWidth < 1024) return;
        if (menu.contains(event.relatedTarget)) return;
        scheduleDesktopClose();
      });
    });
    document.addEventListener("click", (event) => {
      if (window.innerWidth < 1024) return;
      const clickedInside = desktopMenus.some((menu) => menu.contains(event.target));
      if (!clickedInside) closeDesktopMenus();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDesktopMenus();
    });
    window.addEventListener("resize", () => {
      closeDesktopMenus();
    });
  }

  document.querySelectorAll("[data-dismiss-flash]").forEach((button) => {
    button.addEventListener("click", () => {
      const container = button.closest("[data-flash-message]");
      if (container) container.remove();
    });
  });
  window.setTimeout(() => {
    document.querySelectorAll("[data-flash-message]").forEach((item) => item.remove());
  }, 5000);

  document.querySelectorAll(".js-hide-on-image-error").forEach((img) => {
    img.addEventListener("error", () => {
      img.style.display = "none";
    });
  });

  document.querySelectorAll("img[data-missing-image-message]").forEach((img) => {
    img.addEventListener("error", () => {
      const parent = img.parentElement;
      if (!parent) return;
      parent.classList.add("flex", "items-center", "justify-center");
      parent.innerHTML = `<span class="text-xs text-gray-500 px-4 text-center">${img.dataset.missingImageMessage || "Image unavailable"}</span>`;
    });
  });
});
