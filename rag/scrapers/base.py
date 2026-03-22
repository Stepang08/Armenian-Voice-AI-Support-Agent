"""
Base scraper — shared HTTP fetching, chunking, and document creation.
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_fixed

from rag.models import BankDocument, Topic


class BaseBankScraper(ABC):
    bank_name: str = ""
    bank_id:   str = ""
    base_url:  str = ""

    def __init__(self, timeout: float = 20.0):
        self._client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9,hy;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    def _get(self, url: str) -> BeautifulSoup:
        logger.debug(f"GET {url}")
        r = self._client.get(url)
        r.raise_for_status()
        return BeautifulSoup(r.text, "lxml")

    def _make_doc(
        self,
        topic: Topic,
        title: str,
        content: str,
        url: str,
        bank_name: Optional[str] = None,
        bank_id: Optional[str] = None,
    ) -> Optional[BankDocument]:
        content = content.strip()
        if not content:
            return None
        return BankDocument(
            bank_name=bank_name or self.bank_name,
            bank_id=bank_id or self.bank_id,
            topic=topic,
            title=title,
            content=content,
            url=url,
        )

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 600) -> List[str]:
        """Split text into chunks of max_chars, breaking on newlines."""
        lines = text.split("\n")
        chunks, current = [], ""
        for line in lines:
            if len(current) + len(line) + 1 > max_chars and current:
                chunks.append(current.strip())
                current = line
            else:
                current += "\n" + line
        if current.strip():
            chunks.append(current.strip())
        return chunks or [text[:max_chars]]

    def scrape_all(self) -> List[BankDocument]:
        docs = []
        docs.extend(self.scrape_credits())
        docs.extend(self.scrape_deposits())
        docs.extend(self.scrape_branches())
        return docs

    @abstractmethod
    def scrape_credits(self) -> List[BankDocument]: ...

    @abstractmethod
    def scrape_deposits(self) -> List[BankDocument]: ...

    @abstractmethod
    def scrape_branches(self) -> List[BankDocument]: ...
