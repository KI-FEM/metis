# pragma: exclude file
import os


os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
# Force CPU usage
os.environ["CUDA_VISIBLE_DEVICES"] = ""

import logging
import sys
from pathlib import Path
from uuid import uuid4

from sentence_transformers import (
    SentenceTransformer,
)  # dont remove, else segmentation fault occurs when importing faiss
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel
import faiss  # has to be imported after any sentence_transformers to avoid segmentation fault
from rich.logging import RichHandler
from rich.console import Console

sys.path.append(str(Path(__file__).parent.parent.parent))
from framework.llm.google_llm import GoogleLLM
from framework.llm.lite_llm import LiteLLM
from framework.llm.ollama_llm import OllamaLLM
from framework.rag.retrievers.base_retriever import BaseRetriever
from framework.rag.retrievers.parallel_augmentation import QuestionAugmentationTask
from module_loading.ingester import (
    get_data_paths,
    get_modules,
)
from framework.rag.embeddings.lite_llm_embedding import LiteLLMEmbedding

console = Console()

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True, show_path=False, markup=True)
    ],
)
logger = logging.getLogger(__name__)

DATA_PATH = Path(Path(__file__).parent.parent.parent / "data").resolve()
DB_FAISS_PATH = Path(
    Path(__file__).parent.parent.parent / "vectorstore/db_faiss"
).resolve()
SUBDOC_DB_FILE_AUGMENTED = Path(
    Path(__file__).parent.parent.parent / "data/subdoc_db_augmented.json"
).resolve()
SUBDOC_DB_FILE = Path(
    Path(__file__).parent.parent.parent / "data/subdoc_db.json"
).resolve()
SUBDOC_DB_FILE_SUBDOCS_ONLY = Path(
    Path(__file__).parent.parent.parent / "data/subdoc_db_subdocs_only.json"
).resolve()


class SubDoc(BaseModel):
    id: str
    page_content: str
    metadata: dict | None = None


class SubDocDB(BaseModel):
    subdocuments: dict[str, SubDoc]


subdoc_db = SubDocDB(subdocuments={})
vector_store = None
embeddings = None
retriever = BaseRetriever()


def append_subdocuments(doc: Document) -> SubDocDB:
    """Append given subdocuments to the DB."""
    import uuid

    uid = str(uuid.uuid4())
    subdoc_db.subdocuments[uid] = SubDoc(
        id=uid, page_content=doc.page_content, metadata=doc.metadata
    )
    return uid


def save_subdocuments(subdocuments: SubDocDB, db_file: Path) -> None:
    """Save subdocuments to a JSON file."""
    import json

    with Path.open(db_file, "w", encoding="utf-8") as f:
        json.dump(subdocuments.model_dump(), f, indent=4)


