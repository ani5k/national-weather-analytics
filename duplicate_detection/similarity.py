"""
duplicate_detection/similarity.py

Calculates cosine similarity between report embeddings.
"""

from sklearn.metrics.pairwise import cosine_similarity


def text_similarity(embedding_a, embedding_b) -> float:
    """
    Calculate semantic similarity between two report embeddings.

    Returns:
        Similarity score between -1 and 1.
        Higher = more semantically similar.
    """

    if embedding_a is None or embedding_b is None:
        return 0.0

    score = cosine_similarity(
        [embedding_a],
        [embedding_b]
    )[0][0]

    return float(score)