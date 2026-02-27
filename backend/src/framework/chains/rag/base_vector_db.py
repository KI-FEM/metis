from abc import ABC, abstractmethod
from pathlib import Path

from chains.rag.base_embedding import BaseEmbedding
from langchain_core.vectorstores import VectorStore, VectorStoreRetriever


class BaseVectorDB(ABC):
    """Base class for vector databases."""

    @abstractmethod
    def load_local(
        self, path: Path, embeddings: BaseEmbedding, **kwargs
    ) -> VectorStore:
        """Load a vector store from a local path."""

    @abstractmethod
    def as_retriever(self, **kwargs) -> VectorStoreRetriever:
        """Return the vector store as a retriever."""