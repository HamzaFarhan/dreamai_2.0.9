import json
from pathlib import Path
from typing import Callable
from uuid import uuid4

import chromadb
import torch
from chromadb import Collection as ChromaCollection
from chromadb.api.types import Include, QueryResult, GetResult
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from langchain_core.documents import Document as LCDocument
from sentence_transformers import CrossEncoder
from termcolor import colored

CHROMA_EMBEDDING_MODEL = "multi-qa-mpnet-base-cos-v1"
CHROMA_DIR = "chroma_dir"
CHROMA_DEVICE = "cuda"
CHROMA_DELETE_EXISTING = False
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


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
        name,
        embedding_function=embedding_function,  # type: ignore
    )
    return collection


def json_files_to_collection(
    flist: list[str | Path], chroma_collection: ChromaCollection
):
    ids = []
    docs = []
    metas = []
    for i, fname in enumerate(flist):
        with open(fname, "r") as f:
            data = json.load(f)
            ids.append(f"id_{uuid4()}")
            metas.append(
                {
                    "level": data["level"],
                    "type": data["type"],
                    "prev_id": "",
                    "next_id": "",
                }
            )
            docs.append(json.dumps(data))
    # print(colored(f"Adding {i} files to collection", "cyan"))
    chroma_collection.add(ids=ids, documents=docs, metadatas=metas)


def id_from_lc_doc(doc: LCDocument, doc_idx=None, **kwargs) -> str | None:
    try:
        file_name = doc.metadata.get("filename", doc.metadata.get("source"))
        doc_id = file_name or ""
        page_number = doc.metadata.get("page_number")
        if page_number is not None:
            doc_id += f"_page_{page_number}"
        if doc_idx is not None:
            doc_id += f"_{doc_idx}"
        return doc_id + f"_{uuid4()}"
    except Exception as e:
        print(colored(f"Error getting id from LCDocument: {e}", "red"))
        return None


def lc_docs_to_chroma_docs(
    docs: list[LCDocument],
    id_fn: Callable = id_from_lc_doc,
    add_links: bool = True,
) -> dict:
    chroma_ids = []
    chroma_docs = []
    chroma_metadatas = []
    for i, doc in enumerate(docs):
        chroma_ids.append(id_fn(doc=doc, doc_idx=i) or f"id_{i}")
        chroma_docs.append(doc.page_content)
    for i, doc in enumerate(docs):
        metadata = {
            k: v for k, v in doc.metadata.items() if type(v) in [str, int, float, bool]
        }
        metadata["prev_id"] = ""
        metadata["next_id"] = ""
        if add_links:
            metadata["prev_id"] = chroma_ids[i - 1] if i > 0 else ""
            metadata["next_id"] = chroma_ids[i + 1] if i < len(docs) - 1 else ""
        chroma_metadatas.append(metadata)
    return {"ids": chroma_ids, "documents": chroma_docs, "metadatas": chroma_metadatas}


def traverse_id(
    id: str,
    collection: ChromaCollection,
    direction: str = "prev",
    n_steps: int = 2,
) -> list:
    ids = []
    for _ in range(n_steps):
        metadata = collection.get(ids=[id])["metadatas"][0]  # type: ignore
        id = metadata.get(f"{direction}_id", "")  # type: ignore
        if not id:
            break
        ids.append(id)
    return ids


def traverse_ids(
    ids: str | list[str],
    collection: ChromaCollection,
    n_prev_links: int = 2,
    n_next_links: int = 2,
) -> list[list[str]]:
    if isinstance(ids, str):
        ids = [ids]
    res_ids = []
    for id in ids:
        prev_ids = traverse_id(
            id=id,
            collection=collection,
            direction="prev",
            n_steps=n_prev_links,
        )
        next_ids = traverse_id(
            id=id,
            collection=collection,
            direction="next",
            n_steps=n_next_links,
        )
        res_ids.append(prev_ids[::-1] + [id] + next_ids)
    return res_ids


def rerank_chroma_results(
    query_text: str,
    results: QueryResult,
    cross_encoder_model: str = CROSS_ENCODER_MODEL,
) -> dict:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    cross_encoder = CrossEncoder(cross_encoder_model, device=device)
    pairs = [[query_text, doc] for doc in results["documents"][0]]  # type: ignore
    scores = cross_encoder.predict(pairs)
    scores_idx = sorted(
        range(len(scores)), key=lambda i: scores[i].item(), reverse=True
    )
    return {k: [[v[0][i] for i in scores_idx]] for k, v in results.items() if v}  # type: ignore


def query_collection(
    query_text: str,
    collection: ChromaCollection,
    n_results: int = 10,
    rerank_results: bool = False,
    n_prev_links: int = 2,
    n_next_links: int = 2,
    include: Include = ["metadatas", "documents"],
    reranker_model: str = CROSS_ENCODER_MODEL,
) -> tuple[list[GetResult], list[str]]:
    query_res = collection.query(
        query_texts=query_text, n_results=n_results, include=include
    )
    if rerank_results:
        query_res = rerank_chroma_results(
            query_text=query_text,
            results=query_res,
            cross_encoder_model=reranker_model,
        )
    init_ids = query_res["ids"][0]
    traversed_ids = traverse_ids(
        ids=init_ids,
        collection=collection,
        n_prev_links=n_prev_links,
        n_next_links=n_next_links,
    )
    results = [collection.get(ids=ids, include=include) for ids in traversed_ids]
    return results, init_ids
