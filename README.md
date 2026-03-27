# 🛡️ AI-Powered Plagiarism Detector

A semantic plagiarism detection system that identifies **Copied**, **Paraphrased**, and **Original** content using **Sentence-BERT embeddings** and **cosine similarity**.

Unlike traditional plagiarism tools that rely only on keyword matching, this system analyzes **semantic meaning** of sentences to detect rewritten or paraphrased content.

---

## 🚀 Features

- Detects **Copied, Paraphrased, and Original** sentences
- Supports **PDF and TXT file uploads**
- **Semantic similarity detection** using Sentence Transformers
- Sentence-level plagiarism analysis
- **Cosine similarity scoring**
- Interactive **modern web interface**
- Detailed plagiarism summary and sentence comparison
- CSV report generation

---

## 🧠 How It Works

1. Student text or document is uploaded.
2. Text is extracted and preprocessed.
3. Sentences are converted into **semantic embeddings** using **Sentence-BERT**.
4. Each sentence is compared with reference documents using **cosine similarity**.
5. Sentences are classified as:

| Category | Meaning |
|--------|--------|
| **Copied** | Nearly identical to source text |
| **Paraphrased** | Same meaning but different wording |
| **Original** | No significant similarity |

---

## 🛠️ Tech Stack

### Backend
- Python
- FastAPI
- Sentence Transformers
- PyTorch
- Scikit-Learn
- NLTK
- Pandas
- NumPy

### Frontend
- HTML
- CSS
- JavaScript

### NLP Model
- `all-mpnet-base-v2` (Sentence Transformers)

---

## 📂 Project Structure

```
plagiarism-detector-nlp
│
├── src/
│   ├── api.py
│   ├── detector.py
│   ├── embedder.py
│   ├── preprocess.py
│   └── similarity.py
│
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── styles.css
│
├── data/
│   └── reference_texts/
│
├── reports/
│   └── results.csv
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

Clone the repository:

```bash
git clone https://github.com/NirajBhakte/plagiarism-detector-nlp.git
cd plagiarism-detector-nlp
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

### Windows

```bash
venv\Scripts\activate
```

### Linux / Mac

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Project

Start the FastAPI server:

```bash
uvicorn src.api:app --reload
```

Open the application in browser:

```
http://127.0.0.1:8000
```

---

## 📄 API Endpoints

### Detect Plagiarism from Text

```
POST /api/detect
```

### Detect Plagiarism from File

```
POST /api/detect-file
```

Supported formats:

```
.txt
.pdf
```

---

## 📊 Example Output

| Sentence | Score | Category |
|--------|--------|--------|
Artificial intelligence is transforming industries. | 0.99 | Copied |
Many organizations are adopting AI technology. | 0.82 | Paraphrased |
Reading books improves creativity. | 0.12 | Original |

---

## 👨‍💻 Contributors

- **Niraj Bhakte**
- **Nayan Dhanorkar**
- **Mitesh Wani**
- **Maithily Patle**
---

## 📌 Future Improvements

- OCR support for scanned PDFs
- Large-scale vector database integration
- Real-time plagiarism highlighting
- Multi-document comparison
- Cloud deployment with scalable architecture

---

## 📜 License

This project is developed for **academic and educational purposes**.
