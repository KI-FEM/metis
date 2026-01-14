from pathlib import Path

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter


def create_header_splits(documents):
    """Splits the Markdown documents into headers and creates a list of the headers."""
    headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]

    md_text_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )  # , strip_headers = False
    md_header_splits = []
    for doc in documents:
        new_md_splits = md_text_splitter.split_text(doc.page_content)
        for split in new_md_splits:
            split.metadata.update(doc.metadata)
        md_header_splits.extend(new_md_splits)
    return md_header_splits


text_loader_kwargs = {"autodetect_encoding": True}
path = Path(__file__).parent
loader = DirectoryLoader(
    path,
    glob="**/*.md",
    loader_cls=TextLoader,
    loader_kwargs=text_loader_kwargs,
)

documents = loader.load()

md_header_splits = create_header_splits(documents)

embeddings = HuggingFaceEmbeddings(
    model_kwargs={"device": "cpu"},
    cache_folder=str(Path(Path(__file__).parent.parent.parent.parent / "cache")
                     .resolve()),
)

db = FAISS.from_documents(md_header_splits, embeddings)
db.save_local(path / "test_db")
