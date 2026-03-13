# src/preprocess.py

import nltk
import os
import re
from nltk.tokenize import sent_tokenize


def load_text(file_path):
    """
    Reads text from a file and returns it as a string
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    return text


def clean_text(text):
    """
    Cleans text without breaking sentence boundaries
    """

    # Normalize spaces
    text = re.sub(r"\s+", " ", text)

    # Keep sentence punctuation
    text = re.sub(r"[^a-zA-Z0-9\s\.\,\?\!]", "", text)

    return text.strip()



def split_into_sentences(text):
    """
    Splits text into sentences using NLTK
    """
    sentences = sent_tokenize(text)

    # Remove very short sentences
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    return sentences


def preprocess_file(file_path):
    """
    Complete preprocessing pipeline
    """
    text = load_text(file_path)
    text = clean_text(text)
    sentences = split_into_sentences(text)

    return sentences


# Testing the file directly
if __name__ == "__main__":

    # Get project root directory
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    test_file = os.path.join(
        BASE_DIR,
        "data",
        "student_inputs",
        "input.txt"
    )

    sentences = preprocess_file(test_file)

    print("Total Sentences:", len(sentences))
    print("-" * 40)

    for i, s in enumerate(sentences, 1):
        print(f"{i}. {s}")
