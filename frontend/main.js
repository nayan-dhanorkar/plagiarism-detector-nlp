const form         = document.getElementById("detect-form");
const textArea     = document.getElementById("text");
const runButton    = document.getElementById("run-button");
const statusText   = document.getElementById("status-text");
const scannerBar   = document.getElementById("scanner-bar");
const wordCountEl  = document.getElementById("word-count");

// Student File
const dropZone     = document.getElementById("file-drop-zone");
const fileInput    = document.getElementById("file-upload");
const fileInfo     = document.getElementById("file-info");
const fileNameSpan = document.getElementById("file-name");
const fileSizeSpan = document.getElementById("file-size");
const removeFileBtn= document.getElementById("remove-file");
const dropText     = document.getElementById("drop-text");

// Reference Files (multi)
const refDropZone  = document.getElementById("ref-drop-zone");
const refFileInput = document.getElementById("ref-upload");
const refDropText  = document.getElementById("ref-drop-text");
const refFileList  = document.getElementById("ref-file-list");   // new UL element

// Results
const noResultsEl        = document.getElementById("no-results");
const resultsContent     = document.getElementById("results-content");
const summaryTotalEl     = document.getElementById("summary-total");
const summaryCopiedEl    = document.getElementById("summary-copied");
const summaryParaphrasedEl = document.getElementById("summary-paraphrased");
const summaryOriginalEl  = document.getElementById("summary-original");
const scoreRing          = document.getElementById("score-ring");
const scoreText          = document.getElementById("score-text");
const resultsList        = document.getElementById("results-list");
const downloadReportBtn  = document.getElementById("download-report-btn");  // new button

let selectedFile    = null;
let selectedRefFiles = [];        // ← array now, not single file
let lastRequestPayload = null;    // store for report download

// ─────────────────────── Textarea word count ─────────────── //
textArea.addEventListener('input', () => {
    const text  = textArea.value;
    const chars = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    wordCountEl.textContent = `${words} words | ${chars} chars`;
});

// ─────────────────────── Dropzone helper ─────────────────── //
function setupDropZone(zone, input, fileHandler) {
    zone.addEventListener('click', (e) => {
        if (!e.target.classList.contains('remove-file')) input.click();
    });
    input.addEventListener('change', (e) => {
        Array.from(e.target.files).forEach(f => fileHandler(f));
        // Reset so same file can be re-added after removal
        input.value = "";
    });
    zone.addEventListener('dragover',  (e) => { e.preventDefault(); zone.classList.add('dragover'); });
    zone.addEventListener('dragleave', ()  => zone.classList.remove('dragover'));
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        Array.from(e.dataTransfer.files).forEach(f => fileHandler(f));
    });
}

function validateExtension(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    return ext === 'txt' || ext === 'pdf';
}

// ─────────────────────── Student file zone ───────────────── //
setupDropZone(dropZone, fileInput, (file) => {
    if (!validateExtension(file)) { setStatus("Only .txt and .pdf files are supported.", true); return; }
    selectedFile = file;
    fileNameSpan.textContent = file.name;
    fileSizeSpan.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    fileInfo.style.display   = "flex";
    dropText.style.display   = "none";
    textArea.value = "";
    textArea.dispatchEvent(new Event('input'));
    setStatus("");
});

removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    fileInput.value = "";
    fileInfo.style.display = "none";
    dropText.style.display = "block";
});

// ─────────────────────── Reference files zone (MULTI) ────── //
setupDropZone(refDropZone, refFileInput, addRefFile);

function addRefFile(file) {
    if (!validateExtension(file)) { setStatus("Only .txt and .pdf reference files are supported.", true); return; }

    // Prevent duplicate filenames
    if (selectedRefFiles.find(f => f.name === file.name)) {
        setStatus(`"${file.name}" is already added.`, true);
        return;
    }

    selectedRefFiles.push(file);
    renderRefFileList();
    setStatus("");
}

function removeRefFile(fileName) {
    selectedRefFiles = selectedRefFiles.filter(f => f.name !== fileName);
    renderRefFileList();
}

function renderRefFileList() {
    refFileList.innerHTML = "";

    if (selectedRefFiles.length === 0) {
        refDropText.style.display = "block";
        return;
    }

    refDropText.style.display = "none";

    selectedRefFiles.forEach(file => {
        const item = document.createElement("div");
        item.className = "ref-file-item";
        item.innerHTML = `
            <span class="file-name" title="${file.name}">${file.name}</span>
            <span class="file-size">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
            <button type="button" class="remove-file" data-name="${file.name}" aria-label="Remove">×</button>
        `;
        item.querySelector('.remove-file').addEventListener('click', (e) => {
            e.stopPropagation();
            removeRefFile(file.name);
        });
        refFileList.appendChild(item);
    });
}

// ─────────────────────── Score colour helpers ─────────────── //
// FIX: thresholds are on the RAW 0–1 score, not a 0–100 percent
function getBadgeColor(rawScore) {
    if (rawScore >= 0.95) return 'var(--color-danger)';   // Copied
    if (rawScore >= 0.65) return 'var(--color-warn)';     // Paraphrased
    return 'var(--color-safe)';                            // Original
}

