/* ============================================================
   Smart Energy Analytics — Main JS
   ============================================================ */

// ── Theme toggle (dark / light mode) ─────────────────────────
(function () {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");

  function applyTheme(theme) {
    if (theme === "light") {
      root.setAttribute("data-theme", "light");
    } else {
      root.removeAttribute("data-theme");
    }
    if (toggleBtn) {
      const icon = toggleBtn.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-moon", theme !== "light");
        icon.classList.toggle("fa-sun", theme === "light");
      }
    }
  }

  // Apply saved preference (theme-init.js already set data-theme early,
  // this just syncs the icon on full load)
  applyTheme(root.getAttribute("data-theme") === "light" ? "light" : "dark");

  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      const isLight = root.getAttribute("data-theme") === "light";
      const next = isLight ? "dark" : "light";
      applyTheme(next);
      try {
        localStorage.setItem("se-theme", next);
      } catch (e) {
        /* localStorage unavailable — theme won't persist, but still works */
      }
    });
  }
})();

// ── Chart.js theme helper ──────────────────────────────────────
// Returns colors that adapt to the current dark/light theme so
// Chart.js axis labels and grid lines stay readable either way.
window.seChartTheme = function () {
  const isLight = document.documentElement.getAttribute("data-theme") === "light";
  return {
    text: isLight ? "#475569" : "#9ca3af",
    grid: isLight ? "rgba(0,0,0,.06)" : "rgba(255,255,255,.05)",
    tooltipBg: isLight ? "#ffffff" : "#1f2937",
    tooltipText: isLight ? "#1e293b" : "#e2e8f0",
  };
};

// ── Password toggle ──────────────────────────────────────────
document.querySelectorAll(".toggle-password").forEach(btn => {
  btn.addEventListener("click", () => {
    const input = document.querySelector(btn.dataset.target);
    if (!input) return;
    const isText = input.type === "text";
    input.type = isText ? "password" : "text";
    btn.querySelector("i").classList.toggle("fa-eye", isText);
    btn.querySelector("i").classList.toggle("fa-eye-slash", !isText);
  });
});

// ── Password strength meter ───────────────────────────────────
const pwInput = document.getElementById("password");
const strengthBar = document.getElementById("password-strength");
if (pwInput && strengthBar) {
  pwInput.addEventListener("input", () => {
    const val = pwInput.value;
    let score = 0;
    if (val.length >= 8) score++;
    if (/[A-Z]/.test(val)) score++;
    if (/[0-9]/.test(val)) score++;
    if (/[^A-Za-z0-9]/.test(val)) score++;
    const colors = ["danger","danger","warning","info","success"];
    const labels = ["","Weak","Fair","Good","Strong"];
    strengthBar.style.width = (score * 25) + "%";
    strengthBar.className = `progress-bar bg-${colors[score]}`;
    strengthBar.textContent = labels[score];
  });
}

// ── Auto-dismiss flash alerts after 5 s ──────────────────────
setTimeout(() => {
  document.querySelectorAll(".alert.auto-dismiss").forEach(el => {
    const bsAlert = bootstrap.Alert.getOrCreateInstance(el);
    bsAlert.close();
  });
}, 5000);

// ── Confirm dialogs ───────────────────────────────────────────
document.querySelectorAll("[data-confirm]").forEach(el => {
  el.addEventListener("click", e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});
