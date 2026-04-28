// static/landing.js
// Landing-only micro FX: subtle tilt on cards + keyboard shortcut to jump to first chapter.

(() => {
  function initCardTilt() {
    const cards = document.querySelectorAll(".chapter-card");
    if (!cards.length) return;

    const max = 6; // degrees

    cards.forEach((card) => {
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        const rx = (py - 0.5) * -max;
        const ry = (px - 0.5) * max;
        card.style.transform = `translateY(-6px) rotateX(${rx}deg) rotateY(${ry}deg)`;
      });

      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  }

  function initKeyboard() {
    document.addEventListener("keydown", (e) => {
      if (e.key.toLowerCase() !== "enter") return;
      const first = document.querySelector(".chapter-card");
      if (first && first.href) window.location.href = first.href;
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initCardTilt();
    initKeyboard();
  });
})();