function getBadgeClass(rawScore) {
    if (rawScore >= 0.95) return 'danger';
    if (rawScore >= 0.65) return 'warn';
    return 'safe';
}

// Overall plagiarism % uses its own colour scale (0–100 range)
function getPercentColor(percent) {
    if (percent <= 20) return 'var(--color-safe)';
    if (percent <= 50) return 'var(--color-warn)';
    return 'var(--color-danger)';
}

// ─────────────────────── UI Helpers ──────────────────────── //
function setLoading(isLoading) {
    if (isLoading) {
        runButton.disabled = true;
        runButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation:spin 1s linear infinite"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg> Analyzing...`;
        statusText.textContent = selectedRefFiles.length > 0
            ? `Comparing against ${selectedRefFiles.length} reference file(s)...`
            : "Analyzing against reference database...";
        scannerBar.hidden = false;
    } else {
        runButton.disabled = false;
        runButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Check Plagiarism`;
        scannerBar.hidden = true;
    }
}

function setStatus(message, isError = false) {
    statusText.textContent   = message || "";
    statusText.style.color   = isError ? "var(--color-danger)" : "var(--text-muted)";
}

// ─────────────────────── Summary + ring ──────────────────── //
function updateSummary(data) {
    if (!data || data.total_sentences === 0) {
        resultsContent.hidden = true;
        noResultsEl.hidden    = false;
        if (downloadReportBtn) downloadReportBtn.hidden = true;
        return;
    }

    resultsContent.hidden = false;
    noResultsEl.hidden    = true;
    if (downloadReportBtn) downloadReportBtn.hidden = false;

    summaryTotalEl.textContent = data.total_sentences;

    let copied = 0, paraphrased = 0, original = 0;
    (data.results || []).forEach(r => {
        if      (r.category === "Copied")      copied++;
        else if (r.category === "Paraphrased") paraphrased++;
        else                                   original++;
    });
    summaryCopiedEl.textContent      = copied;
    summaryParaphrasedEl.textContent = paraphrased;
    summaryOriginalEl.textContent    = original;

    const percent       = data.plagiarism_percent ?? 0;
    const radius        = scoreRing.r.baseVal.value;
    const circumference = radius * 2 * Math.PI;
    const offset        = circumference - (percent / 100) * circumference;

    scoreRing.style.strokeDasharray = `${circumference} ${circumference}`;
    setTimeout(() => {
        scoreRing.style.strokeDashoffset = offset;
        scoreRing.style.stroke           = getPercentColor(percent);
    }, 50);

    if (percent === 0) {
        scoreText.textContent  = "0%";
        scoreText.style.color  = getPercentColor(0);
    } else {
        let start = 0;
        const inc   = percent / (1000 / 16);
        const timer = setInterval(() => {
            start += inc;
            if (start >= percent) { start = percent; clearInterval(timer); }
            scoreText.textContent = `${Math.round(start)}%`;
            scoreText.style.color = getPercentColor(percent);
        }, 16);
    }

    renderSourceBreakdown(data.source_breakdown);
}

// ─────────────────────── Source breakdown ────────────────── //
function renderSourceBreakdown(breakdown) {
    const old = document.getElementById("source-breakdown-section");
    if (old) old.remove();
    if (!breakdown || Object.keys(breakdown).length === 0) return;

    const section = document.createElement("div");
    section.id = "source-breakdown-section";
    section.style.cssText = `
        margin:16px 0 8px; padding:14px 16px;
        background:rgba(255,255,255,0.04);
        border-radius:10px; border:1px solid rgba(255,255,255,0.08);
    `;

    let html = `<p style="margin:0 0 10px;font-size:0.82em;font-weight:600;
                           text-transform:uppercase;letter-spacing:0.08em;
                           color:var(--text-muted);">Source Breakdown</p>`;

    Object.entries(breakdown)
        .sort((a, b) => b[1] - a[1])
        .forEach(([src, pct]) => {
            const color = getPercentColor(pct);
            html += `
              <div style="margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;
                            font-size:0.85em;margin-bottom:4px;">
                  <span style="color:var(--text-primary);overflow:hidden;
                               text-overflow:ellipsis;white-space:nowrap;
                               max-width:70%;">${src}</span>
                  <span style="font-weight:600;color:${color};">${pct}%</span>
                </div>
                <div style="height:6px;background:rgba(255,255,255,0.08);
                            border-radius:99px;overflow:hidden;">
                  <div style="height:100%;width:${Math.min(pct,100)}%;
                              background:${color};border-radius:99px;
                              transition:width 0.6s ease;"></div>
                </div>
              </div>`;
        });

    section.innerHTML = html;
    document.querySelector(".score-sticky-header").insertAdjacentElement("afterend", section);
}

// ─────────────────────── Render result cards ─────────────── //
function renderResults(results) {
    resultsList.innerHTML = "";
    if (!results || results.length === 0) return;

    results.forEach((item, index) => {
        const rawScore   = item.similarity_score;           // 0–1 value
        // ✅ FIX: use rawScore directly for badge colour, not rawScore*100
        const badgeClass = getBadgeClass(rawScore);
        const badgeColor = getBadgeColor(rawScore);

        const card = document.createElement("div");
        card.className           = "result-card";
        card.style.borderLeftColor = badgeColor;
        card.style.animationDelay  = `${index * 0.05}s`;

        const sourceTag = item.source_file && item.source_file !== "Unknown"
            ? `<span style="font-size:0.75em;color:var(--text-muted);
                            background:rgba(255,255,255,0.06);padding:2px 7px;
                            border-radius:99px;margin-left:6px;">${item.source_file}</span>`
            : "";

        card.innerHTML = `
            <div class="result-header">
                <p class="result-sentence">"${item.student_sentence}"</p>
                <span class="match-badge bg-${badgeClass}">${rawScore.toFixed(3)}</span>
            </div>
            <div class="result-details">
                <strong>Category:</strong>
                <span style="color:${badgeColor};font-weight:600;">${item.category}</span>
                ${sourceTag}<br><br>
                <strong>Matched Source:</strong><br>
                <span style="color:var(--text-muted);">
                    ${item.matched_source.substring(0, 200)}${item.matched_source.length > 200 ? '...' : ''}
                </span>
            </div>
        `;

        card.addEventListener('click', () => card.classList.toggle('expanded'));
        resultsList.appendChild(card);
    });
}

// ─────────────────────── Download Report ─────────────────── //
if (downloadReportBtn) {
    downloadReportBtn.addEventListener('click', async () => {
        if (!lastRequestPayload) return;

        downloadReportBtn.disabled    = true;
        downloadReportBtn.textContent = "Generating...";

        try {
            const response = await fetch("/api/report", {
                method  : "POST",
                headers : { "Content-Type": "application/json" },
                body    : JSON.stringify(lastRequestPayload),
            });

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.detail || `Failed with status ${response.status}`);
            }

            // Stream PDF blob → trigger browser download
            const blob = await response.blob();
            const url  = URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href     = url;
            a.download = "plagiarism_report.pdf";
            a.click();
            URL.revokeObjectURL(url);

        } catch (err) {
            setStatus(`Report error: ${err.message}`, true);
        } finally {
            downloadReportBtn.disabled    = false;
            downloadReportBtn.innerHTML   = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg> Download Report`;
        }
    });
}

// ─────────────────────── Form submit ─────────────────────── //
form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const text = textArea.value.trim();

    if (!text && !selectedFile) {
        setStatus("Please provide a student document (paste text or upload a file).", true);
        return;
    }

    setLoading(true);
    setStatus("");
    lastRequestPayload = null;
    if (downloadReportBtn) downloadReportBtn.hidden = true;

    const radius = scoreRing.r.baseVal.value;
    scoreRing.style.strokeDashoffset = radius * 2 * Math.PI;

    try {
        let response;

        if (selectedRefFiles.length > 0) {
            // ── Mode A: vs uploaded reference file(s) ── //
            const formData = new FormData();

            if (selectedFile) {
                formData.append("student_file", selectedFile);
            } else {
                const blob = new Blob([text], { type: "text/plain" });
                formData.append("student_file", blob, "student_input.txt");
            }

            // Append every reference file under the same field name
            selectedRefFiles.forEach(f => formData.append("reference_files", f));

            // Store text for report download fallback
            lastRequestPayload = { text: text || "(file upload)" };

            response = await fetch("/api/detect-with-reference", {
                method: "POST",
                body  : formData,
            });

        } else if (selectedFile) {
            // ── Mode B: student file vs pre-loaded database ── //
            const formData = new FormData();
            formData.append("file", selectedFile);

            lastRequestPayload = { text: "(file upload)" };

            response = await fetch("/api/detect-file", {
                method: "POST",
                body  : formData,
            });

        } else {
            // ── Mode C: student text vs pre-loaded database ── //
            lastRequestPayload = { text };

            response = await fetch("/api/detect", {
                method : "POST",
                headers: { "Content-Type": "application/json" },
                body   : JSON.stringify({ text }),
            });
        }

        if (!response.ok) {
            let msg = `Request failed with status ${response.status}`;
            try {
                const errJson = await response.json();
                if (errJson.detail) {
                    msg = typeof errJson.detail === "string"
                        ? errJson.detail
                        : JSON.stringify(errJson.detail);
                }
            } catch (_) {}
            throw new Error(msg);
        }

        const data = await response.json();
        updateSummary(data);
        renderResults(data.results);
        setStatus("Detection completed successfully.");

        if (window.innerWidth <= 900) {
            document.getElementById("results-card").scrollIntoView({ behavior: "smooth" });
        }

    } catch (error) {
        console.error(error);
        setStatus(`Error: ${error.message}`, true);
        updateSummary(null);
        renderResults([]);
    } finally {
        setLoading(false);
    }
});

// Spin keyframe
const style = document.createElement('style');
style.innerHTML = `@keyframes spin { 100% { transform: rotate(360deg); } }`;
document.head.appendChild(style);