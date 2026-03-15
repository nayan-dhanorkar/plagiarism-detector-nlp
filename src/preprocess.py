# src/preprocess.py

import nltk
import os
import re
from nltk.tokenize import sent_tokenize

import pdfplumber


# -------------------------------------------------------- #
#  TEXT FILE UTILITIES
# -------------------------------------------------------- #

def load_text(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------------------------------------- #
#  PDF UTILITIES
# -------------------------------------------------------- #

def extract_text_from_pdf(file_path):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")

    all_text = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                all_text.append(page_text.strip())
            else:
                print(f"  [Warning] Page {page_num} yielded no text.")

    if not all_text:
        raise ValueError(
            f"No extractable text found in '{file_path}'. "
            "If it's a scanned PDF, OCR support is needed."
        )
    return "\n".join(all_text)


def extract_text_from_pdf_bytes(file_bytes: bytes) -> str:
    import io
    all_text = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                all_text.append(page_text.strip())
            else:
                print(f"  [Warning] Page {page_num} yielded no text.")

    if not all_text:
        raise ValueError("No extractable text found in the uploaded PDF.")
    return "\n".join(all_text)


# -------------------------------------------------------- #
#  CLEANING + TOKENISATION
# -------------------------------------------------------- #

def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s\.\,\?\!]", "", text)
    return text.strip()


def split_into_sentences(text):
    sentences = sent_tokenize(text)
    return [s.strip() for s in sentences if len(s.strip()) > 10]


# -------------------------------------------------------- #
#  CHUNKING
# -------------------------------------------------------- #

def sliding_chunks(sentences, window_size=2):
    """
    Original chunking function — takes a list of sentences.
    Used internally and by detect_from_text() in detector.py.

    Example with window_size=2:
      [S1, S2, S3, S4] → ["S1 S2", "S2 S3", "S3 S4"]
    """
    if not sentences:
        return []
    if len(sentences) < window_size:
        return [" ".join(sentences)]
    return [
        " ".join(sentences[i : i + window_size])
        for i in range(len(sentences) - window_size + 1)
    ]


def sliding_window_chunks(text, window_size=2, step=1):
    """
    ✅ Alias used by detector.py imports.
    Takes raw text (not a sentence list), tokenises it first,
    then applies sliding window with configurable step size.

    step=1  → maximum overlap (best for detection)
    step=window_size → no overlap (faster)
    """
    sentences = split_into_sentences(text)

    if not sentences:
        return []
    if len(sentences) <= window_size:
        return [" ".join(sentences)]

    chunks = []
    for i in range(0, len(sentences) - window_size + 1, step):
        chunks.append(" ".join(sentences[i : i + window_size]))
    return chunks


# -------------------------------------------------------- #
#  HIGH-LEVEL PIPELINE FUNCTIONS
# -------------------------------------------------------- #

def preprocess_text_file(file_path, use_chunking=False, window_size=2, strategy=None):
    text      = load_text(file_path)
    text      = clean_text(text)
    sentences = split_into_sentences(text)

    # Support both use_chunking=True and strategy="sliding_window"
    if use_chunking or strategy == "sliding_window":
        return sliding_chunks(sentences, window_size)
    return sentences


def preprocess_pdf_file(file_path, use_chunking=False, window_size=2, strategy=None):
    text      = extract_text_from_pdf(file_path)
    text      = clean_text(text)
    sentences = split_into_sentences(text)

    if use_chunking or strategy == "sliding_window":
        return sliding_chunks(sentences, window_size)
    return sentences


def preprocess_file(file_path, use_chunking=False, window_size=2, strategy=None):
    """
    Unified entry-point — auto-detects .txt or .pdf.
    Accepts both calling conventions:
      preprocess_file(path, use_chunking=True, window_size=2)   ← original style
      preprocess_file(path, strategy="sliding_window", window_size=2)  ← new style
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return preprocess_pdf_file(file_path, use_chunking, window_size, strategy)
    elif ext == ".txt":
        return preprocess_text_file(file_path, use_chunking, window_size, strategy)
    else:
        raise ValueError(
            f"Unsupported file type '{ext}'. Only .txt and .pdf are supported."
        )


def preprocess_raw_bytes(file_bytes: bytes, filename: str,
                         use_chunking=False, window_size=2, strategy=None):
    """
    API upload entry-point — accepts raw bytes.
    Accepts both use_chunking= and strategy= calling conventions.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        text = extract_text_from_pdf_bytes(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="replace")

    text      = clean_text(text)
    sentences = split_into_sentences(text)

    if use_chunking or strategy == "sliding_window":
        return sliding_chunks(sentences, window_size)
    return sentences


# -------------------------------------------------------- #
#  QUICK TEST
# -------------------------------------------------------- #

if __name__ == "__main__":
    import sys

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    txt_file = os.path.join(BASE_DIR, "data", "student_inputs", "input.txt")

    if os.path.exists(txt_file):
        print("=== SENTENCE MODE ===")
        sentences = preprocess_file(txt_file)
        print(f"Total: {len(sentences)}")
        for i, s in enumerate(sentences[:3], 1):
            print(f"  {i}. {s}")

        print("\n=== SLIDING WINDOW MODE ===")
        chunks = preprocess_file(txt_file, strategy="sliding_window", window_size=2)
        print(f"Total: {len(chunks)}")
        for i, c in enumerate(chunks[:3], 1):
            print(f"  {i}. {c}")

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        print(f"\n=== PDF TEST: {pdf_path} ===")
        sentences = preprocess_file(pdf_path)
        print(f"Total: {len(sentences)}")
        for i, s in enumerate(sentences[:3], 1):
            print(f"  {i}. {s}")