const form = document.getElementById("detect-form");
const textArea = document.getElementById("text");
const runButton = document.getElementById("run-button");
const statusText = document.getElementById("status-text");

const summaryEl = document.getElementById("summary");
const summaryTotalEl = document.getElementById("summary-total");
const summaryPlagEl = document.getElementById("summary-plag");
const summaryPercentEl = document.getElementById("summary-percent");

const noResultsEl = document.getElementById("no-results");
const tableWrapperEl = document.getElementById("table-wrapper");
const tableBody = document.querySelector("#results-table tbody");

function setLoading(isLoading) {
  if (isLoading) {
    runButton.disabled = true;
    runButton.textContent = "Running...";
    statusText.textContent = "Analysing text against the reference database…";
  } else {
    runButton.disabled = false;
    runButton.textContent = "Run detection";
  }
}

function setStatus(message, isError = false) {
  statusText.textContent = message || "";
  statusText.style.color = isError ? "#b91c1c" : "#64748b";
}

function updateSummary(data) {
  if (!data || data.total_sentences === 0) {
    summaryEl.hidden = true;
    summaryTotalEl.textContent = "0";
    summaryPlagEl.textContent = "0";
    summaryPercentEl.textContent = "";
    summaryPercentEl.className = "summary-value summary-badge";
    return;
  }

  summaryEl.hidden = false;
  summaryTotalEl.textContent = data.total_sentences;
  summaryPlagEl.textContent = data.plagiarized_sentences;

  const percent = data.plagiarism_percent ?? 0;
  summaryPercentEl.textContent = `${percent.toFixed(2)}%`;

  let levelClass = "summary-badge--low";
  if (percent >= 70) {
    levelClass = "summary-badge--high";
  } else if (percent >= 30) {
    levelClass = "summary-badge--medium";
  }

  summaryPercentEl.className = `summary-value summary-badge ${levelClass}`;
}

function renderResults(results) {
  tableBody.innerHTML = "";

  if (!results || results.length === 0) {
    noResultsEl.textContent = "No sentences detected. Try adding more text.";
    noResultsEl.hidden = false;
    tableWrapperEl.hidden = true;
    return;
  }

  noResultsEl.hidden = true;
  tableWrapperEl.hidden = false;

  results.forEach((item, index) => {
    const tr = document.createElement("tr");

    const idxTd = document.createElement("td");
    idxTd.textContent = index + 1;

    const studentTd = document.createElement("td");
    studentTd.className = "sentence-cell";
    studentTd.textContent = item.student_sentence;

    const sourceTd = document.createElement("td");
    sourceTd.className = "sentence-cell";
    sourceTd.textContent = item.matched_source;

    const scoreTd = document.createElement("td");
    const score =
      typeof item.similarity_score === "number"
        ? item.similarity_score.toFixed(3)
        : item.similarity_score;
    scoreTd.textContent = score;

    const categoryTd = document.createElement("td");
    const badge = document.createElement("span");
    const category = (item.category || "").toLowerCase();
    badge.classList.add("badge");
    if (category === "copied") {
      badge.classList.add("badge-copied");
    } else if (category === "paraphrased") {
      badge.classList.add("badge-paraphrased");
    } else {
      badge.classList.add("badge-original");
    }
    badge.textContent = item.category;
    categoryTd.appendChild(badge);

    tr.appendChild(idxTd);
    tr.appendChild(studentTd);
    tr.appendChild(sourceTd);
    tr.appendChild(scoreTd);
    tr.appendChild(categoryTd);

    tableBody.appendChild(tr);
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = textArea.value.trim();

  if (!text) {
    setStatus("Please paste some text to analyse.", true);
    return;
  }

  setLoading(true);
  setStatus("");

  try {
    const response = await fetch("/api/detect", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with ${response.status}`);
    }

    const data = await response.json();

    updateSummary(data);
    renderResults(data.results);
    setStatus("Detection completed.");
  } catch (error) {
    console.error(error);
    setStatus(
      "Could not run detection. Make sure the backend server is running.",
      true
    );
    updateSummary(null);
    renderResults([]);
  } finally {
    setLoading(false);
  }
});

