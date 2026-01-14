import datetime
import logging
import sys
from pathlib import Path

from langchain_community.document_compressors import FlashrankRerank
from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.db.database import Database
from framework.db.db_types import SubDocumentDB
from framework.rag.embeddings.base_embedding import BaseEmbedding
from framework.rag.embeddings.hf_embedding import HFEmbedding
from framework.rag.retrievers.base_retriever import BaseRetriever
from framework.rag.vector_dbs.pgvector import PGVectorDB

logger = logging.getLogger(__name__)


class SubDocRetriever(BaseRetriever):
    """A retriever and ingester splitting into subdocuments and embedding its chunks.

    This retriever processes documents by splitting them into sub-documents based on
    token count, generating summaries for each sub-document. It then creates smaller
    chunks from these sub-documents, prepends the summary, embeds them, and stores them
    in a vector database.
    """

    def __init__(
        self,
        db: Database,
        embedding: BaseEmbedding,
        vector_store: PGVectorDB,
        llms: list[BaseChatModel],
    ):
        """Initializes the SubDocRetriever with a database connection.

        Args:
            db (Database): The database connection to use.
            embedding (BaseEmbedding): The embedding model to use for chunk embeddings.
            vector_store (PGVectorDB): The vector store for storing and retrieving.
            llms (list[BaseChatModel]): LLMs for processing. Last one is fallback.

        """
        self.db = db
        self.embedding = embedding
        self.vector_store = vector_store
        self.llms = llms
        self.language_ids = None
        self.alt_retriever = None
        self.alt_retriever_timestamp = None

    async def get_language_id_by_locale(self, locale: LocaleType) -> int:
        """Get the language ID for a specific locale."""
        if self.language_ids is None:
            languages = await self.db.get_languages()
            self.language_ids = {lang.code: lang.idlanguage for lang in languages}
        return self.language_ids.get(locale, None)

    async def ingest(
        self,
        documents: list[Document],
        subdoc_size: int = 5000,
        subdoc_overlap=500,
        chunk_size=500,
        chunk_overlap=100,
        progress=None,
    ) -> list[Document]:  # pragma: no cover
        """Ingests documents by splitting them into sub-documents and chunks."""
        chunks = []
        sub_doc_count = 0

        # split into big subdocuments
        subdocuments = await self.split_into_subdocuments_by_tokens(
            documents,
            chunk_size=subdoc_size,
            chunk_overlap=subdoc_overlap,
            prepend_summary=False,
        )

        logger.info(
            f":scissors: Created [bold]{len(subdocuments)}[/bold] subdocuments from "
            f"[bold]{len(documents)}[/bold] documents."
        )

        task_id = progress.add_task("Chunking subdocuments", total=len(subdocuments))

        # create chunks for subdocuments
        for sub_doc in subdocuments:
            book = await self.db.get_book_by_code(sub_doc.metadata["book_code"])
            if not book:
                book = (await self.db.get_books())[0]  # Fallback to first book
                logger.warning(
                    f":warning: Book with code [bold]{sub_doc.metadata['book_code']}"
                    "[/bold] not found in database. Setting book to default Book: "
                    f"{book.code}."
                )
            competence = await self.db.get_competence_by_code(
                sub_doc.metadata["competence"]
            )
            if not competence:
                competence = await self.db.get_competences()[0]
                logger.warning(
                    ":warning: Competence with code [bold]"
                    f"{sub_doc.metadata['competence']}[/bold] not found in database. "
                    f"Setting competence to default Competence: {competence.code}."
                )
            topic = await self.db.get_topic_by_code(sub_doc.metadata["topic"])
            if not topic:
                topic = await self.db.get_topics()[0]
                logger.warning(
                    ":warning: Topic with code [bold]"
                    f"{sub_doc.metadata['topic']}[/bold] not found in database. "
                    f"Setting topic to default Topic: {topic.code}."
                )
            subdocument = SubDocumentDB(
                idsubdocument=1,  # This will be set by the database
                content=sub_doc.page_content,
                idbook=book.idbook,
                idlanguage=(
                    await self.get_language_id_by_locale(sub_doc.metadata["language"])
                ),
                idcompetence=competence.idcompetence,
                idtopic=topic.idtopic,
                createdat=datetime.datetime.now(),
                updatedat=datetime.datetime.now(),
                enabled=True,
            )
            sub_doc_id = await self.db.add_subdocument(subdocument)
            sub_doc_count += 1
            try:
                new_chunks = await self.split_into_subdocuments_by_tokens(
                    [sub_doc],
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    prepend_summary=False,
                    additional_metadata={
                        "sub_doc_uuid": sub_doc_id,
                        "idbook": subdocument.idbook,
                        "idlanguage": subdocument.idlanguage,
                        "idcompetence": subdocument.idcompetence,
                        "idtopic": subdocument.idtopic,
                    },
                    llms=self.llms,
                    llm_fallback=self.llms[-1] if self.llms else None,
                )
                logger.debug(
                    f":small_blue_diamond: Created [bold]{len(new_chunks)}[/bold] "
                    f"chunks from subdocument [bold]{sub_doc_id}[/bold]."
                )
                chunks.extend(new_chunks)
                progress.update(task_id, advance=1)
            except Exception as e:
                logger.error(
                    f":warning: Error processing subdocument [bold]{sub_doc_id}[/bold]:"
                    f" {e}"
                )
                continue

        progress.stop_task(task_id)
        logger.debug(
            ":white_check_mark: Completed ingesting using SubDocRetriever. Total "
            f"subdocuments: [bold]{sub_doc_count}[/bold] | Total chunks: "
            f"[bold]{len(chunks)}[/bold]"
        )
        return chunks

    async def rerank(
        self, query: str, retrieved_documents: list[Document]
    ) -> list[Document]:
        """Rerank retrieved documents using FlashrankRerank."""
        compressor = FlashrankRerank()

        reranked_docs = await compressor.acompress_documents(
            documents=retrieved_documents,
            query=query,
        )

        return reranked_docs

    async def retrieve(
        self,
        query: str,
        retrieve_count: int = 10,
        competence_id=None,
        topic_id=None,
        language_id=None,
    ) -> list[tuple[Document, float]]:
        """Retrieve documents from subdocument splits."""
        logger.debug(
            ":mag: Retrieving documents with [bold]Subdocument Split[/bold] for query:"
            f" [italic]'{query}'[/italic]"
        )

        results = []

        try:
            # use a fallback retriever when required
            if self.alt_retriever:
                retrieved = self.alt_retriever.similarity_search_with_relevance_scores(
                    query,
                    k=retrieve_count,
                    competence_id=competence_id,
                    topic_id=topic_id,
                    language_id=language_id,
                )
                if (
                    self.alt_retriever_timestamp
                    and (
                        datetime.datetime.now() - self.alt_retriever_timestamp
                    ).total_seconds()
                    > 3600  # 1 hour
                ):
                    self.alt_retriever = None # reset after 1 hour
                    self.alt_retriever_timestamp = None
            else:
                retrieved = self.vector_store.similarity_search_with_relevance_scores(
                    query,
                    k=retrieve_count,
                    competence_id=competence_id,
                    topic_id=topic_id,
                    language_id=language_id,
                )

        except Exception as e:
            logger.error(f":warning: Error during retrieval: {e}")

            # try with local embedding model
            alt_embedding = HFEmbedding()
            alt_retriever = PGVectorDB(alt_embedding, self.vector_store.db)
            self.alt_retriever = await alt_retriever.ainit()
            try:
                retrieved = self.alt_retriever.similarity_search_with_relevance_scores(
                    query,
                    k=retrieve_count,
                    competence_id=competence_id,
                    topic_id=topic_id,
                    language_id=language_id,
                )
            except Exception as e2:
                logger.error(f":warning: Alt retriever also failed: {e2}")
                return []

        sub_doc_list = {}

        for ret in retrieved:
            doc, score = ret
            subdoc_column = (
                "idsubdocument" if "idsubdocument" in doc.metadata else "sub_doc_uuid"
            )
            if subdoc_column in doc.metadata:
                subdocument = await self.db.get_subdocument(doc.metadata[subdoc_column])
                if not subdocument:
                    logger.warning(
                        ":warning: Subdocument with ID [bold]"
                        f"{doc.metadata[subdoc_column]}[/bold] not found in DB."
                    )
                    results.append((doc, score))
                    continue
                if doc.metadata[subdoc_column] not in sub_doc_list:
                    sub_doc_list[doc.metadata[subdoc_column]] = len(results)
                    doc.page_content = subdocument.content
                    doc.id = f"sd_{subdocument.idsubdocument}"
                    results.append((doc, score))
                else:
                    og_doc_index = sub_doc_list[doc.metadata[subdoc_column]]
                    if score > results[og_doc_index][1]:
                        results[og_doc_index] = (results[og_doc_index][0], score)
            else:
                results.append((doc, score))

        return results
