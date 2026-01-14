# pragma: exclude file

import logging
import sys
from pathlib import Path

import tiktoken
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from framework.rag.retrievers.parallel_augmentation import (
    ParallelAugmentationManager,
    QuestionAugmentationResult,
    QuestionAugmentationTask,
    SummaryAugmentationResult,
    SummaryAugmentationTask,
)

logger = logging.getLogger(__name__)


class BaseRetriever:
    """Base class for retrievers."""

    async def ingest(self, document: Document):
        """Ingest the query using the associated embedding model."""
        raise NotImplementedError("Subclasses should implement this method.")

    async def retrieve(self, query: str):
        """Retrieves relevant documents based on the embedded query."""
        raise NotImplementedError("Subclasses should implement this method.")

    def split_by_characters(
        self,
        documents: list[Document], 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ):
        """Splits documents by usual characters such as newlines."""
        rec_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
        )
        texts = []
        metadatas = []
        for doc in documents:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata)

        return rec_text_splitter.create_documents(texts, metadatas)


    def split_by_semantics(
        self,
        documents: list[Document],
        embedding_func: Embeddings,
        min_chunk_size=None,  # in characters
    ):
        """Splits documents into semantic chunks using an embedding function.

        Careful: takes long time to run, especially with large documents.
        """
        text_splitter = SemanticChunker(embedding_func, min_chunk_size=min_chunk_size)
        texts = []
        metadatas = []
        for doc in documents:
            texts.append(doc.page_content)
            metadatas.append(doc.metadata)

        docs = text_splitter.create_documents(texts, metadatas)
        return docs


    async def split_into_subdocuments_by_tokens(
        self,
        documents: list[Document],
        chunk_size: int = 5000,
        chunk_overlap: int = 500,
        prepend_summary: bool = False,
        additional_metadata: dict = None,
        llms: list[BaseChatModel] = None,
        llm_fallback: BaseChatModel = None,
    ) -> list[Document]:
        """Splits documents based on token count and optionally generates summaries."""
        encoding = tiktoken.encoding_for_model(
            "gpt-4o-mini"
        )  # even though we use LLaMa, token lengths should be similar for all models

        def length_by_tokens(text: str) -> int:
            """Returns the number of tokens in the text."""
            return len(encoding.encode(text))

        rec_text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=length_by_tokens,
            is_separator_regex=False,
        )

        docs = []
        summary_tasks = []
        additional_metadata = additional_metadata or {}
        frags_needing_summary = []

        # First pass: split documents and put into list or queue of tasks
        for i, doc in enumerate(documents):
            doc.metadata["doc_index"] = i
            if length_by_tokens(doc.page_content) < (chunk_size + 2 * chunk_overlap):
                # If the document is smaller than the chunk size, return it as is
                docs.append(doc)
                continue

            if prepend_summary:
                task = SummaryAugmentationTask(
                    fragment=doc,
                    doc_index=i,
                    fragment_index=0,
                    original_doc=doc,
                    summary_length=None,
                )
                summary_tasks.append(task)
            text_frags = rec_text_splitter.split_text(doc.page_content)
            for j, frag_text in enumerate(text_frags):
                frag = Document(
                    page_content=frag_text,
                    metadata={
                        **doc.metadata,
                        # TODO maybe save subdoc text directly here?
                        "doc_index": i,
                        "fragment_index": j,
                        **additional_metadata,
                    },
                )
                if prepend_summary:
                    frags_needing_summary.append(frag)
                else:
                    docs.append(frag)

        if summary_tasks:
            logger.debug(f"Processing {len(summary_tasks)} summary tasks in parallel")

            manager = ParallelAugmentationManager(
                llms, 
                llm_fallback, 
                show_progress=False
            )
            results: list[SummaryAugmentationResult] = await manager.process_fragments(
                summary_tasks
            )

            # Process results and create question documents
            successful_results = [r for r in results if r.success]
            failed_results = [r for r in results if not r.success]

            logger.debug(
                f"Augmentation complete: {len(successful_results)} successful, "
                f"{len(failed_results)} failed"
            )

            if failed_results:
                logger.warning("Failed augmentation tasks:")
                for result in failed_results:
                    logger.warning(
                        f"  Doc {result.task.doc_index} Fragment "
                        f"{result.task.fragment_index}: {result.error}"
                    )

            for result in successful_results:
                if result.summary:
                    text_doc_id = result.task.fragment.metadata["doc_index"]
                    frags_with_doc_id = [
                        frag
                        for frag in frags_needing_summary
                        if frag.metadata["doc_index"] == text_doc_id
                    ]
                    for frag in frags_with_doc_id:
                        frag.page_content = f"{result.summary}\n\n{frag.page_content}"
                        docs.append(frag)

        return docs

    async def split_by_header(
        self,
        documents: list[Document],
        return_each_line=False,
        strip_headers=True,
        augmented: bool = False,
        questions_per_header: int = 5,
        llms: list[BaseChatModel] = None,
    ) -> list[Document]:
        """Splits the documents and optionally augments them using parallel processing.

        First, it splits the documents into fragments based on Markdown headers.
        If `augmented` is True, it generates questions for each header fragment using
        multiple LLMs in parallel, distributing the load across the available LLMs.
        """
        md_text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
                ("####", "Header 4"),
                ("#####", "Header 5"),
                ("######", "Header 6"),
            ],
            return_each_line=return_each_line,
            strip_headers=strip_headers,
        )

        chunks = []
        augmentation_tasks = []

        # First pass: split documents and create original chunks
        for i, text_doc in enumerate(documents):
            text_frags = md_text_splitter.split_text(text_doc.page_content)
            logger.info(
                f"Splitting document {i}: split into {len(text_frags)} fragments."
            )

            for j, frag in enumerate(text_frags):
                frag.metadata.update(
                    {
                        **text_doc.metadata,
                        "type": "ORIGINAL",
                        "text": text_doc.page_content,
                    }
                )
                chunks.append(frag)

                # Create augmentation task if needed
                if augmented:
                    task = QuestionAugmentationTask(
                        fragment=frag,
                        doc_index=i,
                        fragment_index=j,
                        questions_per_header=questions_per_header,
                        original_doc=text_doc,
                    )
                    augmentation_tasks.append(task)

        # Process augmentation tasks in parallel if any exist
        if augmentation_tasks:
            logger.info(
                f"Processing {len(augmentation_tasks)} question augmentation tasks in "
                "parallel"
            )

            augmented_chunks = await self.process_augmentation_tasks(
                augmentation_tasks, llms=llms, llm_fallback=llms[-1] if llms else None
            )
            chunks.extend(augmented_chunks)

            logger.info(f"Added {len(augmented_chunks)} question documents")

        return chunks

    async def process_augmentation_tasks(
        self,
        augmentation_tasks: list[QuestionAugmentationTask],
        llms: list[BaseChatModel] = None,
        llm_fallback: BaseChatModel = None,
    ) -> list[Document]:
        """Processes question augmentation tasks in parallel using multiple LLMs."""
        chunks = []

        manager = ParallelAugmentationManager(llms, llm_fallback)
        results: list[QuestionAugmentationResult] = await manager.process_fragments(
            augmentation_tasks
        )

        # Process results and create question documents
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]

        logger.info(
            f"Augmentation complete: {len(successful_results)} successful, "
            f"{len(failed_results)} failed"
        )

        if failed_results:
            logger.warning("Failed augmentation tasks:")
            for result in failed_results:
                logger.warning(
                    f"  Doc {result.task.doc_index} Fragment "
                    f"{result.task.fragment_index}: {result.error}"
                )

        # Create question documents from successful results
        # each document contains the original text to use as context
        for result in successful_results:
            for question in result.questions:
                question_doc = Document(
                    page_content=question,
                    metadata={
                        **result.task.fragment.metadata,
                        "type": "AUGMENTED",
                        "text": result.task.original_doc.page_content,
                    },
                )
                chunks.append(question_doc)

        return chunks
