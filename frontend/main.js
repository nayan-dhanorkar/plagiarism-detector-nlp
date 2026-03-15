const form = document.getElementById("detect-form");
const textArea = document.getElementById("text");
const runButton = document.getElementById("run-button");
const statusText = document.getElementById("status-text");
const scannerBar = document.getElementById("scanner-bar");
const wordCountEl = document.getElementById("word-count");

// Student File
const dropZone = document.getElementById("file-drop-zone");
const fileInput = document.getElementById("file-upload");
const fileInfo = document.getElementById("file-info");
const fileNameSpan = document.getElementById("file-name");
const fileSizeSpan = document.getElementById("file-size");
const removeFileBtn = document.getElementById("remove-file");
const dropText = document.getElementById("drop-text");

// Reference File
const refDropZone = document.getElementById("ref-drop-zone");
const refFileInput = document.getElementById("ref-upload");
const refFileInfo = document.getElementById("ref-file-info");
const refFileNameSpan = document.getElementById("ref-file-name");
const refFileSizeSpan = document.getElementById("ref-file-size");
const refRemoveFileBtn = document.getElementById("ref-remove-file");
const refDropText = document.getElementById("ref-drop-text");

const noResultsEl = document.getElementById("no-results");
const resultsContent = document.getElementById("results-content");
const summaryTotalEl = document.getElementById("summary-total");
const summaryCopiedEl = document.getElementById("summary-copied");
const summaryParaphrasedEl = document.getElementById("summary-paraphrased");
const summaryOriginalEl = document.getElementById("summary-original");
const scoreRing = document.getElementById("score-ring");

// --- snipped ---
// (We will replace just the upper block and then the specific updateSummary function block in the next replacement or in a multi-replace, but multi-replace is safer)
const scoreText = document.getElementById("score-text");
const resultsList = document.getElementById("results-list");

let selectedFile = null;
let selectedRefFile = null;

// --- Textarea Word Count ---
textArea.addEventListener('input', () => {
    const text = textArea.value;
    const chars = text.length;
    const words = text.trim() ? text.trim().split(/\s+/).length : 0;
    wordCountEl.textContent = `${words} words | ${chars} chars`;
});

// --- Helper: Setup Dropzone ---
function setupDropZone(zone, input, fileHandler) {
    zone.addEventListener('click', (e) => {
        if (!e.target.classList.contains('remove-file')) {
            input.click();
        }
    });
    input.addEventListener('change', (e) => {
        if (e.target.files.length > 0) fileHandler(e.target.files[0]);
    });
    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => {
        zone.classList.remove('dragover');
    });
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) fileHandler(e.dataTransfer.files[0]);
    });
}

function validateExtension(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    return ext === 'txt' || ext === 'pdf';
}

