"""
rag/scrapers/afm.py — Scraper for afm.am

afm.am is the authoritative Armenian financial market aggregator.
It aggregates real-time data from ALL 17 licensed Armenian banks.
Pages are fully server-side rendered — no JS required, no bot blocking.
Data is updated daily and citable as a regulatory-grade source.

Coverage:
  Deposits → 1,600+ products across all banks, all currencies
  Loans    → consumer loans, mortgages, online loans
  Branches → manual data (afm.am does not list branch addresses)

Scalability: adding a new product category = add one URL. No code changes.
"""

import re
import time
from typing import Dict, List, Tuple

from loguru import logger

from rag.models import BankDocument, Topic
from rag.scrapers.base import BaseBankScraper

BASE = "https://afm.am"

_DEPOSIT_URLS = [
    f"{BASE}/en/deposits",
]

_CREDIT_URLS = [
    f"{BASE}/en/loans/consumer-loans",
    f"{BASE}/en/loans/online-loans",
    f"{BASE}/en/mortgage",
]

# All 17 licensed Armenian banks
_KNOWN_BANKS = [
    "Ameriabank", "Ardshinbank", "Evocabank", "ACBA Bank", "Acba Bank",
    "AMIO Bank", "Inecobank", "Converse Bank", "VTB Bank (Armenia)",
    "Araratbank", "Unibank", "IDBank", "Fast Bank", "Armeconombank",
    "Byblos Bank Armenia", "ArmSwissBank", "Artsakhbank", "Mellat Bank",
]

_BANK_ID_MAP = {
    "Ameriabank": "ameriabank", "Ardshinbank": "ardshinbank",
    "Evocabank": "evocabank", "ACBA Bank": "acba", "Acba Bank": "acba",
    "AMIO Bank": "amio", "Inecobank": "inecobank",
    "Converse Bank": "converse", "VTB Bank (Armenia)": "vtb",
    "Araratbank": "araratbank", "Unibank": "unibank", "IDBank": "idbank",
    "Fast Bank": "fastbank", "Armeconombank": "armeconombank",
    "Byblos Bank Armenia": "byblos", "ArmSwissBank": "armswissbank",
    "Artsakhbank": "artsakhbank", "Mellat Bank": "mellat",
}

