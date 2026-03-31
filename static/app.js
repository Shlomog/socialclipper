// ============================================================
// SocialClipper — Frontend Logic
// ============================================================

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// Elements
const form = $("#job-form");
const urlInput = $("#url-input");
const fileInput = $("#file-input");
const uploadArea = $("#upload-area");
const fileNameEl = $("#file-name");
const contextInput = $("#context-input");
const submitBtn = $("#submit-btn");

const inputSection = $("#input-section");
const progressSection = $("#progress-section");
const resultsSection = $("#results-section");
const errorSection = $("#error-section");

const progressBar = $("#progress-bar");
const progressLog = $("#progress-log");

let currentJobId = null;

// ---------------------------------------------------------------
// File upload handling
// ---------------------------------------------------------------
uploadArea.addEventListener("click", () => fileInput.click());

uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
});

uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
});

uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        showFileName(e.dataTransfer.files[0].name);
    }
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        showFileName(fileInput.files[0].name);
    }
});

function showFileName(name) {
    fileNameEl.textContent = name;
    fileNameEl.hidden = false;
    uploadArea.classList.add("has-file");
    // Clear URL if file is selected
    urlInput.value = "";
}

// Clear file if URL is typed
urlInput.addEventListener("input", () => {
    if (urlInput.value.trim()) {
        fileInput.value = "";
        fileNameEl.hidden = true;
        uploadArea.classList.remove("has-file");
    }
});

// ---------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------
form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const url = urlInput.value.trim();
    const file = fileInput.files[0];
    const context = contextInput.value.trim();

    if (!url && !file) {
        alert("Please paste a link or upload a video file.");
        return;
    }

    // Build form data
    const formData = new FormData();
    if (url) formData.append("url", url);
    if (file) formData.append("file", file);
    if (context) formData.append("context", context);
    const subtitlesCheck = document.getElementById("subtitles-input");
    if (subtitlesCheck && subtitlesCheck.checked) formData.append("subtitles", "on");

    // Show progress
    showSection("progress");
    progressLog.innerHTML = "";
    progressBar.style.width = "0%";

    try {
        const res = await fetch("/api/start", { method: "POST", body: formData });
        const data = await res.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        currentJobId = data.job_id;

        // Redirect to Processing page so user can track the job there
        window.location.href = "/processing";
    } catch (err) {
        showError("Failed to start processing. Is the server running?");
    }
});

// ---------------------------------------------------------------
// Progress polling via SSE
// ---------------------------------------------------------------
function pollProgress(jobId) {
    const source = new EventSource(`/api/stream/${jobId}`);
    let stepCount = 0;

    source.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "progress") {
            addProgressLine(data.message);
            // Estimate progress percentage from step numbers
            const stepMatch = data.message.match(/Step (\d)\/6/);
            if (stepMatch) {
                stepCount = parseInt(stepMatch[1]);
                progressBar.style.width = `${(stepCount / 6) * 100}%`;
            }
        } else if (data.type === "done") {
            source.close();
            progressBar.style.width = "100%";
            addProgressLine("All done!");
            setTimeout(() => showResults(data.result), 500);
        } else if (data.type === "error") {
            source.close();
            showError(data.error);
        }
    };

    source.onerror = () => {
        source.close();
        // Fall back to polling
        pollFallback(jobId);
    };
}

// Fallback polling if SSE fails
async function pollFallback(jobId) {
    const poll = async () => {
        try {
            const res = await fetch(`/api/status/${jobId}`);
            const data = await res.json();

            // Show any new progress
            const log = progressLog.children.length;
            for (let i = log; i < data.progress.length; i++) {
                addProgressLine(data.progress[i]);
            }

            if (data.status === "done") {
                progressBar.style.width = "100%";
                showResults(data.result);
            } else if (data.status === "error") {
                showError(data.error);
            } else {
                setTimeout(poll, 1000);
            }
        } catch {
            setTimeout(poll, 2000);
        }
    };
    poll();
}

function addProgressLine(msg) {
    const p = document.createElement("p");
    p.textContent = msg;
    progressLog.appendChild(p);
    progressLog.scrollTop = progressLog.scrollHeight;
}

// ---------------------------------------------------------------
// Results display
// ---------------------------------------------------------------
function showResults(result) {
    showSection("results");

    // Summary
    $("#result-title").textContent = result.source_name;
    $("#result-summary").textContent = result.summary;

    const themesEl = $("#result-themes");
    themesEl.innerHTML = "";
    (result.key_themes || []).forEach((t) => {
        const span = document.createElement("span");
        span.className = "tag";
        span.textContent = t;
        themesEl.appendChild(span);
    });

    // Download all button
    $("#download-all-btn").href = `/api/download-all/${currentJobId}`;

    // Clip cards
    const container = $("#clips-container");
    container.innerHTML = "";

    result.clips.forEach((clip) => {
        const card = document.createElement("div");
        card.className = "clip-card";

        const videoUrl = clip.video_file
            ? `/api/clip/${currentJobId}/${clip.video_file}`
            : null;

        card.innerHTML = `
            <h3>${clip.title}</h3>
            <div class="clip-meta">
                <span class="tag platform">${clip.platform_name}</span>
                <span class="tag">${clip.content_type}</span>
                <span class="tag pillar">${clip.brand_pillar}</span>
            </div>
            ${videoUrl ? `<video class="clip-video" controls preload="metadata">
                <source src="${videoUrl}" type="video/mp4">
            </video>` : ""}
            <div class="draft-box">${escapeHtml(clip.draft_text)}</div>
            <div class="clip-actions">
                <button class="btn-copy" onclick="copyDraft(this, ${JSON.stringify(clip.draft_text).replace(/"/g, '&quot;')})">
                    Copy Draft
                </button>
                ${videoUrl ? `<a class="btn-download-clip" href="${videoUrl}" download="${clip.video_file}">
                    Download Clip
                </a>` : ""}
            </div>
        `;

        container.appendChild(card);
    });
}

// ---------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------
function showSection(name) {
    inputSection.hidden = name !== "input";
    progressSection.hidden = name !== "progress";
    resultsSection.hidden = name !== "results";
    errorSection.hidden = name !== "error";
}

function showError(msg) {
    showSection("error");
    $("#error-message").textContent = msg;
}

function resetUI() {
    showSection("input");
    urlInput.value = "";
    fileInput.value = "";
    contextInput.value = "";
    fileNameEl.hidden = true;
    uploadArea.classList.remove("has-file");
    currentJobId = null;
}

function copyDraft(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        setTimeout(() => {
            btn.textContent = "Copy Draft";
            btn.classList.remove("copied");
        }, 2000);
    });
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}
