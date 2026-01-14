from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.vectorstores import VectorStore, VectorStoreRetriever

from framework.rag.embeddings.base_embedding import BaseEmbedding
from framework.rag.vector_dbs.base_vector_db import BaseVectorDB


class FAISSVectorDB(BaseVectorDB):
    """FAISS-based vector database for document retrieval.

    This class provides methods to store and retrieve documents using FAISS for
    similarity search in a vector space.

    Args:
        None

    Returns:
        None

    """

    def __init__(self) -> None:
        """Initialize the FAISS vector store."""
        self.vector_store = None

    def load_local(
        self, module_path: str, embeddings: BaseEmbedding, **kwargs
    ) -> VectorStore:
        """Load a FAISS vector store from a relative local path.

        The module_path is relative to the databases's directory.
        """
        dir_path = Path(__file__).resolve().parents[4] / "vectorstore/db_faiss"
        module_path = module_path.replace(" ", "").lower()
        return self.load_full_path(str(dir_path / module_path), embeddings, **kwargs)

    def load_full_path(
        self, module_path: Path, embeddings: BaseEmbedding, **kwargs
    ) -> VectorStore:
        """Load a FAISS vector store from a full path."""
        self.vector_store = FAISS.load_local(
            str(module_path),
            embeddings.embeddings,
            allow_dangerous_deserialization=True,
            **kwargs,
        )

        return self.vector_store

    def as_retriever(
        self,
        search_type="similarity",
        search_kwargs=None,
    ) -> VectorStoreRetriever:
        """Return the FAISS vector store as a retriever."""
        if search_kwargs is None:
            search_kwargs = {
                # number of documents to retrieve (Default: 4)
                "k": 4,
                # (threshold) threshold for the retriever to return
                "score_threshold": 0.8,
                # (MMR) number of documents to fetch from the database
                "fetch_k": 20,
                # (MMR) Diversity of results returned, 1=min diversity
                "lambda_mult": 0.5,
            }
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")
        return self.vector_store.as_retriever(
            search_type,  # alternatives: mmr, similarity_score_threshold
            search_kwargs,
        )
