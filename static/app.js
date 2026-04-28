// static/app.js
// Global UI behaviors shared across pages (header search, play-all hook, back-to-top).

(() => {
  document.documentElement.classList.add("js");

  function isNumeric(s) {
    return /^\d+$/.test(s);
  }

  function initHeaderSearch() {
    const sbox = document.getElementById("search-box");
    const sbtn = document.getElementById("search-btn");
    if (!sbox || !sbtn) return;

    const run = () => {
      const v = (sbox.value || "").trim();
      if (!v) return;

      if (!isNumeric(v)) {
        alert("Please enter a Kural number (digits only).");
        return;
      }

      const url = new URL(window.location.href);
      url.searchParams.set("search", v);
      url.searchParams.set("page", "1");
      window.location.href = url.toString();
    };

    sbtn.addEventListener("click", run);
    sbox.addEventListener("keydown", (e) => {
      if (e.key === "Enter") run();
    });
  }

  function initPlayAllHook() {
    const playAllBtn = document.getElementById("play-all-btn");
    if (!playAllBtn) return;
    playAllBtn.addEventListener("click", () => {
      if (typeof window.playAll === "function") window.playAll();
    });
  }

  function applyTheme(theme) {
    const isDark = theme === "dark";
    document.body.classList.toggle("theme-dark", isDark);
    const label = document.querySelector(".theme-state");
    if (label) label.textContent = isDark ? "Dark" : "Light";
  }

  function initThemeToggle() {
    const saved = localStorage.getItem("theme");
    const prefersDark =
      window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
    const initial = saved || (prefersDark ? "dark" : "light");
    applyTheme(initial);

    const toggle = document.getElementById("theme-toggle");
    if (!toggle) return;

    toggle.addEventListener("click", () => {
      const next = document.body.classList.contains("theme-dark") ? "light" : "dark";
      localStorage.setItem("theme", next);
      applyTheme(next);
    });
  }

  function initProfileMenu() {
    const menu = document.getElementById("profile-menu");
    if (!menu) return;
    const trigger = menu.querySelector(".profile-trigger");
    const dropdown = menu.querySelector(".profile-dropdown");
    if (!trigger || !dropdown) return;

    const close = () => {
      menu.classList.remove("open");
      trigger.setAttribute("aria-expanded", "false");
    };

    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      const open = menu.classList.toggle("open");
      trigger.setAttribute("aria-expanded", open ? "true" : "false");
    });

    document.addEventListener("click", (e) => {
      if (!menu.contains(e.target)) close();
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });
  }

  function initBackToTop() {
    const topBtn = document.getElementById("to-top");
    if (!topBtn) return;

    const onScroll = () => {
      topBtn.classList.toggle("show", window.scrollY > 600);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    topBtn.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  function initRevealOnScroll() {
    const items = document.querySelectorAll(".reveal-on-scroll");
    if (!items.length) return;

    const io = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("reveal-in");
          obs.unobserve(entry.target);
        });
      },
      { threshold: 0.2, rootMargin: "0px 0px -10% 0px" }
    );

    items.forEach((el) => io.observe(el));
  }

  function initParallax() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    const root = document.documentElement;
    let ticking = false;

    const update = () => {
      const y = Math.min(40, window.scrollY * 0.06);
      root.style.setProperty("--bg-parallax", `${y}px`);
      ticking = false;
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    update();
  }

  document.addEventListener("DOMContentLoaded", () => {
    initHeaderSearch();
    initPlayAllHook();
    initThemeToggle();
    initProfileMenu();
    initBackToTop();
    initRevealOnScroll();
    initParallax();
  });
})();
