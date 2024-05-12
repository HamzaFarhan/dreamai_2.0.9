from chromadb import Collection as ChromaCollection
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader  # type: ignore
from langchain_core.documents import Document as LCDocument

from .chroma import (
    CHROMA_DEVICE,
    CHROMA_DIR,
    CHROMA_EMBEDDING_MODEL,
    chroma_collection,
    lc_docs_to_chroma_docs,
)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
SEPARATORS = ["\n\n", "\n"]
CHROMA_COLLECTION_NAME = "pdf_collection"
CHROMA_DELETE_EXISTING = False


def pdf_to_docs(
    pdf_file: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list = SEPARATORS,
) -> list[LCDocument]:
    loader = PyPDFLoader(file_path=pdf_file)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        keep_separator=False,
    )
    docs = loader.load_and_split(splitter)
    return docs


def pdf_to_collection(
    pdf_file: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
    collection_name: str = CHROMA_COLLECTION_NAME,
    persistent_dir: str = CHROMA_DIR,
    delete_existing: bool = CHROMA_DELETE_EXISTING,
    embedding_model: str = CHROMA_EMBEDDING_MODEL,
    device: str = CHROMA_DEVICE,
    add_links: bool = True,
) -> ChromaCollection:
    pdf_docs = pdf_to_docs(
        pdf_file=pdf_file,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
    )
    collection = chroma_collection(
        name=collection_name,
        persistent_dir=persistent_dir,
        delete_existing=delete_existing,
        embedding_model=embedding_model,
        device=device,
    )
    collection.add(**lc_docs_to_chroma_docs(pdf_docs, add_links=add_links))
    return collection
