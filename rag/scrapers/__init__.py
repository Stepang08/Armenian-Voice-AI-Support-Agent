"""
Scraper registry.

Uses AfmScraper — a single scraper for all 17 Armenian banks via afm.am.

To add a new data source:
  1. Create a scraper class extending BaseBankScraper
  2. Add it to ALL_SCRAPERS below
"""

from rag.scrapers.afm import AfmScraper
from rag.scrapers.base import BaseBankScraper

ALL_SCRAPERS: list[type[BaseBankScraper]] = [
    AfmScraper,
]

__all__ = ["ALL_SCRAPERS", "BaseBankScraper"]
