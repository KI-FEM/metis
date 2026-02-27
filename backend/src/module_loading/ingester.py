import logging
import pprint as pp
from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

from framework.api_types.locale_type import LocaleType

topics = set()
DATA_PATH = Path(Path(__file__).parent.parent.parent / "data").resolve()
DB_FAISS_PATH = Path(
    Path(__file__).parent.parent.parent / "vectorstore/db_faiss"
).resolve()

logger = logging.getLogger(__name__)


def set_config_variables() -> dict:
    """Sets the config variables for the ingest process via the directories present."""
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
    logger.warning("Modules: " + pp.pformat(modules))
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


def create_header_splits(documents, return_each_line=False, st_exercises=False):
    """Splits the Markdown documents into headers and creates a list of the headers."""
    md_text_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
            ("#####", "Header 5"),
            ("######", "Header 6"),
        ],
        return_each_line=return_each_line,
    )
    md_header_splits = []
    for doc in documents:
        new_md_splits = md_text_splitter.split_text(doc.page_content)
        for split in new_md_splits:
            if st_exercises:
                split.metadata.update({**doc.metadata, "text": doc.page_content})
            else:
                split.metadata.update(doc.metadata)
        md_header_splits.extend(new_md_splits)
    return md_header_splits


def create_vector_db(embeddings, md_header_splits, path):
    """Embeds the headers and creates a Faiss DB for a module."""
    db = FAISS.from_documents(md_header_splits, embeddings)
    db.save_local(path)


def create_legacy_vector_db(embeddings, old_header_splits):
    """Embeds the headers and creates a Faiss DB for all modules."""
    db = FAISS.from_documents(old_header_splits, embeddings)
    logger.info(f"Saving legacy vector database at {DB_FAISS_PATH / 'all'}")
    db.save_local(DB_FAISS_PATH / "all")


def ingest():
    """Template Method for the ingestion of documents into Faiss DBs."""
    """logging.basicConfig(level=logging.INFO, filename=f"../logs/ingest.log")
    logging.info(f"CurrentDate: {datetime.datetime.now()}")
    logging.info(f"Data Path: {DATA_PATH}")
    logging.info(f"DB Faiss Path: {DB_FAISS_PATH}")"""

    modules = set_config_variables()

    old_header_splits = []
    db_paths = get_db_paths(modules)
    data_paths = get_data_paths(modules)
    
    # Calculate total files to process for progress tracking
    total_files = 0
    files_by_path = {}
    
    logger.info("Scanning directories to count total files...")
    for path in data_paths:
        md_files = list(path.glob("**/*.md"))
        files_count = len(md_files)
        files_by_path[path] = md_files
        total_files += files_count
        logger.info(f"Found {files_count} markdown files in {path}")
    
    logger.info(f"Total files to process: {total_files}")
    
    processed_files = 0
    
    for i, path in enumerate(data_paths):
        logger.info(f"Processing directory [{i+1}/{len(data_paths)}]: {path}")
        
        text_loader_kwargs = {"encoding": "utf-8", "autodetect_encoding": True}
        loader = DirectoryLoader(
            path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs=text_loader_kwargs,
        )

        # Get number of files in this directory
        current_dir_files = len(files_by_path[path])
        # Extract only the relevant part of the path (relative to DATA_PATH)
        relative_path = path.relative_to(DATA_PATH)
        logger.info(
            f"Loading documents from {relative_path} "
            f"({current_dir_files} files)"
        )
        documents = loader.load()
        
        # Log files processed in this directory
        dir_files_count = len(files_by_path[path])
        processed_files += dir_files_count
        
        # Update progress bar after processing this directory
        progress_percent = (processed_files / total_files) * 100
        bar_length = 30
        filled_length = int(bar_length * processed_files // total_files)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        logger.warning(
            f"[{bar}] {progress_percent:.1f}% | Processed: {relative_path} "
            f"({dir_files_count}/{total_files} files)"
        )
        
        md_header_splits = None
        if "StudyCompetence" in str(path):
            logger.info(f"Creating header splits for {path}")
            md_header_splits = create_header_splits(documents, return_each_line=False)
        elif "exercises" in str(path):
            logger.info("Creating header splits for the ST exercises")
            md_header_splits = create_header_splits(documents, st_exercises=True)
        else:
            logger.info(f"Creating standard header splits for {path}")
            md_header_splits = create_header_splits(documents)
        old_header_splits.extend(md_header_splits)

        logger.debug(
            "Documents split into headers: \n" + pp.pformat(md_header_splits) + "\n\n\n"
        )

        logger.info(f"Creating embeddings for {path}")
        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
        )

        logger.info(f"Creating vector database at {db_paths[i]}")
        create_vector_db(embeddings, md_header_splits, db_paths[i])

    logger.info("Creating legacy vector database for all modules")
    create_legacy_vector_db(embeddings, old_header_splits)
    logger.info("Ingestion complete (100%)")


if __name__ == "__main__":
    ingest()