_BRANCH_DATA: Dict[str, List[Dict]] = {
    "Ameriabank": [
        {"title": "Head Office", "content": "Ameriabank Head Office. Address: 2 Vazgen Sargsyan St, 0010 Yerevan. Phone: +374 10 561111. Hours: Mon-Fri 09:30-17:00, Sat 10:00-15:30."},
        {"title": "Full Branch Network", "content": "Ameriabank — 50+ branches across Armenia. Yerevan: Mashtots Ave, Arabkir, Nor Nork, Erebuni, Davtashen, Komitas, Yerevan Mall, Dalma Mall, Rio Mall. Regional: Gyumri, Vanadzor, Armavir, Hrazdan."},
    ],
    "Ardshinbank": [
        {"title": "Head Office", "content": "Ardshinbank Head Office. Address: 13 Grigor Lusavorich St, Yerevan. Phone: +374 10 560555. Hours: Mon-Fri 09:00-18:00."},
        {"title": "Full Branch Network", "content": "Ardshinbank — one of Armenia's largest networks. Yerevan: Kentron, Arabkir, Nor Nork, Erebuni, Davtashen, Malatia, Shengavit, Avan. Regional: Gyumri, Vanadzor, Abovyan, Hrazdan, Charentsavan, Armavir, Artashat, Gavar, Kapan, Goris."},
    ],
    "Evocabank": [
        {"title": "Head Office", "content": "Evocabank Head Office. Address: 9 Grigor Lusavorich St, 0015 Yerevan. Phone: +374 10 605555. Hours: Mon-Fri 09:00-18:00, Sat 10:00-15:00. Best Digital Bank Armenia 2024."},
        {"title": "Branch Network", "content": "Evocabank: Yerevan (Kentron, Arabkir, Malatia, Shengavit), Gyumri, Vanadzor, Abovyan, Hrazdan. Most services via EvocaTouch mobile app."},
    ],
    "ACBA Bank": [
        {"title": "Head Office & Network", "content": "ACBA Bank. Address: 82/1 Aram St, Yerevan. Phone: +374 10 311111. Hours: Mon-Fri 09:00-18:00. Extensive network with strong agricultural focus across all regions."},
    ],
    "AMIO Bank": [
        {"title": "Head Office & Network", "content": "AMIO Bank. Address: 48 Nalbandyan St, Yerevan. Phone: +374 10 510051. Hours: Mon-Fri 09:00-18:00. Branches in Yerevan and major cities. Digital-first with AMIO Mobile app."},
    ],
    "Inecobank": [
        {"title": "Head Office & Network", "content": "Inecobank. Address: 131 Anrapetutyan St, Yerevan. Phone: +374 10 510510. Hours: Mon-Fri 09:00-18:00. Branches: Yerevan, Gyumri, Vanadzor, Abovyan."},
    ],
    "Converse Bank": [
        {"title": "Head Office & Network", "content": "Converse Bank. Address: 26/1 Marshal Baghramyan Ave, Yerevan. Phone: +374 10 511212. Hours: Mon-Fri 09:00-18:00. Branches across Yerevan and regional cities."},
    ],
    "VTB Bank (Armenia)": [
        {"title": "Head Office & Network", "content": "VTB Bank Armenia. Address: 46 Nalbandyan St, Yerevan. Phone: +374 10 597222. Hours: Mon-Fri 09:00-18:00. Part of VTB Group. Branches in Yerevan and regional centers."},
    ],
    "Araratbank": [
        {"title": "Head Office & Network", "content": "Araratbank. Address: 50 Grigor Lusavorich St, Yerevan. Phone: +374 10 592222. Hours: Mon-Fri 09:00-18:00. Branches across Yerevan and Armenia."},
    ],
    "Unibank": [
        {"title": "Head Office & Network", "content": "Unibank. Address: 27 Vagharshyan St, Yerevan. Phone: +374 10 599955. Hours: Mon-Fri 09:00-18:00. Branches in Yerevan and major regional cities."},
    ],
    "IDBank": [
        {"title": "Head Office & Network", "content": "IDBank. Address: 15 Moskovyan St, Yerevan. Phone: +374 10 593311. Hours: Mon-Fri 09:00-18:00. Digital bank — most services via Idram&IDBank app. Branches in Yerevan, Gyumri, Vanadzor."},
    ],
    "Fast Bank": [
        {"title": "Head Office & Network", "content": "Fast Bank. Yerevan, Armenia. Phone: +374 10 272727. Hours: Mon-Fri 09:00-18:00. Known for rapid loan processing. Branches in Yerevan."},
    ],
    "Armeconombank": [
        {"title": "Head Office & Network", "content": "Armeconombank. Address: 23/1 Abovyan St, Yerevan. Phone: +374 10 596696. Hours: Mon-Fri 09:00-18:00. Branches in Yerevan and regional cities."},
    ],
    "Byblos Bank Armenia": [
        {"title": "Head Office & Network", "content": "Byblos Bank Armenia. Address: 18 Vazgen Sargsyan St, Yerevan. Phone: +374 10 510510. Hours: Mon-Fri 09:00-18:00. Part of Byblos Bank international group."},
    ],
    "ArmSwissBank": [
        {"title": "Head Office", "content": "ArmSwissBank. Address: 19 Abovyan St, Yerevan. Phone: +374 10 599009. Hours: Mon-Fri 09:00-18:00. Boutique private bank in central Yerevan."},
    ],
    "Artsakhbank": [
        {"title": "Head Office & Network", "content": "Artsakhbank. Yerevan, Armenia. Phone: +374 10 515050. Hours: Mon-Fri 09:00-18:00. Branches in Yerevan and regional centers."},
    ],
    "Mellat Bank": [
        {"title": "Head Office", "content": "Mellat Bank. Address: 44 Nalbandyan St, Yerevan. Phone: +374 10 542542. Hours: Mon-Fri 09:00-18:00. Iranian-owned bank operating in Armenia."},
    ],
}