def read_subdocuments(db_file: Path) -> SubDocDB:
    """Read subdocuments from a JSON file."""
    import json

    if not db_file.exists():
        logger.warning(
            f":warning: Subdocument database file [bold]{db_file}[/bold] does not exist. Creating a new empty database."
        )
        subdoc_db = SubDocDB(subdocuments={})
        return subdoc_db
    with Path.open(db_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    subdoc_db = SubDocDB(**data)
    return subdoc_db


def create_vector_db():
    global vector_store

    embed = embeddings.embed_query("hello world")
    index = faiss.IndexFlatL2(len(embed))  # Create a flat index for L2 distance

    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    logger.debug(":sparkles: Vector store created with FAISS index.")


def load_vector_db(path: Path) -> FAISS:
    """Load the vector database from the given path."""
    global vector_store

    if not path.exists():
        create_vector_db()
    else:
        vector_store = FAISS.load_local(str(path), embeddings)
    logger.debug(f":inbox_tray: Vector store loaded from [bold]{path}[/bold]")
    return vector_store


def add_documents_to_vector_db(documents: list[Document]) -> list[str]:
    global vector_store
    if vector_store is None:
        logger.error(
            ":warning: Vector store is not initialized. Please load the vector store first."
        )
        return []

    uuids = [str(uuid4()) for _ in range(len(documents))]
    return vector_store.add_documents(documents=documents, ids=uuids)


def delete_documents_from_vector_db(document_ids: list[str]) -> bool:
    global vector_store
    if vector_store is None:
        logger.error(
            ":warning: Vector store is not initialized. Please load the vector store first."
        )
        return False

    logger.debug(f":wastebasket: Deleting documents with IDs: {document_ids}")
    return vector_store.delete(ids=document_ids)


def save_vector_db(path: Path) -> None:
    """Save the vector database to the given path."""
    global vector_store
    if vector_store is None:
        logger.error(
            ":warning: Vector store is not initialized. Please load the vector store first."
        )
        return

    logger.debug(f":floppy_disk: Saving vector store to [bold]{path}[/bold]")
    vector_store.save_local(str(path))


async def ingest_subdocs(llms, llm_fallback):
    """Split the file into larger subdocuments and split those into smaller chunks which are then stored in the vector db."""
    global subdoc_db, embeddings, vector_store
    if vector_store is not None:
        vector_store = None

    create_vector_db()
    modules = get_modules()
    data_paths = get_data_paths(modules)

    subdoc_db = read_subdocuments(SUBDOC_DB_FILE)
    chunks_len = 0

    logger.info(":arrow_down: Ingesting using subdocuments...")
    for i, path in enumerate(data_paths):
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()
        chunks = []

        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents from [bold]{path}[/bold]..."
        )

        # split into big subdocuments
        subdocuments = await retriever.split_into_subdocuments_by_tokens(
            documents, chunk_size=5000, chunk_overlap=500, prepend_summary=False
        )

        logger.info(
            f":scissors: Created [bold]{len(subdocuments)}[/bold] subdocuments from [bold]{len(documents)}[/bold] documents."
        )

        # create chunks for subdocuments
        for sub_doc in subdocuments:
            sub_doc_uuid = append_subdocuments(sub_doc)
            try:
                new_chunks = await retriever.split_into_subdocuments_by_tokens(
                    [sub_doc],
                    chunk_size=500,
                    chunk_overlap=100,
                    prepend_summary=True,
                    additional_metadata={"sub_doc_uuid": sub_doc_uuid},
                    llms=llms,
                    llm_fallback=llm_fallback,
                )
                logger.debug(
                    f":small_blue_diamond: Created [bold]{len(new_chunks)}[/bold] chunks from subdocument [bold]{sub_doc_uuid}[/bold]."
                )
                chunks.extend(new_chunks)
            except Exception as e:
                logger.error(
                    f":warning: Error processing subdocument [bold]{sub_doc_uuid}[/bold]: {e}"
                )
                continue

        logger.info(
            f":brain: Embedding and saving [bold]{len(chunks)}[/bold] chunks to VectorDB"
        )
        add_documents_to_vector_db(chunks)
        chunks_len += len(chunks)

    save_subdocuments(subdoc_db, SUBDOC_DB_FILE)
    logger.info(f":floppy_disk: Subdocuments saved to [bold]{SUBDOC_DB_FILE}[/bold]")
    save_vector_db(DB_FAISS_PATH / "subdocs")
    logger.info(
        f":white_check_mark: Completed ingesting using subdocuments. Total subdocuments: [bold]{len(subdoc_db.subdocuments)}[/bold] | Total chunks: [bold]{chunks_len}[/bold]"
    )


