"""
scripts/ingest_data.py — Scrape all banks and store in ChromaDB.

Usage:
  PYTHONPATH=. python3 scripts/ingest_data.py          # incremental
  PYTHONPATH=. python3 scripts/ingest_data.py --clear  # wipe and rebuild
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rag.knowledge_base import KnowledgeBase
from rag.scrapers import ALL_SCRAPERS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Clear DB before ingesting")
    args = parser.parse_args()

    kb = KnowledgeBase(persist_path=os.getenv("CHROMA_DB_PATH", "./data/chroma_db"))

    if args.clear:
        kb.delete_all()
        logger.info("Cleared existing data")

    total = 0
    for scraper_cls in ALL_SCRAPERS:
        scraper = scraper_cls()
        logger.info(f"{'─'*50}")
        logger.info(f"Scraping: {scraper.bank_name}")
        docs = scraper.scrape_all()
        logger.info(f"Scraped {len(docs)} chunks from {scraper.bank_name}")
        if docs:
            kb.upsert_documents(docs)
            logger.success(f"✓ Stored {len(docs)} chunks")
            total += len(docs)

    logger.info(f"{'─'*50}")
    logger.success(f"Ingestion complete. Total chunks: {total}")
    logger.info(f"DB stats: {kb.stats()}")


if __name__ == "__main__":
    main()
