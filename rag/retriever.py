"""
Retriever — topic classification + semantic search.
"""

import re
from typing import List, Tuple

from loguru import logger

from rag.knowledge_base import KnowledgeBase
from rag.models import RetrievedChunk, Topic

# Keywords that trigger each topic (Armenian + English + transliteration)
_TOPIC_KEYWORDS = {
    Topic.CREDIT: [
        "վարկ", "credit", "loan", "կրեդիտ", "ипотека", "mortgage",
        "ipoteka", "vark", "փոխառու", "տոկոս", "faiz",
        "անշարժ գույք", "բնակարան", "ավտո",
    ],
    Topic.DEPOSIT: [
        "ավանդ", "deposit", "депозит", "avand", "накопление",
        "խնայողություն", "savings", "interest", "rate", "տոկոս",
        "AMD", "USD", "EUR", "դրամ", "դոլար", "եվրո", "percent", "%",
    ],
    Topic.BRANCH: [
        "մասնաճյուղ", "branch", "филиал", "masnachyugh", "address",
        "հասցե", "hasde", "working hours", "աշխ", "phone", "հեռախոս",
        "բաց", "open", "location", "map", "atm", "բանկոmat",
    ],
}

# Phrases that are clearly off-topic
_OFF_TOPIC_PATTERNS = [
    r"\bcrypto\b", r"\bbitcoin\b", r"\bweather\b", r"\bsport\b",
    r"\bfootball\b", r"\bpolitics\b", r"\bnews\b", r"\bcooking\b",
    r"\brecipe\b", r"\bfilm\b", r"\bmovie\b",
]

_SIMILARITY_THRESHOLD = 0.25


class Retriever:
    def __init__(self, kb: KnowledgeBase):
        self._kb = kb

    def retrieve(self, query: str) -> Tuple[List[RetrievedChunk], bool]:
        """
        Returns (chunks, is_on_topic).
        """
        # Check explicit off-topic patterns first
        q_lower = query.lower()
        for pattern in _OFF_TOPIC_PATTERNS:
            if re.search(pattern, q_lower):
                logger.debug(f"Off-topic pattern matched: {query!r}")
                return [], False

        # Detect relevant topics
        detected = self._detect_topics(query)

        if not detected:
            # No topic keywords — treat as general banking query
            # search across all topics rather than refusing
            detected = list(Topic)

        logger.debug(f"Detected topics: {[t.value for t in detected]} for: {query!r}")

        chunks = self._kb.query(query, topics=detected, n_results=5)
        chunks = [c for c in chunks if c.score >= _SIMILARITY_THRESHOLD]

        if not chunks:
            # Try without topic filter as fallback
            chunks = self._kb.query(query, topics=list(Topic), n_results=5)
            chunks = [c for c in chunks if c.score >= _SIMILARITY_THRESHOLD]

        return chunks, True  # Always on-topic if we got here

    @staticmethod
    def _detect_topics(query: str) -> List[Topic]:
        q_lower = query.lower()
        detected = []
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw.lower() in q_lower for kw in keywords):
                detected.append(topic)
        return detected

    @staticmethod
    def format_context(chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return "No specific information found. Answer based on general Armenian banking knowledge."
        parts = []
        for c in chunks:
            parts.append(f"[{c.bank_name} — {c.title}]\n{c.content}\nSource: {c.url}")
        return "\n\n---\n\n".join(parts)
