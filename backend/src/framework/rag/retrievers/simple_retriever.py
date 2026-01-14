import logging
import sys
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from framework.db.database import Database
from framework.rag.embeddings.base_embedding import BaseEmbedding
from framework.rag.retrievers.base_retriever import BaseRetriever
from framework.rag.vector_dbs.pgvector import PGVectorDB

logger = logging.getLogger(__name__)


class SimpleRetriever(BaseRetriever):
    """A retriever that simply returns the documents retrieved from the vector store."""

    def __init__(
        self,
        db: Database,
        embedding: BaseEmbedding,
        vector_store: PGVectorDB,
    ):
        """Initialize the SimpleRetriever."""
        self.db = db
        self.embedding = embedding
        self.vector_store = vector_store

    async def ingest(self, documents: list[Document]):
        """Ingest documents into the vector store."""
        return await self.ingest_markdown_header_split(documents=documents)

    async def ingest_markdown_header_split(
        self,
        documents: list[Document],
        return_each_line=False,
        strip_headers=True,
    ):
        """Ingest documents into the vector store splitting by markdown headers."""
        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents..."
        )
        chunks = await self.split_by_header(
            documents=documents,
            return_each_line=return_each_line,
            strip_headers=strip_headers,
        )
        return chunks

    async def ingest_with_augmented_questions(
        self,
        documents: list[Document],
        llms: list[BaseChatModel],
        return_each_line=False,
        strip_headers=True,
        questions_per_header=20,
    ):
        """Ingest documents into the vector store with questions."""
        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents "
            "with questions..."
        )
        chunks = await self.split_by_header(
            documents,
            return_each_line=return_each_line,
            strip_headers=strip_headers,
            augmented=True,
            questions_per_header=questions_per_header,
            llms=llms,
            llm_fallback=llms[-1] if llms else None,
        )
        return chunks

    async def retrieve(
        self,
        query: str,
        retrieve_count: int = 4,
    ) -> list[tuple[Document, float]]:
        """Retrieve documents from the vector store."""
        logger.debug(
            f":mag: Retrieving documents for query: [italic]'{query}'[/italic]"
        )
        retrieved = (
            await self.vector_store.get_store().similarity_search_with_relevance_scores(
                query, k=retrieve_count
            )
        )
        return retrieved
