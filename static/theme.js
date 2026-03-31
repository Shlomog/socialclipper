// ============================================================
// Theme toggle — dark is default, light is alternate
// ============================================================
(function () {
    // Apply saved theme immediately (before paint)
    const saved = localStorage.getItem("sc-theme");
    if (saved === "light") {
        document.documentElement.setAttribute("data-theme", "light");
    }

    // Inject toggle button into header
    document.addEventListener("DOMContentLoaded", () => {
        const header = document.querySelector("header");
        if (!header) return;

        const btn = document.createElement("button");
        btn.className = "theme-toggle";
        btn.setAttribute("aria-label", "Toggle light mode");
        updateIcon(btn);

        btn.addEventListener("click", () => {
            const isLight = document.documentElement.getAttribute("data-theme") === "light";
            if (isLight) {
                document.documentElement.removeAttribute("data-theme");
                localStorage.setItem("sc-theme", "dark");
            } else {
                document.documentElement.setAttribute("data-theme", "light");
                localStorage.setItem("sc-theme", "light");
            }
            updateIcon(btn);
        });

        header.appendChild(btn);
    });

    function updateIcon(btn) {
        const isLight = document.documentElement.getAttribute("data-theme") === "light";
        // Show moon in light mode (click to go dark), sun in dark mode (click to go light)
        btn.innerHTML = isLight
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
    }
})();
