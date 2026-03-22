"""
ChromaDB wrapper — stores and retrieves BankDocument embeddings.
"""

import os
from typing import List

import chromadb
from chromadb.utils import embedding_functions
from loguru import logger

from rag.models import BankDocument, RetrievedChunk, Topic


class KnowledgeBase:
    def __init__(self, persist_path: str = "./data/chroma_db"):
        os.makedirs(persist_path, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_path)
        self._ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small",
        )
        self._collection = self._client.get_or_create_collection(
            name="bank_knowledge",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"KnowledgeBase ready — {self._collection.count()} docs in 'bank_knowledge'")

    def upsert_documents(self, docs: List[BankDocument]) -> None:
        if not docs:
            return
        self._collection.upsert(
            ids=[d.doc_id for d in docs],
            documents=[d.content for d in docs],
            metadatas=[{
                "bank_name": d.bank_name,
                "bank_id":   d.bank_id,
                "topic":     d.topic.value,
                "title":     d.title,
                "url":       d.url,
            } for d in docs],
        )
        logger.info(f"Upserted {len(docs)} documents into ChromaDB")

    def query(
        self,
        query_text: str,
        topics: List[Topic],
        n_results: int = 5,
    ) -> List[RetrievedChunk]:
        where = {"topic": {"$in": [t.value for t in topics]}} if topics else None
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=min(n_results, self._collection.count()),
                where=where,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning(f"ChromaDB query failed: {e}")
            return []

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append(RetrievedChunk(
                doc_id=meta.get("title", ""),
                bank_name=meta["bank_name"],
                topic=Topic(meta["topic"]),
                title=meta["title"],
                content=doc,
                url=meta["url"],
                score=1 - dist,
            ))
        return chunks

    def delete_all(self) -> None:
        self._client.delete_collection("bank_knowledge")
        self._collection = self._client.get_or_create_collection(
            name="bank_knowledge",
            embedding_function=self._ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Cleared all documents from ChromaDB")

    def stats(self) -> dict:
        return {"total_documents": self._collection.count(), "collection": "bank_knowledge"}
