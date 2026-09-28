import json

from preprocessing.cleaner import clean_text
from duplicate_detection.embeddings import get_embedding
from duplicate_detection.similarity import text_similarity


# Load sample reports
with open("data/sample_reports.json", "r", encoding="utf-8") as file:
    reports = json.load(file)


# Select three reports
report_a = reports[0]  # Heavy rain in Whitefield
report_b = reports[1]  # Heavy rainfall in Whitefield
report_c = reports[3]  # Extreme heat in Delhi


# Clean the text
text_a = clean_text(report_a["text"])
text_b = clean_text(report_b["text"])
text_c = clean_text(report_c["text"])


# Generate embeddings
embedding_a = get_embedding(text_a)
embedding_b = get_embedding(text_b)
embedding_c = get_embedding(text_c)


# Calculate similarities
similarity_ab = text_similarity(embedding_a, embedding_b)
similarity_ac = text_similarity(embedding_a, embedding_c)


print("\n--- Similarity Test ---")

print(f"\nReport A: {report_a['text']}")
print(f"Report B: {report_b['text']}")
print(f"Similarity A-B: {similarity_ab:.4f}")

print(f"\nReport A: {report_a['text']}")
print(f"Report C: {report_c['text']}")
print(f"Similarity A-C: {similarity_ac:.4f}")