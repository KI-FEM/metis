# pragma: exclude file
import json
import logging
import os
from typing import Any, Optional

import numpy as np
from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStoreRetriever, utils
from langchain_postgres import Column, PGEngine, PGVectorStore
from langchain_postgres.v2.indexes import HNSWIndex
from sqlalchemy.exc import ProgrammingError

from framework.db.database import Database
from framework.rag.embeddings.base_embedding import BaseEmbedding
from framework.rag.vector_dbs.base_vector_db import BaseVectorDB

logger = logging.getLogger(__name__)


class PGVectorDB(BaseVectorDB):
    """Postgres vector database for document retrieval using pgvector."""

    def __init__(
        self,
        embeddings: BaseEmbedding,
        db: Database,
        table_name: str = None,
        vector_size: int = 2560,
    ) -> None:
        """Initialize the PGVectorDB instance."""
        self.embeddings = embeddings
        self.table_name = table_name or "chunk"
        self.vector_size = vector_size
        self.vector_store = None
        self.pg_engine = None
        self.db = db
        self.index = HNSWIndex()

    async def ainit(self) -> "PGVectorDB":
        """Async initialization of the postgres vector store with pgvector."""
        connection = os.getenv("DATABASE_URL_DRIVER")
        if not connection:
            raise ValueError("DATABASE_URL_DRIVER environment variable is not set.")
        self.pg_engine = PGEngine.from_connection_string(url=connection)

        # details
        schema_name = "public"
        content_column = "content"
        embedding_column = "embedding"
        id_column = "idchunk"

        if self.db.connection is None:
            await self.db.connect()
            
        # Check if table exists, if not create it
        exists = await self.db.get_chunk_table_exists()
        if not exists:
            try:
                await self.pg_engine.ainit_vectorstore_table(
                    table_name=self.table_name,
                    vector_size=self.vector_size,
                    schema_name=schema_name,
                    content_column=content_column,
                    embedding_column=embedding_column,
                    metadata_columns=[
                        Column("idbook", "INTEGER"),
                        Column("idlanguage", "INTEGER"),
                        Column("idcompetence", "INTEGER"),
                        Column("idsubdocument", "INTEGER"),
                        Column("createdat", "TIMESTAMP"),
                        Column("updatedat", "TIMESTAMP"),
                    ],
                    id_column=Column(name=id_column, data_type="INTEGER"),
                )
            except ProgrammingError:
                # Catching the exception here
                logger.warning("Table already exists. Skipping creation.")

        embeddings = self.embeddings.get_embeddings()

        self.vector_store = await PGVectorStore.create(
            engine=self.pg_engine,
            table_name=self.table_name,
            embedding_service=embeddings,
            schema_name=schema_name,
            content_column=content_column,
            embedding_column=embedding_column,
            metadata_columns=[
                "idbook",
                "idlanguage",
                "idcompetence",
                "idsubdocument",
                "createdat",
                "updatedat",
            ],
            id_column=id_column,
            k=4,  # number of documents to retrieve (default: 4)
            fetch_k=20,  # number of documents to fetch from the database (default: 20)
            lambda_mult=0.5,  # diversity of results returned (default: 0.5)
            index_query_options=None,  # default query options
        )
        return self

    def get_store(self) -> PGVectorStore:
        """Return the Postgres vector store."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")
        return self.vector_store

    def as_retriever(
        self,
        search_type="mmr",  # one of: similarity, mmr, similarity_score_threshold
        search_kwargs=None,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
    ) -> VectorStoreRetriever:
        """Return the Postgres vector store as a retriever."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")
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
        return self.vector_store.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
        )

    async def apply_index(self):
        """Apply the vector index to the vector store."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")
        if self.vector_store.is_valid_index():
            logger.debug("Vector store already has a valid index.")
            return
        await self.vector_store.aapply_vector_index(self.index)

    async def reindex(self):
        """Reindex the vector store."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")
        await self.vector_store.areindex()

    def _generate_filter(
        self,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
    ) -> dict[str, Any]:
        """Generate a filter for the vector store."""
        filter_dict = {}
        if topic_id is not None:
            filter_dict["idtopic"] = topic_id
        if competence_id is not None:
            filter_dict["idcompetence"] = competence_id
        if language_id is not None:
            filter_dict["idlanguage"] = language_id
        return filter_dict

    async def custom_search(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
    ) -> list[Document]:
        """Perform a custom search."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        statement = """SELECT "idchunk", "idbook", "idlanguage", "idcompetence", 
        "createdat", "updatedat", "idchunk", "content", "embedding", 
        cosine_distance("embedding", %s) as distance
        FROM "public"."chunk" 
        WHERE idcompetence = %s AND idlanguage = %s
        ORDER BY embedding::halfvec(2560) <=> %s LIMIT %s;"""
        # ORDER BY embedding <=> %s::halfvec(2560) LIMIT %s;"""
        # ORDER BY "embedding" <=> %s LIMIT %s;"""

        embedding = await self.embeddings.get_embeddings().aembed_query(query)
        query_embedding = (
            f"[{','.join([str(float(dimension)) for dimension in embedding])}]"
        )

        params = (query_embedding, competence_id, language_id, query_embedding, fetch_k)
        if self.db.connection is None:
            await self.db.connect()
        results = await self.db.execute(statement, params=params)

        lambda_mult = lambda_mult if lambda_mult else self.lambda_mult
        embedding_list = [json.loads(row[8]) for row in results]
        mmr_selected = utils.maximal_marginal_relevance(
            np.array(embedding, dtype=np.float32),
            embedding_list,
            k=k,
            lambda_mult=lambda_mult,
        )

        documents_with_scores = []
        for row in results:
            documents_with_scores.append(
                (
                    Document(
                        page_content=row[7],
                        metadata={
                            "idbook": row[1],
                            "idlanguage": row[2],
                            "idcompetence": row[3],
                            "createdat": row[4],
                            "updatedat": row[5],
                            "idchunk": row[6],
                            "relevance_score": row[9],
                        },
                        id=str(row[0]),
                    ),
                    row[9],
                )
            )

        docs = [r for i, r in enumerate(documents_with_scores) if i in mmr_selected]
        return docs

    def similarity_search(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[Document]:
        """Perform a similarity search."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.similarity_search(
            query=query,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def asimilarity_search(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[Document]:
        """Perform an async similarity search."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.asimilarity_search(
            query=query,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def asimilarity_search_with_score(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform an async similarity search with scores."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.asimilarity_search_with_score(
            query=query,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def asimilarity_search_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[Document]:
        """Perform an async similarity search by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.asimilarity_search_by_vector(
            embedding=embedding,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def asimilarity_search_with_score_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform an async similarity search with scores by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.asimilarity_search_with_score_by_vector(
            embedding=embedding,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def amax_marginal_relevance_search(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[Document]:
        """Perform an async maximum marginal relevance search."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.amax_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def amax_marginal_relevance_search_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[Document]:
        """Perform an async maximum marginal relevance search by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return await self.vector_store.amax_marginal_relevance_search_by_vector(
            embedding=embedding,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    async def amax_marginal_relevance_search_with_score_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform an async maximum marginal relevance search with scores by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return (
            await self.vector_store.amax_marginal_relevance_search_with_score_by_vector(
                embedding=embedding,
                k=k,
                fetch_k=fetch_k,
                lambda_mult=lambda_mult,
                filter=self._generate_filter(
                    topic_id=topic_id,
                    competence_id=competence_id,
                    language_id=language_id,
                ),
                **kwargs,
            )
        )

    def similarity_search_with_score(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform a similarity search with scores."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.similarity_search_with_score(
            query=query,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def similarity_search_with_relevance_scores(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform a similarity search with relevance scores."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.similarity_search_with_relevance_scores(
            query=query,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def similarity_search_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[Document]:
        """Perform a similarity search by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.similarity_search_by_vector(
            embedding=embedding,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def similarity_search_with_score_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform a similarity search with scores by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.similarity_search_with_score_by_vector(
            embedding=embedding,
            k=k,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def max_marginal_relevance_search(
        self,
        query: str,
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[Document]:
        """Perform a maximum marginal relevance search."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.max_marginal_relevance_search(
            query=query,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def max_marginal_relevance_search_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[Document]:
        """Perform a maximum marginal relevance search by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.max_marginal_relevance_search_by_vector(
            embedding=embedding,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )

    def max_marginal_relevance_search_with_score_by_vector(
        self,
        embedding: list[float],
        topic_id: Optional[int] = None,
        competence_id: Optional[int] = None,
        language_id: Optional[int] = None,
        k: Optional[int] = 4,
        fetch_k: Optional[int] = 20,
        lambda_mult: float = 0.5,
        **kwargs,
    ) -> list[tuple[Document, float]]:
        """Perform a maximum marginal relevance search with scores by vector."""
        if self.vector_store is None:
            raise ValueError("Vector store has not been loaded yet.")

        return self.vector_store.max_marginal_relevance_search_with_score_by_vector(
            embedding=embedding,
            k=k,
            fetch_k=fetch_k,
            lambda_mult=lambda_mult,
            filter=self._generate_filter(
                topic_id=topic_id, competence_id=competence_id, language_id=language_id
            ),
            **kwargs,
        )