async def ingest_subdocs_with_questions(llms, llm_fallback, questions_per_header=20):
    """Split the file into larger subdocuments and split those into smaller chunks and additional questions which are then stored in the vector db."""
    global subdoc_db, embeddings, vector_store
    if vector_store is not None:
        vector_store = None

    create_vector_db()
    modules = get_modules()
    data_paths = get_data_paths(modules)

    subdoc_db = read_subdocuments(SUBDOC_DB_FILE_AUGMENTED)
    chunks_len = 0

    logger.info(":arrow_down: Ingesting using subdocuments with questions...")
    for i, path in enumerate(data_paths):
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()
        chunks = []
        augmentation_tasks = []

        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents from [bold]{path}[/bold]..."
        )

        # split into big subdocuments
        subdocuments = await retriever.split_into_subdocuments_by_tokens(
            documents, chunk_size=5000, chunk_overlap=500, prepend_summary=False
        )

        logger.info(
            f":scissors: Created [bold]{len(subdocuments)}[/bold] subdocuments from [bold]{len(documents)}[/bold] documents."
        )

        # create chunks for subdocuments
        for i, sub_doc in enumerate(subdocuments):
            sub_doc_uuid = append_subdocuments(sub_doc)
            try:
                new_chunks = await retriever.split_into_subdocuments_by_tokens(
                    [sub_doc],
                    chunk_size=500,
                    chunk_overlap=100,
                    prepend_summary=True,
                    additional_metadata={"sub_doc_uuid": sub_doc_uuid},
                    llms=llms,
                    llm_fallback=llm_fallback,
                )
                logger.debug(
                    f":small_blue_diamond: Created [bold]{len(new_chunks)}[/bold] chunks from subdocument [bold]{sub_doc_uuid}[/bold]."
                )
                chunks.extend(new_chunks)

                # Also create questions for every chunk
                for j, chunk in enumerate(new_chunks):
                    task = QuestionAugmentationTask(
                        fragment=chunk,
                        doc_index=i,
                        fragment_index=j,
                        questions_per_header=questions_per_header,
                        original_doc=sub_doc,
                    )
                    augmentation_tasks.append(task)
            except Exception as e:
                logger.error(
                    f":warning: Error processing subdocument [bold]{sub_doc_uuid}[/bold]: {e}"
                )
                continue

        # Process augmentation tasks in parallel
        if augmentation_tasks:
            augmented_chunks = await retriever.process_augmentation_tasks(
                augmentation_tasks, llms=llms, llm_fallback=llm_fallback
            )
            chunks.extend(augmented_chunks)

        logger.info(
            f":brain: Embedding and saving [bold]{len(chunks)}[/bold] chunks to VectorDB"
        )
        add_documents_to_vector_db(chunks)
        chunks_len += len(chunks)

    save_subdocuments(subdoc_db, SUBDOC_DB_FILE_AUGMENTED)
    logger.info(
        f":floppy_disk: Subdocuments saved to [bold]{SUBDOC_DB_FILE_AUGMENTED}[/bold]"
    )
    save_vector_db(DB_FAISS_PATH / "subdocs_augmented")
    logger.info(
        f":white_check_mark: Completed ingesting using subdocuments augmented. Total subdocuments: [bold]{len(subdoc_db.subdocuments)}[/bold] | Total chunks: [bold]{chunks_len}[/bold]"
    )


async def ingest_subdocs_only():
    """Split the file into larger subdocuments and split those into smaller chunks which are then stored in the vector db."""
    global subdoc_db, embeddings, vector_store
    if vector_store is not None:
        vector_store = None

    create_vector_db()
    modules = get_modules()
    data_paths = get_data_paths(modules)

    subdoc_db = read_subdocuments(SUBDOC_DB_FILE_SUBDOCS_ONLY)
    subdocs_len = 0

    logger.info(":arrow_down: Ingesting subdocuments only...")
    for i, path in enumerate(data_paths):
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()

        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents from [bold]{path}[/bold]..."
        )

        # split into big subdocuments
        subdocuments = await retriever.split_into_subdocuments_by_tokens(
            documents, chunk_size=5000, chunk_overlap=500, prepend_summary=False
        )

        logger.info(
            f":scissors: Created [bold]{len(subdocuments)}[/bold] subdocuments from [bold]{len(documents)}[/bold] documents."
        )

        logger.info(
            f":brain: Embedding and saving [bold]{len(subdocuments)}[/bold] subdocuments to VectorDB"
        )
        add_documents_to_vector_db(subdocuments)
        subdocs_len += len(subdocuments)

    save_subdocuments(subdoc_db, SUBDOC_DB_FILE_SUBDOCS_ONLY)
    save_vector_db(DB_FAISS_PATH / "subdocs_only")
    logger.info(
        f":white_check_mark: Completed ingesting subdocuments only. Total subdocuments: [bold]{subdocs_len}[/bold]"
    )


