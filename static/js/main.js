/**
 * main.js — GreenField Local Hub (GLH)
 * Shared behaviour loaded on every page via base.html.
 *
 * Covers:
 *   1. Mobile nav hamburger toggle
 *   2. Flash message auto-dismiss and close button
 *   3. Password show / hide toggle (all pages)
 *   4. Inject `now` into footer year (Jinja already does this, but kept as fallback)
 */

(function () {
  "use strict";

  /* ─────────────────────────────────────────────
     1. MOBILE NAV HAMBURGER
  ───────────────────────────────────────────── */
  const toggle = document.getElementById("nav-toggle");
  const menu   = document.getElementById("nav-menu");

  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      const isOpen = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.setAttribute("aria-label", isOpen ? "Close navigation menu" : "Open navigation menu");
    });

    // Close on outside click
    document.addEventListener("click", function (e) {
      if (!toggle.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
      }
    });

    // Close on Escape
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.classList.contains("open")) {
        menu.classList.remove("open");
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
      }
    });
  }

  /* ─────────────────────────────────────────────
     2. FLASH MESSAGE DISMISS
  ───────────────────────────────────────────── */
  const FLASH_AUTO_DISMISS_MS = 5000;

  function dismissFlash(el) {
    el.style.opacity = "0";
    el.style.transform = "translateX(20px)";
    el.style.transition = "opacity 0.3s, transform 0.3s";
    setTimeout(function () { el.remove(); }, 320);
  }

  // Close button
  document.querySelectorAll(".flash-close").forEach(function (btn) {
    btn.addEventListener("click", function () {
      dismissFlash(btn.closest(".flash"));
    });
  });

  // Auto-dismiss after timeout
  document.querySelectorAll(".flash").forEach(function (flash) {
    setTimeout(function () {
      if (flash.isConnected) dismissFlash(flash);
    }, FLASH_AUTO_DISMISS_MS);
  });

  /* ─────────────────────────────────────────────
     3. PASSWORD SHOW / HIDE TOGGLES
  ───────────────────────────────────────────── */
  const EYE_OPEN = `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
  const EYE_SHUT = `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;

  document.querySelectorAll(".password-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const targetId = btn.dataset.target;
      const input = document.getElementById(targetId);
      if (!input) return;

      const isHidden = input.type === "password";
      input.type = isHidden ? "text" : "password";
      btn.innerHTML = isHidden ? EYE_SHUT : EYE_OPEN;
      btn.setAttribute("aria-label", isHidden ? "Hide password" : "Show password");
    });
  });

})();