import asyncio
import json
import logging
import pprint as pp
import sys
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

sys.path.append(str(Path(__file__).parent.parent))
from framework.api_types.locale_type import LocaleType
from framework.db.database import Database
from framework.llm.lite_llm import LiteLLM
from framework.llm.scads_llm import ScadsLLM
from framework.rag.embeddings.lite_llm_embedding import LiteLLMEmbedding
from framework.rag.retrievers.simple_retriever import SimpleRetriever
from framework.rag.retrievers.sub_doc_retriever import SubDocRetriever
from framework.rag.vector_dbs.pgvector import PGVectorDB

topics = set()
DATA_PATH = Path(Path(__file__).parent.parent.parent / "data").resolve()
DB_FAISS_PATH = Path(
    Path(__file__).parent.parent.parent / "vectorstore/db_faiss"
).resolve()

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(console=console, rich_tracebacks=True, show_path=False, markup=True)
    ],
)
logger = logging.getLogger(__name__)


def get_modules() -> dict:
    """Retrieves the modules from the data folders."""
    modules = {}
    for root, dirs, files in DATA_PATH.walk():
        # only go into folders with subfolders, i.e. don't go into the submodules
        for name in dirs:
            parent_dir = root.name
            if name in LocaleType:  # is a language folder
                modules[parent_dir][name] = []
            # topic folder
            elif parent_dir not in topics and parent_dir not in LocaleType:
                topics.add(name)
                modules[name] = {}
            else:  # is a module folder
                modules[root.parent.name][parent_dir].append(name)
    logger.debug("Modules: " + pp.pformat(modules))
    return modules


def get_db_paths(modules: dict):
    """Determines where to save the Faiss DBs dependent on the modules' names."""
    paths = []
    for topic in modules.keys():
        for locale in modules[topic]:
            for module in modules[topic][locale]:
                paths.append(
                    DB_FAISS_PATH
                    / topic.replace(" ", "").lower()
                    / locale
                    / module.replace(" ", "").lower()
                )
    return paths


def get_data_paths(modules: dict):
    """Finds datapaths dependent on OS."""
    paths = []
    for topic in modules.keys():
        for locale in modules[topic]:
            for module in modules[topic][locale]:
                paths.append(DATA_PATH / topic / locale / module)
    return paths


def set_doc_metadata(doc: Document):
    """Sets the metadata for a document based on its relative path."""
    rel_path = Path(doc.metadata["source"]).relative_to(DATA_PATH)  # Get relative path
    language = rel_path.parts[1]
    topic = rel_path.parts[0]
    competence = rel_path.parts[2] if len(rel_path.parts) > 2 else None
    if language.lower() not in LocaleType:
        language = [part for part in rel_path.parts if part.lower() in LocaleType][
            0
        ] or "en"
    doc.metadata["language"] = language
    book_code = None
    if topic == "study_competence":
        book_code = rel_path.stem  # Last part of path without file extension
    elif topic == "scientific_writing":
        book_code = "Scientific_Writing"
        competence = f"sw_{competence}"
    elif topic == "st":
        if competence == "st_organizational":
            book_code = "ST_Organizational"
        elif competence == "st_content":
            if "swebok" in rel_path.stem:
                book_code = "SweBok"
            elif "swt4einst" in rel_path.stem:
                book_code = "Swt4Einst"
            else:
                book_code = "OPAL"
        elif competence == "st_exercises":
            if len(rel_path.parts) > 3:
                if rel_path.parts[3] == "artemis_bonuspoints_tasks":
                    book_code = "ArtemisBonus"
                elif rel_path.parts[3] == "artemis_normal_tasks":
                    book_code = "ArtemisExercises"
                else:
                    book_code = "ST_Exercises"
            else:
                book_code = "ST_Exercises"
    elif topic == "grumci":
        if competence == "grumci_organizational":
            book_code = "Grumci_Organizational"
        elif competence == "grumci_content":
            if len(rel_path.parts) > 3:
                if rel_path.parts[3] == "website_dart":
                    book_code = "Website_Dart"
                else:
                    book_code = "Grumci_Content"
            else:
                book_code = "Grumci_Content"
    elif topic == "maschbau":
        competence = f"mb_{competence}"
        book_code = "Maschbau"
    elif topic == "btsllm":
        if competence == "btsllm_content":
            if rel_path.parts[3] == "speech_and_language_processing":
                book_code = "Speech_and_Language_Processing"
            elif rel_path.parts[3] == "deep_learning_for_NLP":
                book_code = "Deep_Learning_for_NLP"
            else:
                book_code = "tokenius_Content"
        elif competence == "btsllm_exercises":
            book_code = "tokenius_Exercises"
        elif competence == "btsllm_organizational":
            book_code = "tokenius_Organizational"
        elif competence == "btsllm_project":
           book_code = "tokenius_Project"
    elif topic == 'ds':
        if competence == 'ds_exercises':
            book_code = 'ds_exercises'
        elif competence == 'ds_content':
            book_code = 'ds_content'
        elif competence == 'ds_organizational':
            book_code = 'ds_organizational'
    doc.metadata["topic"] = topic
    doc.metadata["competence"] = competence
    doc.metadata["book_code"] = book_code
    return doc


