# src/api.py

import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .detector import PlagiarismDetector


# ─────────────────────── Pydantic Schemas ────────────────── #

class DetectRequest(BaseModel):
    """Request body for the plain-text detect endpoint."""
    text: str


class DetectResultItem(BaseModel):
    student_sentence : str
    matched_source   : str
    similarity_score : float
    category         : str


class DetectResponse(BaseModel):
    total_sentences       : int
    plagiarized_sentences : int
    plagiarism_percent    : float
    results               : list[DetectResultItem]


# ─────────────────────── App Setup ───────────────────────── #

app = FastAPI(
    title       = "Plagiarism Detector API",
    description = "Semantic plagiarism detection using SBERT embeddings.",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ─────────────────────── Detector Init ───────────────────── #

detector = PlagiarismDetector()
detector.load_database()


# ─────────────────────── Helper ──────────────────────────── #

def _build_response(summary: dict) -> DetectResponse:
    """Converts the raw summary dict into a typed DetectResponse."""
    results = [
        DetectResultItem(
            student_sentence = item["Student Sentence"],
            matched_source   = item["Matched Source"],
            similarity_score = item["Similarity Score"],
            category         = item["Category"],
        )
        for item in summary["results"]
    ]

    return DetectResponse(
        total_sentences       = summary["total_sentences"],
        plagiarized_sentences = summary["plagiarized_sentences"],
        plagiarism_percent    = summary["plagiarism_percent"],
        results               = results,
    )


# ─────────────────────── Endpoints ───────────────────────── #

@app.post("/api/detect", response_model=DetectResponse)
def detect_text(request: DetectRequest):
    """
    Detect plagiarism from a plain-text string.

    Use this when the student pastes or types their text directly
    into the frontend input box.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    summary = detector.detect_from_text(request.text)
    return _build_response(summary)


@app.post("/api/detect-file", response_model=DetectResponse)
async def detect_file(file: UploadFile = File(...)):
    """
    Detect plagiarism from an uploaded file.

    Accepts:
      - .pdf  — academic papers, essays (text-based PDFs)
      - .txt  — plain text files

    The backend auto-extracts text, cleans it, and runs detection.
    Scanned/image-only PDFs are not supported (no OCR).
    """
    filename = file.filename or ""
    ext      = os.path.splitext(filename)[1].lower()

    ALLOWED_EXTENSIONS = {".pdf", ".txt"}

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code = 422,
            detail      = f"Unsupported file type '{ext}'. "
                          f"Please upload a .pdf or .txt file.",
        )

    # Read file bytes
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Run detection
    try:
        summary = detector.detect_from_bytes(file_bytes, filename)
    except ValueError as e:
        # Raised when no text can be extracted (e.g. scanned PDF)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")

    return _build_response(summary)


@app.post("/api/detect-with-reference", response_model=DetectResponse)
async def detect_with_reference(
    student_file: UploadFile = File(...),
    reference_file: UploadFile = File(...)
):
    """
    Detect plagiarism by comparing a student's file directly against a provided reference file.
    """
    ALLOWED_EXTENSIONS = {".pdf", ".txt"}

    # Validate student file
    s_ext = os.path.splitext(student_file.filename or "")[1].lower()
    if s_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported student file type '{s_ext}'.")

    # Validate reference file
    r_ext = os.path.splitext(reference_file.filename or "")[1].lower()
    if r_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported reference file type '{r_ext}'.")

    # Read bytes
    s_bytes = await student_file.read()
    r_bytes = await reference_file.read()

    if not s_bytes or not r_bytes:
        raise HTTPException(status_code=400, detail="One or both uploaded files are empty.")

    try:
        summary = detector.detect_with_dynamic_reference(
            student_bytes=s_bytes,
            student_filename=student_file.filename or "student.txt",
            ref_bytes=r_bytes,
            ref_filename=reference_file.filename or "reference.txt"
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")

    return _build_response(summary)


# ─────────────────────── Static Frontend ─────────────────── #

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

# Mounted last so API routes take priority over static file serving
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)