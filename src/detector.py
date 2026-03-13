# src/detector.py

import os
import pickle
import pandas as pd

from preprocess import preprocess_file, clean_text, split_into_sentences
from embedder import SentenceEmbedder
from similarity import find_best_matches


# ---------------- CONFIG ---------------- #

COPY_THRESHOLD = 0.95
PARAPHRASE_THRESHOLD = 0.65

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REFERENCE_DIR = os.path.join(BASE_DIR, "data", "reference_texts")
STUDENT_FILE = os.path.join(BASE_DIR, "data", "student_inputs", "input.txt")

EMBEDDING_FILE = os.path.join(BASE_DIR, "embeddings", "db_embeddings.pkl")

REPORT_FILE = os.path.join(BASE_DIR, "reports", "results.csv")

# ---------------------------------------- #


class PlagiarismDetector:

    def __init__(self):

        self.embedder = SentenceEmbedder()

        self.db_sentences = []
        self.db_embeddings = None

# Checks for the negation words.
    def has_negation(self, sentence):

        neg_words = [
            "not", "no", "never", "don't", "doesn't","neither",
            "didn't", "can't", "won't", "isn't", "aren't"
        ]

        s = sentence.lower()

        for word in neg_words:
            if word in s:
                return True

        return False

    # --------- Load Reference Database --------- #

    def build_database(self):

        print("\nBuilding reference database...")

        all_sentences = []

        for file in os.listdir(REFERENCE_DIR):

            path = os.path.join(REFERENCE_DIR, file)

            if file.endswith(".txt"):

                sentences = preprocess_file(path)
                all_sentences.extend(sentences)

        if not all_sentences:
            raise Exception("No reference sentences found!")

        embeddings = self.embedder.encode(all_sentences)

        # Save embeddings
        with open(EMBEDDING_FILE, "wb") as f:
            pickle.dump((all_sentences, embeddings), f)

        print("Database built successfully!")
        print("Total reference sentences:", len(all_sentences))


    # --------- Load Saved Database --------- #

    def load_database(self):

        if not os.path.exists(EMBEDDING_FILE):

            print("No database found. Building new one...")
            self.build_database()

        with open(EMBEDDING_FILE, "rb") as f:

            self.db_sentences, self.db_embeddings = pickle.load(f)

        print("Reference database loaded!")


    # --------- Core Detection Logic (Reusable) --------- #

    def _run_detection(self, student_sentences):

        if not student_sentences:
            return {
                "total_sentences": 0,
                "plagiarized_sentences": 0,
                "plagiarism_percent": 0.0,
                "results": []
            }

        student_embeddings = self.embedder.encode(student_sentences)

        matches = find_best_matches(
            student_embeddings,
            self.db_embeddings,
            top_k=3
        )

        results = []
        plag_count = 0

        for i, match_list in enumerate(matches):

            # Take best match from top-K
            j, score = match_list[0]

            student_sentence = student_sentences[i]
            source_sentence = self.db_sentences[j]

            neg1 = self.has_negation(student_sentence)
            neg2 = self.has_negation(source_sentence)

            if neg1 != neg2:
                score = score - 0.2

            # Classification
            if score >= COPY_THRESHOLD:
                label = "Copied"
                plag_count += 1

            elif score >= PARAPHRASE_THRESHOLD:
                label = "Paraphrased"
                plag_count += 1

            else:
                label = "Original"

            results.append(
                {
                    "Student Sentence": student_sentence,
                    "Matched Source": source_sentence,
                    "Similarity Score": round(score, 3),
                    "Category": label,
                }
            )

        total = len(student_sentences)

        plagiarism_percent = round((plag_count / total) * 100, 2)

        return {
            "total_sentences": total,
            "plagiarized_sentences": plag_count,
            "plagiarism_percent": plagiarism_percent,
            "results": results,
        }

    # --------- Detect Plagiarism (CLI) --------- #

    def detect(self):

        print("\nRunning plagiarism detection...")

        # Load student text
        student_sentences = preprocess_file(STUDENT_FILE)

        summary = self._run_detection(student_sentences)

        total = summary["total_sentences"]
        plag_count = summary["plagiarized_sentences"]
        plagiarism_percent = summary["plagiarism_percent"]
        results = summary["results"]

        if total == 0:
            print("No student sentences found!")
            return

        print("\n----- Detection Summary -----")
        print("Total Sentences :", total)
        print("Plagiarized     :", plag_count)
        print("Plagiarism %    :", plagiarism_percent)
        print("-----------------------------\n")

        # Save report
        df = pd.DataFrame(results)
        df.to_csv(REPORT_FILE, index=False)

        print("Detailed report saved at:")
        print(REPORT_FILE)

    # --------- Detect from Raw Text (for API) --------- #

    def detect_from_text(self, text):

        cleaned = clean_text(text)
        sentences = split_into_sentences(cleaned)

        return self._run_detection(sentences)


# --------- Run System --------- #

if __name__ == "__main__":

    detector = PlagiarismDetector()

    detector.load_database()

    detector.detect()
