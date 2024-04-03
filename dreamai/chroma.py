import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import chromadb
from chromadb import Collection as ChromaCollection
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_core.documents import Document as LCDocument
from termcolor import colored

CHROMA_EMBEDDING_MODEL = "multi-qa-mpnet-base-cos-v1"
CHROMA_DIR = "chroma_dir"
CHROMA_DEVICE = "cuda"
CHROMA_DELETE_EXISTING = False


def chroma_collection(
    name: str,
    persistent_dir: str = CHROMA_DIR,
    delete_existing: bool = CHROMA_DELETE_EXISTING,
    embedding_model: str = CHROMA_EMBEDDING_MODEL,
    device: str = CHROMA_DEVICE,
) -> ChromaCollection:
    chroma_client = chromadb.PersistentClient(path=persistent_dir)
    if delete_existing:
        try:
            chroma_client.delete_collection(name)
        except Exception as e:
            print(colored(f"Error deleting collection named {name}: {e}", "red"))
            pass
    embedding_function = SentenceTransformerEmbeddingFunction(
        model_name=embedding_model, device=device
    )
    collection = chroma_client.get_or_create_collection(
        name, embedding_function=embedding_function
    )
    return collection


def json_files_to_collection(
    flist: list[str | Path], chroma_collection: ChromaCollection
):
    metas = []
    ids = [f"id_{uuid4()}" for _ in range(len(flist))]
    docs = []
    i = 0
    for fname in flist:
        with open(fname, "r") as f:
            data = json.load(f)
            data_str = json.dumps(data)
            meta = {"level": data["level"], "type": data["type"]}
            metas.append(meta)
            docs.append(data_str)
            i += 1
    print(f"Ddding {i} files to collection")
    chroma_collection.add(documents=docs, ids=ids, metadatas=metas)


def id_from_lc_doc(doc: LCDocument, doc_idx=None, **kwargs) -> str | None:
    """Get a unique id from an LCDocument."""

    try:
        file_name = doc.metadata.get("filename", doc.metadata["source"])
        doc_id = f"{file_name}_{doc.metadata.get('page_number', 0)}"
        if doc_idx is not None:
            doc_id += f"_{doc_idx}"
        return doc_id + f"_{uuid4()}"
    except Exception as e:
        print(colored(f"Error getting id from LCDocument: {e}", "red"))
        return None


def lc_docs_to_chroma_docs(
    docs: list[LCDocument], id_fn: Callable = id_from_lc_doc
) -> tuple[list[str], list[str], list[dict]]:
    """Convert a list of LCDocuments to Chroma docs with ids and metadata."""

    chroma_ids = []
    chroma_docs = []
    chroma_metadatas = []
    for i, doc in enumerate(docs):
        chroma_docs.append(doc.page_content)
        chroma_metadatas.append(
            {
                k: v
                for k, v in doc.metadata.items()
                if type(v) in [str, int, float, bool]
            }
        )
        chroma_ids.append(id_fn(doc=doc, doc_idx=i) or f"id_{i}")
    return chroma_ids, chroma_docs, chroma_metadatas