def get_default_llms() -> tuple[list[BaseChatModel], BaseChatModel]:
    """Initializes and returns a list of LLMs for parallel augmentation."""
    # Initialize multiple LLMs for used to distribute the load of parallel augmentation
    scads = ScadsLLM(model_name="meta-llama/Llama-3.3-70B-Instruct").llm(temperature=0)
    kisski = LiteLLM(model_name="llama-3.1-8b").llm_chatopenai(temperature=0)
    llm_fallback = LiteLLM(model_name="llama-3.3").llm_chatopenai(temperature=0)

    llms = [scads, kisski]
    return (llms, llm_fallback)


def create_local_vector_db(
    embeddings: Embeddings,
    docs: list[Document],
    faiss_path: str,
):
    """Embeds the documents and creates a Faiss DB for a module."""
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(faiss_path)


async def ingest():
    """Template Method for the ingestion of documents into Faiss DBs."""
    logger.info(":rocket: Starting ingestion process...")
    modules = get_modules()
    data_paths = get_data_paths(modules)

    logger.info(":brain: Loading embeddings...")
    embeddings = LiteLLMEmbedding()
    logger.info(":file_cabinet: Loading database and vector store...")
    db = Database()
    await db.connect()
    await db.register_vector()
    vector_store = PGVectorDB(
        embeddings=embeddings, db=db, table_name="chunk", vector_size=2560
    )
    (llm, llm_fallback) = get_default_llms()
    llm.extend([llm_fallback])  # Add fallback LLM to the list
    sub_doc_retriever = SubDocRetriever(db, embeddings, vector_store, llms=llm)
    header_retriever = SimpleRetriever(db, embeddings, vector_store)

    # Calculate total files to process for progress tracking
    total_files = 0
    processed_files = 0
    files_by_path = {}

    logger.info(":mag: Scanning directories to count total files...")
    for path in data_paths:
        md_files = list(path.glob("**/*.md"))
        files_count = len(md_files)
        files_by_path[path] = md_files
        total_files += files_count
        logger.info(
            f"Found {files_count} markdown files in {Path(path).relative_to(DATA_PATH)}"
        )

    logger.info(f":file_folder: Total files to process: {total_files}")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task_id = progress.add_task(
            description="Ingesting documents",
            total=total_files,
        )

        for i, path in enumerate(data_paths):
            logger.info(
                f":open_file_folder: Processing directory "
                f"[{i + 1}/{len(data_paths)}]: {Path(path).relative_to(DATA_PATH)}"
            )

            text_loader_kwargs = {"encoding": "utf-8", "autodetect_encoding": True}
            loader = DirectoryLoader(
                path,
                glob="**/*.md",
                loader_cls=TextLoader,
                loader_kwargs=text_loader_kwargs,
            )

            # Extract only the relevant part of the path (relative to DATA_PATH)
            relative_path = path.relative_to(DATA_PATH)
            documents = loader.load()
            if len(documents) == 0:
                continue
            documents = [set_doc_metadata(doc) for doc in documents]

            # Files processed in this directory
            dir_files_count = len(files_by_path[path])
            processed_files += dir_files_count

            chunks = []

            topic = documents[0].metadata.get("topic", "unknown")
            if topic == "study_competence":
                logger.info(
                    ":page_facing_up: Splitting into sub-documents and chunks for "
                    f"{relative_path}"
                )
                chunks = await sub_doc_retriever.ingest(documents, progress=progress)
            else:
                logger.info(
                    ":page_facing_up: Splitting by markdown headers for "
                    f"{relative_path}"
                )
                chunks = await header_retriever.ingest(documents)

            debug = False
            if debug:
                # save to file to debug
                log_file_path = Path(f"./logs/splits_{relative_path}.json")
                log_file_path.parent.mkdir(parents=True, exist_ok=True)

                serializable_splits = [
                    {
                        "page_content": split.page_content,
                        "metadata": split.metadata,
                    }
                    for split in chunks
                ]

                with log_file_path.open("w", encoding="utf-8") as f:  # noqa: ASYNC230
                    json.dump({"splits": serializable_splits}, f)
            else:
                logger.info(
                    ":brain: :arrow_right: :floppy_disk: Embedding and saving generated"
                    " chunks to vector DB..."
                )
                await db.add_documents(
                    embeddings.get_embeddings(),
                    chunks,
                )
            progress.update(task_id, advance=dir_files_count)

        progress.stop()
        logger.info(
            f"Ingestion complete :tada: Processed {processed_files}/{total_files} "
            f"({(total_files / processed_files) * 100:.1f}%) files."
        )


if __name__ == "__main__":
    import asyncio
    import platform

    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(ingest())
