# src/detector.py

import os
import pickle
import pandas as pd

from .preprocess import (
    preprocess_file,
    preprocess_raw_bytes,
    clean_text,
    split_into_sentences,
    sliding_window_chunks,        # ✅ FIX: was "sliding_chunks" — correct name
)
from .embedder import SentenceEmbedder
from .similarity import find_best_matches
from .report_generator import generate_pdf_report   # ✅ FIX: was "from .report" — correct module name


# ─────────────────────── CONFIG ─────────────────────────── #

COPY_THRESHOLD       = 0.95
PARAPHRASE_THRESHOLD = 0.65

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REFERENCE_DIR  = os.path.join(BASE_DIR, "data", "reference_texts")
STUDENT_FILE   = os.path.join(BASE_DIR, "data", "student_inputs", "input.pdf")
EMBEDDING_FILE = os.path.join(BASE_DIR, "embeddings", "db_embeddings.pkl")
REPORT_FILE    = os.path.join(BASE_DIR, "reports", "results.csv")

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}

# ─────────────────────────────────────────────────────────── #


class PlagiarismDetector:

    def __init__(self):
        self.embedder      = SentenceEmbedder()
        self.db_sentences  = []
        self.db_sources    = []
        self.db_embeddings = None

    # ─────────────────────────────────────────────────────── #
    #  NEGATION HELPER
    # ─────────────────────────────────────────────────────── #

    def has_negation(self, sentence):
        neg_words = [
            "not", "no", "never", "don't", "doesn't", "neither",
            "didn't", "can't", "won't", "isn't", "aren't",
        ]
        return any(word in sentence.lower() for word in neg_words)

    # ─────────────────────────────────────────────────────── #
    #  BUILD DATABASE
    # ─────────────────────────────────────────────────────── #

    def build_database(self):
        print("\nBuilding reference database...")

        all_sentences   = []
        all_sources     = []
        processed_files = 0

        for filename in os.listdir(REFERENCE_DIR):
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            path = os.path.join(REFERENCE_DIR, filename)
            try:
                sentences = preprocess_file(path)
                all_sentences.extend(sentences)
                all_sources.extend([filename] * len(sentences))
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

        os.makedirs(os.path.dirname(EMBEDDING_FILE), exist_ok=True)

        # ✅ Consistent tuple order: (sentences, embeddings, sources)
        with open(EMBEDDING_FILE, "wb") as f:
            pickle.dump((all_sentences, embeddings, all_sources), f)

        # Save file count for deletion detection
        with open(EMBEDDING_FILE + ".meta", "w") as f:
            f.write(str(processed_files))

        print("Database built and saved successfully!\n")

    # ─────────────────────────────────────────────────────── #
    #  LOAD DATABASE
    # ─────────────────────────────────────────────────────── #

    def _reference_files_modified(self):
        if not os.path.exists(EMBEDDING_FILE):
            return True

        db_mtime  = os.path.getmtime(EMBEDDING_FILE)
        ref_files = [
            f for f in os.listdir(REFERENCE_DIR)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        ]

        # Check deletion via saved file count
        meta_path = EMBEDDING_FILE + ".meta"
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                try:
                    if int(f.read().strip()) != len(ref_files):
                        return True
                except ValueError:
                    pass

        # Check timestamps
        for filename in ref_files:
            path = os.path.join(REFERENCE_DIR, filename)
            if os.path.getmtime(path) > db_mtime:
                return True

        return False

    def load_database(self):
        if not os.path.exists(EMBEDDING_FILE):
            print("No database found. Building new one...")
            self.build_database()
        elif self._reference_files_modified():
            print("Reference files changed. Rebuilding database...")
            self.build_database()

        with open(EMBEDDING_FILE, "rb") as f:
            data = pickle.load(f)

        # ✅ Safe unpacker — handles both tuple orderings that may exist on disk
        if len(data) == 3:
            a, b, c = data
            import numpy as np
            # Detect which element is the numpy array (embeddings)
            if isinstance(b, np.ndarray):
                # Order: (sentences, embeddings, sources) — current format
                self.db_sentences, self.db_embeddings, self.db_sources = a, b, c
            else:
                # Order: (sentences, sources, embeddings) — older format
                self.db_sentences, self.db_sources, self.db_embeddings = a, b, c
        else:
            # Legacy 2-tuple without sources
            self.db_sentences, self.db_embeddings = data
            self.db_sources = ["Unknown Reference"] * len(self.db_sentences)

        print(f"Reference database loaded! ({len(self.db_sentences)} sentences)")

    # ─────────────────────────────────────────────────────── #
    #  CORE DETECTION ENGINE
    # ─────────────────────────────────────────────────────── #

    def _run_detection(
        self,
        student_sentences,
        reference_sentences=None,
        reference_embeddings=None,
        reference_sources=None,
    ):
        if not student_sentences:
            return {
                "total_sentences"      : 0,
                "plagiarized_sentences": 0,
                "plagiarism_percent"   : 0.0,
                "source_breakdown"     : {},
                "results"              : [],
            }

        student_embeddings = self.embedder.encode(student_sentences)

        db_sent = reference_sentences  if reference_sentences  is not None else self.db_sentences
        db_emb  = reference_embeddings if reference_embeddings is not None else self.db_embeddings
        db_src  = reference_sources    if reference_sources    is not None else self.db_sources

        if not db_sent:
            return {
                "total_sentences"      : len(student_sentences),
                "plagiarized_sentences": 0,
                "plagiarism_percent"   : 0.0,
                "source_breakdown"     : {},
                "results"              : [],
            }

        matches = find_best_matches(student_embeddings, db_emb, top_k=3)

        results        = []
        plag_count     = 0
        source_matches = {}

        for i, match_list in enumerate(matches):
            j, score = match_list[0]

            student_sentence = student_sentences[i]
            source_sentence  = db_sent[j]
            source_file      = (db_src[j]
                                if db_src is not None and j < len(db_src)
                                else "Unknown")

            # Negation penalty
            if self.has_negation(student_sentence) != self.has_negation(source_sentence):
                score -= 0.2

            # Classification
            if score >= COPY_THRESHOLD:
                label = "Copied"
                plag_count += 1
                source_matches[source_file] = source_matches.get(source_file, 0) + 1
            elif score >= PARAPHRASE_THRESHOLD:
                label = "Paraphrased"
                plag_count += 1
                source_matches[source_file] = source_matches.get(source_file, 0) + 1
            else:
                label = "Original"

            results.append({
                "Student Sentence" : student_sentence,
                "Matched Source"   : source_sentence,
                "Source File"      : source_file,
                "Similarity Score" : round(score, 3),
                "Category"         : label,
            })

        total              = len(student_sentences)
        plagiarism_percent = round((plag_count / total) * 100, 2)

        source_breakdown = {
            src: round((count / total) * 100, 2)
            for src, count in source_matches.items()
        }

        summary_dict = {
            "total_sentences"      : total,
            "plagiarized_sentences": plag_count,
            "plagiarism_percent"   : plagiarism_percent,
            "source_breakdown"     : source_breakdown,
            "results"              : results,
        }

        # Auto-generate PDF report
        generate_pdf_report(results, summary_dict)

        return summary_dict

    # ─────────────────────────────────────────────────────── #
    #  ENTRY POINT 1 — CLI
    # ─────────────────────────────────────────────────────── #

    def detect(self, use_chunking=False, window_size=2):
        print("\nRunning plagiarism detection...")
        print(f"Student file : {STUDENT_FILE}")
        print(f"Mode         : {'Chunking (window=' + str(window_size) + ')' if use_chunking else 'Sentence'}")

        # ✅ FIX: preprocess_file takes strategy/window_size, not use_chunking
        strategy = "sliding_window" if use_chunking else "sentence"
        student_sentences = preprocess_file(
            STUDENT_FILE,
            strategy=strategy,
            window_size=window_size,
        )
        summary = self._run_detection(student_sentences)

        total            = summary["total_sentences"]
        plag_count       = summary["plagiarized_sentences"]
        plag_percent     = summary["plagiarism_percent"]
        source_breakdown = summary.get("source_breakdown", {})

        if total == 0:
            print("No student sentences found!")
            return

        print("\n─────── Detection Summary ───────")
        print(f"  Total Sentences : {total}")
        print(f"  Plagiarized     : {plag_count}")
        print(f"  Plagiarism %    : {plag_percent}%")
        if source_breakdown:
            print("  Source Breakdown:")
            for src, pct in source_breakdown.items():
                print(f"    - {src}: {pct}%")
        print("─────────────────────────────────\n")

        os.makedirs(os.path.dirname(REPORT_FILE), exist_ok=True)
        pd.DataFrame(summary["results"]).to_csv(REPORT_FILE, index=False)
        print(f"CSV report saved at:\n  {REPORT_FILE}")

    # ─────────────────────────────────────────────────────── #
    #  ENTRY POINT 2 — API: raw text
    # ─────────────────────────────────────────────────────── #

    def detect_from_text(self, text: str, use_chunking: bool = False, window_size: int = 2):
        cleaned   = clean_text(text)
        sentences = split_into_sentences(cleaned)

        # ✅ FIX: was importing non-existent "sliding_chunks" — use correct function
        if use_chunking and len(sentences) > 1:
            sentences = sliding_window_chunks(
                " ".join(sentences),
                window_size=window_size,
                step=1,
            )

        return self._run_detection(sentences)

    # ─────────────────────────────────────────────────────── #
    #  ENTRY POINT 3 — API: uploaded file bytes
    # ─────────────────────────────────────────────────────── #

    def detect_from_bytes(self, file_bytes: bytes, filename: str,
                          use_chunking: bool = False, window_size: int = 2):
        # ✅ FIX: preprocess_raw_bytes uses strategy= not use_chunking=
        strategy = "sliding_window" if use_chunking else "sentence"
        sentences = preprocess_raw_bytes(
            file_bytes, filename,
            strategy=strategy,
            window_size=window_size,
        )
        return self._run_detection(sentences)

    # ─────────────────────────────────────────────────────── #
    #  ENTRY POINT 4 — API: dynamic custom references
    # ─────────────────────────────────────────────────────── #

    def detect_with_dynamic_references(
        self,
        student_bytes    : bytes,
        student_filename : str,
        reference_files  : list,          # list of (bytes, filename) tuples
        use_chunking     : bool = False,
        window_size      : int  = 2,
    ):
        strategy = "sliding_window" if use_chunking else "sentence"

        student_sentences = preprocess_raw_bytes(
            student_bytes, student_filename,
            strategy=strategy, window_size=window_size,
        )

        all_ref_sentences = []
        all_ref_sources   = []

        for ref_bytes, ref_filename in reference_files:
            ref_sentences = preprocess_raw_bytes(
                ref_bytes, ref_filename,
                strategy=strategy, window_size=window_size,
            )
            all_ref_sentences.extend(ref_sentences)
            all_ref_sources.extend([ref_filename] * len(ref_sentences))

        if not all_ref_sentences:
            raise ValueError("No text could be extracted from the reference file(s).")

        ref_embeddings = self.embedder.encode(all_ref_sentences)

        return self._run_detection(
            student_sentences,
            reference_sentences  = all_ref_sentences,
            reference_embeddings = ref_embeddings,
            reference_sources    = all_ref_sources,
        )


# ─────────────────────────────────────────────────────────── #
#  CLI RUN
# ─────────────────────────────────────────────────────────── #

if __name__ == "__main__":
    detector = PlagiarismDetector()
    detector.load_database()
    detector.detect()