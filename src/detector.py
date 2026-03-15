# src/detector.py

import os
import pickle
import pandas as pd

from .preprocess import (
    preprocess_file,
    preprocess_raw_bytes,
    clean_text,
    split_into_sentences,
)
from .embedder import SentenceEmbedder
from .similarity import find_best_matches


# ─────────────────────── CONFIG ─────────────────────────── #

COPY_THRESHOLD       = 0.95   # Score >= this  →  Copied
PARAPHRASE_THRESHOLD = 0.65   # Score >= this  →  Paraphrased
                               # Below          →  Original

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REFERENCE_DIR  = os.path.join(BASE_DIR, "data", "reference_texts")
STUDENT_FILE   = os.path.join(BASE_DIR, "data", "student_inputs", "input.pdf")
EMBEDDING_FILE = os.path.join(BASE_DIR, "embeddings", "db_embeddings.pkl")
REPORT_FILE    = os.path.join(BASE_DIR, "reports", "results.csv")

# Supported reference file extensions
SUPPORTED_EXTENSIONS = {".txt", ".pdf"}

# ─────────────────────────────────────────────────────────── #


class PlagiarismDetector:

    def __init__(self):
        self.embedder = SentenceEmbedder()
        self.db_sentences  = []
        self.db_embeddings = None

    # ──────────────────────────────────────────────────────── #
    #  HELPER: Negation Check
    # ──────────────────────────────────────────────────────── #

    def has_negation(self, sentence):
        """
        Returns True if sentence contains a negation word.
        Used to penalise score when one sentence negates and the other doesn't,
        preventing false 'Paraphrased' matches like:
            "AI helps students" vs "AI does not help students"
        """
        neg_words = [
            "not", "no", "never", "don't", "doesn't", "neither",
            "didn't", "can't", "won't", "isn't", "aren't",
        ]
        s = sentence.lower()
        return any(word in s for word in neg_words)

    # ──────────────────────────────────────────────────────── #
    #  BUILD REFERENCE DATABASE
    # ──────────────────────────────────────────────────────── #

    def build_database(self):
        """
        Scans REFERENCE_DIR for .txt and .pdf files, preprocesses each one,
        embeds all sentences, and saves to disk as a pickle file.
        """
        print("\nBuilding reference database...")

        all_sentences = []
        processed_files = 0

        for filename in os.listdir(REFERENCE_DIR):
            ext = os.path.splitext(filename)[1].lower()

            # Skip unsupported file types
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            path = os.path.join(REFERENCE_DIR, filename)

            try:
                sentences = preprocess_file(path)   # auto-detects .txt / .pdf
                all_sentences.extend(sentences)
                processed_files += 1
                print(f"  ✔  {filename}  →  {len(sentences)} sentences")

            except Exception as e:
                print(f"  ✘  {filename}  →  Skipped ({e})")

        if not all_sentences:
            raise Exception(
                "No reference sentences found! "
                "Add .txt or .pdf files to data/reference_texts/"
            )

        print(f"\nTotal files processed : {processed_files}")
        print(f"Total sentences       : {len(all_sentences)}")
        print("Encoding embeddings...")

        embeddings = self.embedder.encode(all_sentences)

        # Persist to disk
        os.makedirs(os.path.dirname(EMBEDDING_FILE), exist_ok=True)
        with open(EMBEDDING_FILE, "wb") as f:
            pickle.dump((all_sentences, embeddings), f)

        print("Database built and saved successfully!\n")

    # ──────────────────────────────────────────────────────── #
    #  LOAD / CACHE MANAGEMENT
    # ──────────────────────────────────────────────────────── #

    def _reference_files_modified(self):
        """
        Returns True if any reference file (.txt or .pdf) was modified
        after the last time the embedding pickle was written.
        This ensures the database is always in sync with source files.
        """
        if not os.path.exists(EMBEDDING_FILE):
            return True

        db_mtime = os.path.getmtime(EMBEDDING_FILE)

        for filename in os.listdir(REFERENCE_DIR):
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                path = os.path.join(REFERENCE_DIR, filename)
                if os.path.getmtime(path) > db_mtime:
                    return True

        return False

    def load_database(self):
        """
        Loads the embedding database from disk.
        Auto-rebuilds if the pickle is missing or stale.
        """
        if not os.path.exists(EMBEDDING_FILE):
            print("No database found. Building new one...")
            self.build_database()

        elif self._reference_files_modified():
            print("Reference files changed. Rebuilding database...")
            self.build_database()

        with open(EMBEDDING_FILE, "rb") as f:
            self.db_sentences, self.db_embeddings = pickle.load(f)

        print(f"Reference database loaded! ({len(self.db_sentences)} sentences)")

    # ──────────────────────────────────────────────────────── #
    #  CORE DETECTION ENGINE  (shared by all entry-points)
    # ──────────────────────────────────────────────────────── #

    def _run_detection(self, student_sentences, reference_sentences=None, reference_embeddings=None):
        """
        Core logic: embeds student sentences, finds best matches in the
        reference DB (or the provided dynamic reference), applies negation
        penalty, and classifies each sentence.

        Args:
            student_sentences (list[str]): Preprocessed sentences to check.
            reference_sentences (list[str], optional): Dynamic custom reference sentences.
            reference_embeddings (np.ndarray, optional): Dynamic custom reference embeddings.

        Returns:
            dict: Detection summary.
        """
        if not student_sentences:
            return {
                "total_sentences"      : 0,
                "plagiarized_sentences": 0,
                "plagiarism_percent"   : 0.0,
                "results"              : [],
            }

        student_embeddings = self.embedder.encode(student_sentences)

        # Fallback to DB if no dynamic reference provided
        db_sent = reference_sentences if reference_sentences is not None else self.db_sentences
        db_emb  = reference_embeddings if reference_embeddings is not None else self.db_embeddings

        if not db_sent or len(db_sent) == 0:
             return {
                "total_sentences"      : len(student_sentences),
                "plagiarized_sentences": 0,
                "plagiarism_percent"   : 0.0,
                "results"              : [],
            }

        matches = find_best_matches(
            student_embeddings,
            db_emb,
            top_k=3,
        )

        results    = []
        plag_count = 0

        for i, match_list in enumerate(matches):

            j, score = match_list[0]          # Best match from top-K

            student_sentence = student_sentences[i]
            source_sentence  = db_sent[j]

            # ── Negation penalty ────────────────────────────
            # If exactly one of the two sentences has a negation, the
            # semantic meaning is likely opposite → penalise similarity.
            neg1 = self.has_negation(student_sentence)
            neg2 = self.has_negation(source_sentence)
            if neg1 != neg2:
                score -= 0.2

            # ── Classification ──────────────────────────────
            if score >= COPY_THRESHOLD:
                label = "Copied"
                plag_count += 1

            elif score >= PARAPHRASE_THRESHOLD:
                label = "Paraphrased"
                plag_count += 1

            else:
                label = "Original"

            results.append({
                "Student Sentence" : student_sentence,
                "Matched Source"   : source_sentence,
                "Similarity Score" : round(score, 3),
                "Category"         : label,
            })

        total              = len(student_sentences)
        plagiarism_percent = round((plag_count / total) * 100, 2)

        return {
            "total_sentences"      : total,
            "plagiarized_sentences": plag_count,
            "plagiarism_percent"   : plagiarism_percent,
            "results"              : results,
        }

    # ──────────────────────────────────────────────────────── #
    #  ENTRY POINT 1 — CLI  (reads from STUDENT_FILE)
    # ──────────────────────────────────────────────────────── #

    def detect(self):
        """
        CLI entry-point. Reads the student file defined by STUDENT_FILE
        (supports both .txt and .pdf), runs detection, prints a summary,
        and saves a CSV report.
        """
        print("\nRunning plagiarism detection...")
        print(f"Student file: {STUDENT_FILE}")

        student_sentences = preprocess_file(STUDENT_FILE)  # auto .txt / .pdf
        summary = self._run_detection(student_sentences)

        total              = summary["total_sentences"]
        plag_count         = summary["plagiarized_sentences"]
        plagiarism_percent = summary["plagiarism_percent"]
        results            = summary["results"]

        if total == 0:
            print("No student sentences found!")
            return

        print("\n─────── Detection Summary ───────")
        print(f"  Total Sentences : {total}")
        print(f"  Plagiarized     : {plag_count}")
        print(f"  Plagiarism %    : {plagiarism_percent}%")
        print("─────────────────────────────────\n")

        # Save CSV report
        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
        df = pd.DataFrame(results)
        df.to_csv(REPORT_FILE, index=False)
        print(f"Detailed report saved at:\n  {REPORT_FILE}")

    # ──────────────────────────────────────────────────────── #
    #  ENTRY POINT 2 — API: raw text string
    # ──────────────────────────────────────────────────────── #

    def detect_from_text(self, text: str):
        """
        Called by the API when the frontend sends raw text.

        Args:
            text (str): Pasted/typed student text.

        Returns:
            dict: Detection summary (same structure as _run_detection).
        """
        cleaned   = clean_text(text)
        sentences = split_into_sentences(cleaned)
        return self._run_detection(sentences)

    # ──────────────────────────────────────────────────────── #
    #  ENTRY POINT 3 — API: uploaded file bytes
    # ──────────────────────────────────────────────────────── #

    def detect_from_bytes(self, file_bytes: bytes, filename: str):
        """
        Called by the API when the frontend uploads a PDF or .txt file.

        Internally delegates to preprocess_raw_bytes() which auto-detects
        the format from the filename extension.

        Args:
            file_bytes (bytes): Raw bytes of the uploaded file.
            filename   (str)  : Original filename (for extension detection).

        Returns:
            dict: Detection summary.
        """
        sentences = preprocess_raw_bytes(file_bytes, filename)
        return self._run_detection(sentences)

    # ──────────────────────────────────────────────────────── #
    #  ENTRY POINT 4 — API: dynamic custom reference file
    # ──────────────────────────────────────────────────────── #

    def detect_with_dynamic_reference(self, student_bytes: bytes, student_filename: str, ref_bytes: bytes, ref_filename: str):
        """
        Called when the user uploads both a student document AND a custom reference document.
        """
        student_sentences = preprocess_raw_bytes(student_bytes, student_filename)
        ref_sentences     = preprocess_raw_bytes(ref_bytes, ref_filename)

        ref_embeddings    = self.embedder.encode(ref_sentences)

        return self._run_detection(
            student_sentences,
            reference_sentences=ref_sentences,
            reference_embeddings=ref_embeddings
        )


# ──────────────────────────────────────────────────────────── #
#  CLI RUN
# ──────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    detector = PlagiarismDetector()
    detector.load_database()
    detector.detect()