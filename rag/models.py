"""
Shared data models for the RAG pipeline.
"""

from enum import Enum
from pydantic import BaseModel, Field


class Topic(str, Enum):
    CREDIT  = "credit"
    DEPOSIT = "deposit"
    BRANCH  = "branch"


class BankDocument(BaseModel):
    bank_name: str
    bank_id:   str
    topic:     Topic
    title:     str
    content:   str
    url:       str
    language:  str = "hy"

    @property
    def doc_id(self) -> str:
        import hashlib
        unique = f"{self.bank_id}|{self.topic.value}|{self.title}|{self.url}|{self.content}"
        return hashlib.md5(unique.encode()).hexdigest()


class RetrievedChunk(BaseModel):
    doc_id:    str
    bank_name: str
    topic:     Topic
    title:     str
    content:   str
    url:       str
    score:     float
