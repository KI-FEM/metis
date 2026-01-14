from abc import ABC, abstractmethod

from langchain_core.vectorstores import VectorStoreRetriever


class BaseVectorDB(ABC):
    """Base class for vector databases."""

    @abstractmethod
    def as_retriever(self, **kwargs) -> VectorStoreRetriever:
        """Return the vector store as a retriever."""