class AfmScraper(BaseBankScraper):
    """
    Scrapes afm.am — the single authoritative source for all 17 Armenian banks.

    Data source: afm.am (Armenian Financial Market aggregator)
    Updated: daily
    Coverage: all licensed banks in Armenia
    Method: plain HTTP GET — no JavaScript, no bot blocking

    Scalability:
      - All 17 Armenian banks covered automatically
      - Adding a new product category: add URL to _DEPOSIT_URLS or _CREDIT_URLS
      - No per-bank Python files needed
    """

    bank_name = "AFM (Armenian Financial Market)"
    bank_id   = "afm"
    base_url  = BASE

    def scrape_all(self) -> List[BankDocument]:
        docs: List[BankDocument] = []
        docs.extend(self._scrape_pages(Topic.DEPOSIT, _DEPOSIT_URLS, "deposit"))
        docs.extend(self._scrape_pages(Topic.CREDIT,  _CREDIT_URLS,  "loan"))
        docs.extend(self._scrape_branches())
        return docs

    def scrape_credits(self)  -> List[BankDocument]:
        return self._scrape_pages(Topic.CREDIT, _CREDIT_URLS, "loan")

    def scrape_deposits(self) -> List[BankDocument]:
        return self._scrape_pages(Topic.DEPOSIT, _DEPOSIT_URLS, "deposit")

    def scrape_branches(self) -> List[BankDocument]:
        return self._scrape_branches()

    # ── Core ──────────────────────────────────────────────────────────

    def _scrape_pages(self, topic: Topic, urls: List[str], label: str) -> List[BankDocument]:
        by_bank: Dict[str, List[str]] = {}

        for url in urls:
            try:
                soup = self._get(url)
                pairs = self._extract_products(soup)
                logger.info(f"[afm] {label} {url} → {len(pairs)} entries")
                for bank, text in pairs:
                    by_bank.setdefault(bank, []).append(text)
                time.sleep(1)
            except Exception as e:
                logger.error(f"[afm] failed {url}: {e}")

        docs: List[BankDocument] = []
        for bank_name, entries in by_bank.items():
            bank_id = _BANK_ID_MAP.get(bank_name, re.sub(r"[^a-z0-9]", "", bank_name.lower()))
            header  = f"{bank_name} {label} products — source: afm.am (live data):\n"
            combined = header + "\n".join(entries)
            for i, chunk in enumerate(self._chunk_text(combined, max_chars=600)):
                docs.append(BankDocument(
                    bank_name=bank_name,
                    bank_id=bank_id,
                    topic=topic,
                    title=f"{bank_name} {label} (part {i+1})",
                    content=chunk,
                    url=urls[0],
                ))
        logger.info(f"[afm] {label}: {len(docs)} docs for {len(by_bank)} banks")
        return docs

    # ── Parsing ───────────────────────────────────────────────────────

    def _extract_products(self, soup) -> List[Tuple[str, str]]:
        results = self._parse_h6(soup)
        if not results:
            results = self._text_fallback(soup)
        return results

    def _parse_h6(self, soup) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        h6_tags = soup.find_all("h6")
        i = 0
        while i < len(h6_tags):
            text = h6_tags[i].get_text(strip=True)
            bank = self._match_bank(text)
            if bank:
                fields = []
                j = i + 1
                while j < len(h6_tags) and j < i + 8:
                    ft = h6_tags[j].get_text(strip=True)
                    if self._match_bank(ft):
                        break
                    if ft and ft not in ("More details", "State program"):
                        fields.append(ft)
                    j += 1
                if fields:
                    results.append((bank, "• " + " | ".join(fields)))
                    i = j
                    continue
            i += 1
        return results

    def _text_fallback(self, soup) -> List[Tuple[str, str]]:
        results: List[Tuple[str, str]] = []
        lines = [l.strip() for l in soup.get_text(separator="\n").splitlines() if l.strip()]
        current_bank, current_product, current_fields = "", "", []

        def flush():
            if current_bank and (current_product or current_fields):
                line = current_product
                if current_fields:
                    line += " | " + " | ".join(current_fields[:4])
                results.append((current_bank, "• " + line))

        for line in lines:
            bank = self._match_bank(line)
            if bank and len(line) < 80:
                flush()
                current_bank, current_product, current_fields = bank, "", []
            elif current_bank:
                if line in ("More details", "State program", "Reset"):
                    continue
                if any(c in line for c in ["%", "֏", "AMD", "USD", "EUR"]) or \
                   any(k in line.lower() for k in ["year", "month", "day", "to ", "from "]):
                    current_fields.append(line)
                elif not current_product and 3 < len(line) < 100:
                    current_product = line
        flush()
        return results

    @staticmethod
    def _match_bank(text: str) -> str:
        for bank in _KNOWN_BANKS:
            if bank.lower() in text.lower() and len(text) < 80:
                return bank
        return ""

    def _scrape_branches(self) -> List[BankDocument]:
        docs: List[BankDocument] = []
        for bank_name, branches in _BRANCH_DATA.items():
            bank_id = _BANK_ID_MAP.get(bank_name, re.sub(r"[^a-z0-9]", "", bank_name.lower()))
            for b in branches:
                doc = self._make_doc(
                    Topic.BRANCH,
                    f"{bank_name} — {b['title']}",
                    b["content"],
                    f"https://afm.am/en",
                    bank_name=bank_name,
                    bank_id=bank_id,
                )
                if doc:
                    docs.append(doc)
        logger.info(f"[afm] branches: {len(docs)} docs for {len(_BRANCH_DATA)} banks")
        return docs
