import logging
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from framework.db.database import Database
from framework.rag.retrievers.base_retriever import BaseRetriever
from framework.rag.vector_dbs.pgvector import PGVectorDB

logger = logging.getLogger(__name__)


class SemanticRetriever(BaseRetriever):
    """A retriever and ingester that splits documents semantically.

    This retriever processes documents by splitting them into dynamically sized chunks,
    by building larger and larger chunks until a threshold is reached where semantic
    coherence is lost.
    """

    def __init__(self, db: Database, embedding: Embeddings, vector_store: PGVectorDB):
        """Initializes the SemanticRetriever with a database connection."""
        self.db = db
        self.embedding = embedding
        self.vector_store = vector_store
        self.language_ids = None

    def ingest(
        self,
        documents: list[Document],
    ):
        """Ingest the documents using a semantic splitter."""
        logger.info(":arrow_down: Ingesting using semantic split...")

        chunks = self.split_by_semantics(
            documents=documents,
            embedding_func=self.embedding,
            min_chunk_size=None,  # in characters, set to None for default behavior
        )

        logger.info(
            f":scissors: Created [bold]{len(chunks)}[/bold] chunks "
            "using semantic split."
        )
        return chunks

    async def retrieve(
        self, query: str, retrieve_count: int = 10
    ) -> list[tuple[Document, float]]:
        """Retrieve the top-k relevant documents for a given query."""
        retrieved = (
            await self.vector_store.get_store().similarity_search_with_relevance_scores(
                query, k=retrieve_count
            )
        )
        return retrieved
