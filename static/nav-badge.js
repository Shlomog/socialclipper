// ============================================================
// Nav Badge — Shows a pulsing dot on "Processing" when jobs are active
// Shared across all pages (Create, Processing, Library)
// ============================================================

(function () {
    const POLL_INTERVAL = 4000; // 4 seconds

    function updateProcessingBadge() {
        fetch("/api/jobs")
            .then(res => res.json())
            .then(data => {
                const jobIds = Object.keys(data);
                const hasActive = jobIds.some(
                    id => data[id].status === "running" || data[id].status === "queued"
                );

                const navLink = document.querySelector('.nav a[href="/processing"]');
                if (!navLink) return;

                if (hasActive) {
                    if (!navLink.querySelector(".nav-pulse")) {
                        const dot = document.createElement("span");
                        dot.className = "nav-pulse";
                        dot.style.cssText =
                            "display:inline-block;width:8px;height:8px;background:var(--primary);" +
                            "border-radius:50%;animation:pulse 1.5s ease-in-out infinite;" +
                            "margin-left:4px;vertical-align:middle;";
                        navLink.appendChild(dot);
                    }
                } else {
                    const dot = navLink.querySelector(".nav-pulse");
                    if (dot) dot.remove();
                }
            })
            .catch(() => {});
    }

    // Add pulse animation if not already in stylesheet
    if (!document.querySelector("#nav-pulse-style")) {
        const style = document.createElement("style");
        style.id = "nav-pulse-style";
        style.textContent = `
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
        `;
        document.head.appendChild(style);
    }

    // Check immediately and then poll
    updateProcessingBadge();
    setInterval(updateProcessingBadge, POLL_INTERVAL);
})();
