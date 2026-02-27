from abc import ABC, abstractmethod

from langchain_core.embeddings.embeddings import Embeddings


class BaseEmbedding(ABC):
    """Base class for embeddings."""

    @abstractmethod
    def __init__(self) -> None:
        """Initialize the embedding."""
        self.embeddings = None

    def get_embeddings(self) -> Embeddings:
        """Return the embedding creator."""
        return self.embeddings
