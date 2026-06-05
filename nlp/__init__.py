"""NLP pipeline package for the Opportunity Intelligence Platform.

Provides named entity recognition, entity extraction, text classification,
embedding generation, and text summarization capabilities.

Components:
    - StartupNERPipeline: spaCy-based NER with custom domain entities
    - UnifiedEntityExtractor: facade over spaCy + Ollama extraction
    - EmbeddingGenerator: SentenceTransformer embeddings (all-MiniLM-L6-v2)
    - SignalTextClassifier: signal type and sentiment classification
    - OllamaSummarizer: text summarization via Ollama
"""

from nlp.ner_pipeline import StartupNERPipeline, NERResult
from nlp.entity_extractor import UnifiedEntityExtractor
from nlp.embedding_generator import EmbeddingGenerator
from nlp.text_classifier import SignalTextClassifier
from nlp.summarizer import OllamaSummarizer

__all__ = [
    "StartupNERPipeline",
    "NERResult",
    "UnifiedEntityExtractor",
    "EmbeddingGenerator",
    "SignalTextClassifier",
    "OllamaSummarizer",
]
