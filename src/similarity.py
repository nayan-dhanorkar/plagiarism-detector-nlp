# src/similarity.py

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity_matrix(embeddings1, embeddings2):
    """
    Compute cosine similarity between two sets of embeddings
    """

    if len(embeddings1) == 0 or len(embeddings2) == 0:
        return np.array([])

    similarity_matrix = cosine_similarity(embeddings1, embeddings2)

    return similarity_matrix


def find_best_matches(student_embeddings, db_embeddings, top_k=3):

    similarity_matrix = compute_similarity_matrix(
        student_embeddings, db_embeddings
    )

    all_matches = []

    for i in range(len(student_embeddings)):

        scores = similarity_matrix[i]

        # Get indices of top K scores
        top_indices = np.argsort(scores)[-top_k:][::-1]

        top_matches = []

        for idx in top_indices:
            top_matches.append((idx, scores[idx]))

        all_matches.append(top_matches)

    return all_matches



# Test this file directly
if __name__ == "__main__":

    from embedder import SentenceEmbedder

    sentences_a = [
        "Artificial intelligence is transforming education.",
        "I love playing cricket."
    ]

    sentences_b = [
        "AI is changing the education system.",
        "Chess is my favourite game."
    ]

    embedder = SentenceEmbedder()

    emb_a = embedder.encode(sentences_a)
    emb_b = embedder.encode(sentences_b)

    matches = find_best_matches(emb_a, emb_b)

    print("\nSimilarity Results:")
    print("-" * 40)

    for i, j, score in matches:
        print(f"Sentence A {i+1} vs Sentence B {j+1}")
        print(f"Similarity Score: {round(score, 3)}")
        print()