// Setup Student File Zone
setupDropZone(dropZone, fileInput, (file) => {
    if (!validateExtension(file)) {
        setStatus("Only student .txt and .pdf files are supported.", true);
        return;
    }
    selectedFile = file;
    fileNameSpan.textContent = file.name;
    fileSizeSpan.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    fileInfo.style.display = "flex";
    dropText.style.display = "none";
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

// Setup Reference File Zone
setupDropZone(refDropZone, refFileInput, (file) => {
    if (!validateExtension(file)) {
        setStatus("Only reference .txt and .pdf files are supported.", true);
        return;
    }
    selectedRefFile = file;
    refFileNameSpan.textContent = file.name;
    refFileSizeSpan.textContent = `(${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    refFileInfo.style.display = "flex";
    refDropText.style.display = "none";
    setStatus("");
});

refRemoveFileBtn.addEventListener('click', () => {
    selectedRefFile = null;
    refFileInput.value = "";
    refFileInfo.style.display = "none";
    refDropText.style.display = "block";
});

// --- UI Helpers ---
function setLoading(isLoading) {
  if (isLoading) {
    runButton.disabled = true;
    runButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="animation: spin 1s linear infinite;"><path d="M21 12a9 9 0 1 1-6.219-8.56"></path></svg> Analyzing...`;
    statusText.textContent = selectedRefFile ? "Comparing against your uploaded reference document..." : "Analyzing against reference database...";
    scannerBar.hidden = false;
  } else {
    runButton.disabled = false;
    runButton.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> Check Plagiarism`;
    scannerBar.hidden = true;
  }
}

function setStatus(message, isError = false) {
  statusText.textContent = message || "";
  statusText.style.color = isError ? "var(--color-danger)" : "var(--text-muted)";
}

function getScoreColor(percent) {
    if (percent <= 20) return 'var(--color-safe)';
    if (percent <= 50) return 'var(--color-warn)';
    return 'var(--color-danger)';
}

function getScoreClass(percent) {
    if (percent <= 20) return 'safe';
    if (percent <= 50) return 'warn';
    return 'danger';
}

function updateSummary(data) {
  if (!data || data.total_sentences === 0) {
    resultsContent.hidden = true;
    noResultsEl.hidden = false;
    return;
  }

  resultsContent.hidden = false;
  noResultsEl.hidden = true;
  
  summaryTotalEl.textContent = data.total_sentences;

  // Count exactly how many fall into each bucket
  let copiedCount = 0;
  let paraphrasedCount = 0;
  let originalCount = 0;

  if (data.results && data.results.length > 0) {
      data.results.forEach(res => {
          if (res.category === "Copied") copiedCount++;
          else if (res.category === "Paraphrased") paraphrasedCount++;
          else originalCount++;
      });
  }

  summaryCopiedEl.textContent = copiedCount;
  summaryParaphrasedEl.textContent = paraphrasedCount;
  summaryOriginalEl.textContent = originalCount;
  
  const percent = data.plagiarism_percent ?? 0;

  // Update Progress Ring
  const radius = scoreRing.r.baseVal.value;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percent / 100) * circumference;
  
  scoreRing.style.strokeDasharray = `${circumference} ${circumference}`;
  
  setTimeout(() => {
    scoreRing.style.strokeDashoffset = offset;
    scoreRing.style.stroke = getScoreColor(percent);
  }, 50);

  let start = 0;
  const duration = 1000;
  const increment = percent / (duration / 16); 
  
  if (percent === 0) {
      scoreText.textContent = `0%`;
      scoreText.style.color = getScoreColor(percent);
  } else {
      const timer = setInterval(() => {
          start += increment;
          if (start >= percent) {
              start = percent;
              clearInterval(timer);
          }
          scoreText.textContent = `${Math.round(start)}%`;
          scoreText.style.color = getScoreColor(percent);
      }, 16);
  }
}

function renderResults(results) {
  resultsList.innerHTML = "";

  if (!results || results.length === 0) return;

  results.forEach((item, index) => {
    const rawScore = item.similarity_score;
    const percentScore = rawScore * 100;
    
    // Use the 0-100 scale for determining the color/class
    const scoreState = getScoreClass(percentScore);
    const scoreColor = getScoreColor(percentScore);
    
    const card = document.createElement("div");
    card.className = "result-card";
    card.style.borderLeftColor = scoreColor;
    card.style.animationDelay = `${index * 0.05}s`;

    card.innerHTML = `
        <div class="result-header">
            <p class="result-sentence">"${item.student_sentence}"</p>
            <span class="match-badge bg-${scoreState}">${rawScore.toFixed(3)}</span>
        </div>
        <div class="result-details">
            <strong>Category:</strong> ${item.category}<br>
            <strong>Matched Source:</strong> ${item.matched_source.substring(0, 150)}${item.matched_source.length > 150 ? '...' : ''}
        </div>
    `;

    card.addEventListener('click', () => {
        card.classList.toggle('expanded');
    });

    resultsList.appendChild(card);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  
  const text = textArea.value.trim();

  if (!text && !selectedFile) {
    setStatus("Please provide a Student Document (paste text or upload file).", true);
    return;
  }

  setLoading(true);
  setStatus("");
  
  // reset ring visual
  const radius = scoreRing.r.baseVal.value;
  scoreRing.style.strokeDashoffset = radius * 2 * Math.PI; 

  try {
    let response;

    if (selectedFile && selectedRefFile) {
        // Mode 1: File vs File
        const formData = new FormData();
        formData.append("student_file", selectedFile);
        formData.append("reference_file", selectedRefFile);
        
        response = await fetch("/api/detect-with-reference", {
            method: "POST",
            body: formData,
        });

    } else if (text && selectedRefFile) {
        // Mode 2: Text vs File (Text is converted to a virtual file Blob before uploading)
        const formData = new FormData();
        const textBlob = new Blob([text], { type: "text/plain" });
        formData.append("student_file", textBlob, "student_input.txt");
        formData.append("reference_file", selectedRefFile);
        
        response = await fetch("/api/detect-with-reference", {
            method: "POST",
            body: formData,
        });

    } else if (selectedFile && !selectedRefFile) {
        // Mode 3: Student File vs Database
        const formData = new FormData();
        formData.append("file", selectedFile);
        
        response = await fetch("/api/detect-file", {
            method: "POST",
            body: formData,
        });
    } else {
        // Mode 4: Student Text vs Database
        response = await fetch("/api/detect", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text }),
        });
    }

    if (!response.ok) {
        let errorData = await response.text();
        try {
            const json = JSON.parse(errorData);
            if (json.detail) errorData = json.detail;
        } catch(e){}
        throw new Error(errorData || `Request failed with ${response.status}`);
    }

    const data = await response.json();

    updateSummary(data);
    renderResults(data.results);
    setStatus("Detection completed successfully.");
    
    if (window.innerWidth <= 900) {
        document.getElementById("results-card").scrollIntoView({ behavior: 'smooth' });
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

const style = document.createElement('style');
style.innerHTML = `
@keyframes spin { 100% { transform: rotate(360deg); } }
`;
document.head.appendChild(style);
