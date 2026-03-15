# src/api.py

import os
import io
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .detector import PlagiarismDetector
from .report_generator import generate_pdf_report_bytes


# ─────────────────────── Schemas ─────────────────────────── #

class DetectRequest(BaseModel):
    text: str


class DetectResultItem(BaseModel):
    student_sentence : str
    matched_source   : str
    source_file      : str
    similarity_score : float
    category         : str


class DetectResponse(BaseModel):
    total_sentences       : int
    plagiarized_sentences : int
    plagiarism_percent    : float
    source_breakdown      : dict[str, float]
    results               : list[DetectResultItem]


# ─────────────────────── App ─────────────────────────────── #

app = FastAPI(title="Plagiarism Detector API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

detector = PlagiarismDetector()
detector.load_database()


# ─────────────────────── Helper ──────────────────────────── #

def _build_response(summary: dict) -> DetectResponse:
    results = [
        DetectResultItem(
            student_sentence = item["Student Sentence"],
            matched_source   = item["Matched Source"],
            source_file      = item.get("Source File", "Unknown"),
            similarity_score = item["Similarity Score"],
            category         = item["Category"],
        )
        for item in summary["results"]
    ]
    return DetectResponse(
        total_sentences       = summary["total_sentences"],
        plagiarized_sentences = summary["plagiarized_sentences"],
        plagiarism_percent    = summary["plagiarism_percent"],
        source_breakdown      = summary.get("source_breakdown", {}),
        results               = results,
    )


# ─────────────────────── Endpoints ───────────────────────── #

@app.post("/api/detect", response_model=DetectResponse)
def detect_text(request: DetectRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    return _build_response(detector.detect_from_text(request.text))


@app.post("/api/detect-file", response_model=DetectResponse)
async def detect_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    if os.path.splitext(filename)[1].lower() not in {".pdf", ".txt"}:
        raise HTTPException(status_code=422, detail="Only .pdf or .txt files are supported.")
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    try:
        summary = detector.detect_from_bytes(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")
    return _build_response(summary)


@app.post("/api/detect-with-reference", response_model=DetectResponse)
async def detect_with_reference(
    student_file    : UploadFile       = File(...),
    reference_files : List[UploadFile] = File(...),
):
    ALLOWED = {".pdf", ".txt"}
    s_ext = os.path.splitext(student_file.filename or "")[1].lower()
    if s_ext not in ALLOWED:
        raise HTTPException(status_code=422, detail=f"Unsupported student file type '{s_ext}'.")
    s_bytes = await student_file.read()
    if not s_bytes:
        raise HTTPException(status_code=400, detail="Student file is empty.")

    ref_data_list = []
    for r in reference_files:
        r_ext = os.path.splitext(r.filename or "")[1].lower()
        if r_ext not in ALLOWED:
            raise HTTPException(status_code=422, detail=f"Unsupported reference file type '{r_ext}'.")
        r_bytes = await r.read()
        if not r_bytes:
            raise HTTPException(status_code=400, detail=f"Reference file '{r.filename}' is empty.")
        ref_data_list.append((r_bytes, r.filename or "reference.txt"))

    if not ref_data_list:
        raise HTTPException(status_code=400, detail="No valid reference files provided.")

    try:
        summary = detector.detect_with_dynamic_references(
            student_bytes=s_bytes,
            student_filename=student_file.filename or "student.txt",
            reference_files=ref_data_list,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {e}")
    return _build_response(summary)


@app.post("/api/report")
def download_report(request: DetectRequest):
    """
    Re-runs detection on the submitted text and returns a PDF report.
    Called by the Download Report button in the frontend.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    summary   = detector.detect_from_text(request.text)
    results   = summary["results"]
    pdf_bytes = generate_pdf_report_bytes(results, summary)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="plagiarism_report.pdf"'},
    )


# ─────────────────────── Static ──────────────────────────── #

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")