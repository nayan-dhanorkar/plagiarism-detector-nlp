# src/embedder.py

from sentence_transformers import SentenceTransformer
import numpy as np


class SentenceEmbedder:
    """
    Handles SBERT model loading and embedding generation
    """

    def __init__(self, model_name="all-MiniLM-L6-v2"):

        print("Loading SBERT model...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded successfully!")


    def encode(self, sentences):
        """
        Convert list of sentences into embeddings
        """

        if not sentences:
            return np.array([])

        embeddings = self.model.encode(
            sentences,
            convert_to_numpy=True,
            show_progress_bar=True
        )

        return embeddings


# Test this file directly
if __name__ == "__main__":

    test_sentences = [
        "Artificial intelligence is transforming education.",
        "AI is changing the way students learn.",
        "I love playing cricket."
    ]

    embedder = SentenceEmbedder()

    vectors = embedder.encode(test_sentences)

    print("\nNumber of sentences:", len(test_sentences))
    print("Embedding shape:", vectors.shape)
    print("Sample vector (first 5 values):")
    print(vectors[0][:5])
