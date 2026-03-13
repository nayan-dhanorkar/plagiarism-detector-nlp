from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

from detector import PlagiarismDetector


class DetectRequest(BaseModel):
    text: str


class DetectResultItem(BaseModel):
    student_sentence: str
    matched_source: str
    similarity_score: float
    category: str


class DetectResponse(BaseModel):
    total_sentences: int
    plagiarized_sentences: int
    plagiarism_percent: float
    results: list[DetectResultItem]


app = FastAPI(title="Plagiarism Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


detector = PlagiarismDetector()
detector.load_database()


@app.post("/api/detect", response_model=DetectResponse)
def detect(request: DetectRequest):
    summary = detector.detect_from_text(request.text)

    results = [
        DetectResultItem(
            student_sentence=item["Student Sentence"],
            matched_source=item["Matched Source"],
            similarity_score=item["Similarity Score"],
            category=item["Category"],
        )
        for item in summary["results"]
    ]

    return DetectResponse(
        total_sentences=summary["total_sentences"],
        plagiarized_sentences=summary["plagiarized_sentences"],
        plagiarism_percent=summary["plagiarism_percent"],
        results=results,
    )


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

from fastapi.staticfiles import StaticFiles

app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)