async def ingest_questions(llms, llm_fallback):
    """Ingest documents but also questions towards the documents."""
    global embeddings, vector_store
    if vector_store is not None:
        vector_store = None

    create_vector_db()

    modules = get_modules()
    data_paths = get_data_paths(modules)

    chunks_len = 0
    logger.info(":arrow_down: Ingesting with additional questions...")
    for i, path in enumerate(data_paths):
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()

        logger.info(
            f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents from [bold]{path}[/bold]..."
        )
        try:
            chunks = await retriever.split_by_header(
                documents,
                augmented=True,
                questions_per_header=20,
                llms=llms,
                llm_fallback=llm_fallback,
            )

            logger.info(
                f":brain: Embedding and saving [bold]{len(chunks)}[/bold] chunks to VectorDB"
            )
            add_documents_to_vector_db(chunks)
            chunks_len += len(chunks)
        except Exception as e:
            logger.error(
                f":warning: Error processing documents from [bold]{path}[/bold]: {e}"
            )
            continue

    save_vector_db(DB_FAISS_PATH / "questions")
    logger.info(
        f":white_check_mark: Completed ingesting using additional questions. Total chunks: [bold]{chunks_len}[/bold]"
    )


def ingest_semantic_split():
    """Ingest the documents using a semantic splitter."""
    global embeddings, vector_store
    if vector_store is not None:
        vector_store = None

    create_vector_db()

    modules = get_modules()
    data_paths = get_data_paths(modules)

    chunks_len = 0
    logger.info(":arrow_down: Ingesting using semantic split...")
    for i, path in enumerate(data_paths):
        text_loader_kwargs = {"autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )
        documents = loader.load()

        try:
            logger.info(
                f":page_facing_up: Processing [bold]{len(documents)}[/bold] documents from [bold]{path}[/bold]..."
            )
            chunks = retriever.split_by_semantics(
                documents=documents,
                embedding_func=embeddings,
                min_chunk_size=None,  # in characters, set to None for default behavior
            )

            logger.info(
                f":brain: Embedding and saving [bold]{len(chunks)}[/bold] chunks to VectorDB"
            )
            add_documents_to_vector_db(chunks)
            chunks_len += len(chunks)
        except Exception as e:
            logger.error(
                f":warning: Error processing documents from [bold]{path}[/bold]: {e}"
            )
            continue

    save_vector_db(DB_FAISS_PATH / "semantic_split")
    logger.info(
        f":white_check_mark: Completed ingesting using semantic split. Total chunks: [bold]{chunks_len}[/bold]"
    )


async def ingest():
    """Ingest the subdocuments into the vector database."""
    global embeddings
    embeddings = HuggingFaceEmbeddings(  # new model (has 1024 dimensions)
        model_name="intfloat/multilingual-e5-large-instruct",
        model_kwargs={"device": "cpu"},
    )
    # scads = ScadsLLM(model_name="meta-llama/Llama-3.3-70B-Instruct").llm(temperature=0)
    # scads2 = ScadsLLM(model_name="meta-llama/Llama-3.3-70B-Instruct").llm(temperature=0)
    llama3 = LiteLLM(model_name="llama-3.3").llm_chatopenai(temperature=0)
    kisski = LiteLLM(model_name="llama-3.1-8b").llm_chatopenai(temperature=0)
    google = GoogleLLM(model_name="gemini-2.5-flash").llm(temperature=0)
    gemma = GoogleLLM(model_name="gemma-3-27b-it").llm(
        temperature=0
    )  # seems to not support structured output
    ollama = OllamaLLM(model_name="gemma3n:latest").llm(temperature=0)
    llm_fallback = ollama

    llms = [llama3, kisski, google, ollama]

    # await ingest_subdocs(llms, llm_fallback)
    # await ingest_questions(llms, llm_fallback)
    # ingest_semantic_split()
    await ingest_subdocs_only()
    # await ingest_subdocs_with_questions(llms, llm_fallback, questions_per_header=10)
    logger.info(":white_check_mark: Completed all ingestion processes.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(ingest())