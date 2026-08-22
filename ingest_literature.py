"""
PRISMA Literature API Ingestion Pipeline
Target: Step 2 of PRISMA-compliant meta-analysis (CI timeouts and crash triage in game development)
Target Sources: arXiv API and CrossRef API (filtered for Association for Computing Machinery / ACM)
Search Logic: ("CI timeout" OR "continuous integration") AND ("crash triage" OR "automated repair" OR "OSSGameBench") AND "game"
Output: literature_raw.json
"""

import os
import re
import sys
import time
import json
import logging
import urllib.parse
from typing import List, Dict, Any, Optional
import xml.etree.ElementTree as ET
import requests
import arxiv

# ---------------------------------------------------------------------------
# Configuration and Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PRISMA_Ingestion")

SEARCH_QUERY_LOGIC = '("CI timeout" OR "continuous integration") AND ("crash triage" OR "automated repair" OR "OSSGameBench") AND "game"'
OUTPUT_FILE = "literature_raw.json"
USER_AGENT = "PRISMA-MetaAnalysis-Ingest/1.0 (academic-research; mailto:researcher@prisma-survey.org)"


# ---------------------------------------------------------------------------
# Helper Utility Functions
# ---------------------------------------------------------------------------
def clean_text(text: Optional[str]) -> str:
    """Sanitizes text by stripping XML/HTML tags and normalizing whitespace."""
    if not text:
        return ""
    # Remove HTML/XML markup (e.g. JATS XML tags from CrossRef abstracts)
    cleaned = re.sub(r"<[^>]+>", " ", text)
    # Collapse consecutive whitespace and strip edges
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    """
    Normalizes DOI to lowercase string without URL schemes or leading prefixes.
    Ensures consistent format for strict deduplication comparison.
    """
    if not doi:
        return None
    doi_clean = doi.strip().lower()
    # Strip common DOI URL resolvers
    doi_clean = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi_clean)
    doi_clean = re.sub(r"^doi:\s*", "", doi_clean)
    return doi_clean if doi_clean else None


# ---------------------------------------------------------------------------
# 1. arXiv API Ingestion
# ---------------------------------------------------------------------------
def fetch_arxiv_literature(query_logic: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """
    Queries the arXiv API using the official 'arxiv' Python library with fallback
    to direct Atom/XML HTTP endpoint handling. Incorporates retry backoff for rate limits.
    """
    logger.info("=" * 60)
    logger.info("Querying arXiv API...")
    logger.info(f"Query: {query_logic}")
    records = []

    # Method A: Using official arxiv library
    try:
        client = arxiv.Client(
            page_size=50,
            delay_seconds=3.5,
            num_retries=3
        )
        search = arxiv.Search(
            query=query_logic,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )
        for result in client.results(search):
            doi = normalize_doi(result.doi)
            authors = [author.name.strip() for author in result.authors]
            pub_date = result.published.strftime("%Y-%m-%d") if result.published else ""
            pdf_url = result.pdf_url
            if not pdf_url and result.entry_id:
                pdf_url = result.entry_id.replace("/abs/", "/pdf/") + ".pdf"

            record = {
                "title": clean_text(result.title),
                "abstract": clean_text(result.summary),
                "authors": authors,
                "publication_date": pub_date,
                "source_database": "arXiv",
                "DOI": doi,
                "pdf_url": pdf_url
            }
            records.append(record)

        logger.info(f"arXiv library query completed: successfully retrieved {len(records)} records.")
        return records
    except Exception as e:
        logger.warning(f"arXiv client encountered: {e}. Executing direct HTTP fallback...")

    # Method B: Direct HTTP GET with XML parsing and exponential backoff
    query_variants = [
        query_logic,
        '(all:"CI timeout" OR all:"continuous integration") AND (all:"crash triage" OR all:"automated repair" OR all:"OSSGameBench") AND all:game'
    ]

    for q_var in query_variants:
        encoded_q = urllib.parse.quote(q_var)
        url = f"https://export.arxiv.org/api/query?search_query={encoded_q}&start=0&max_results={max_results}"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml"
        }

        for attempt in range(1, 4):
            try:
                logger.info(f"arXiv HTTP fallback attempt {attempt}...")
                resp = requests.get(url, headers=headers, timeout=25)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.content)
                    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
                    entries = root.findall("atom:entry", ns)
                    for entry in entries:
                        title_el = entry.find("atom:title", ns)
                        title = clean_text(title_el.text if title_el is not None else "")
                        if not title:
                            continue

                        summary_el = entry.find("atom:summary", ns)
                        abstract = clean_text(summary_el.text if summary_el is not None else "")

                        published_el = entry.find("atom:published", ns)
                        pub_date = published_el.text.strip()[:10] if published_el is not None and published_el.text else ""

                        doi_el = entry.find("arxiv:doi", ns)
                        raw_doi = doi_el.text if doi_el is not None else None
                        doi = normalize_doi(raw_doi)

                        authors = [
                            a.find("atom:name", ns).text.strip()
                            for a in entry.findall("atom:author", ns)
                            if a.find("atom:name", ns) is not None and a.find("atom:name", ns).text
                        ]

                        pdf_url = None
                        for link in entry.findall("atom:link", ns):
                            if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                                pdf_url = link.attrib.get("href")
                                break
                        if not pdf_url:
                            id_el = entry.find("atom:id", ns)
                            if id_el is not None and id_el.text:
                                pdf_url = id_el.text.replace("/abs/", "/pdf/") + ".pdf"

                        records.append({
                            "title": title,
                            "abstract": abstract,
                            "authors": authors,
                            "publication_date": pub_date,
                            "source_database": "arXiv",
                            "DOI": doi,
                            "pdf_url": pdf_url
                        })
                    logger.info(f"arXiv HTTP fallback succeeded: fetched {len(records)} records.")
                    return records
                elif resp.status_code in [429, 503]:
                    backoff = 5 * attempt
                    logger.warning(f"arXiv returned HTTP {resp.status_code}. Backing off for {backoff}s...")
                    time.sleep(backoff)
                else:
                    logger.warning(f"arXiv HTTP status {resp.status_code}")
                    break
            except Exception as ex:
                logger.warning(f"arXiv HTTP attempt {attempt} error: {ex}")
                time.sleep(3)

    return records


# ---------------------------------------------------------------------------
# 2. CrossRef API Ingestion (ACM Filtered)
# ---------------------------------------------------------------------------
def parse_crossref_author(author_dict: Dict[str, Any]) -> str:
    """Formats CrossRef author dict to 'Given Family' or full name string."""
    if "name" in author_dict:
        return clean_text(author_dict["name"])
    given = author_dict.get("given", "").strip()
    family = author_dict.get("family", "").strip()
    if given and family:
        return f"{given} {family}"
    return clean_text(family or given or "Unknown")


def parse_crossref_date(item: Dict[str, Any]) -> str:
    """Extracts ISO/formatted date from CrossRef date-parts dictionary."""
    for field in ["issued", "published-print", "published-online", "published", "created"]:
        if field in item and isinstance(item[field], dict):
            date_parts = item[field].get("date-parts", [])
            if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
                parts = date_parts[0]
                if len(parts) == 1:
                    return f"{parts[0]:04d}"
                elif len(parts) == 2:
                    return f"{parts[0]:04d}-{parts[1]:02d}"
                elif len(parts) >= 3:
                    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
    return ""


def fetch_crossref_acm_literature(query_logic: str, max_records: int = 1000) -> List[Dict[str, Any]]:
    """
    Queries CrossRef API filtering specifically for publisher:
    'Association for Computing Machinery' (ACM Member ID: 320).
    Implements offset pagination to harvest all matching bibliographic records.
    """
    logger.info("=" * 60)
    logger.info("Querying CrossRef API (Filtered for Association for Computing Machinery / ACM)...")
    logger.info(f"Query: {query_logic}")
    records = []
    base_url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": USER_AGENT
    }

    rows_per_page = 100
    offset = 0
    total_available = None

    while True:
        params = {
            "query": query_logic,
            "filter": "member:320",  # Association for Computing Machinery (ACM)
            "rows": rows_per_page,
            "offset": offset
        }

        try:
            resp = requests.get(base_url, params=params, headers=headers, timeout=30)
            if resp.status_code != 200:
                logger.error(f"CrossRef request returned status {resp.status_code}: {resp.text[:200]}")
                break

            message = resp.json().get("message", {})
            if total_available is None:
                total_available = message.get("total-results", 0)
                logger.info(f"Total matching ACM records in CrossRef: {total_available}")

            items = message.get("items", [])
            if not items:
                logger.info("No more items returned from CrossRef.")
                break

            logger.info(f"Retrieved CrossRef batch: {len(items)} items (offset {offset}/{total_available})")

            for item in items:
                # Title
                raw_title = item.get("title", [""])
                title = raw_title[0] if isinstance(raw_title, list) and raw_title else str(raw_title)
                title = clean_text(title)

                # DOI Normalization
                raw_doi = item.get("DOI", "")
                doi = normalize_doi(raw_doi)

                # Authors
                authors = [parse_crossref_author(a) for a in item.get("author", [])]

                # Abstract
                abstract = clean_text(item.get("abstract", ""))

                # Publication Date
                pub_date = parse_crossref_date(item)

                # PDF URL Resolution
                pdf_url = None
                for link in item.get("link", []):
                    if link.get("content-type") == "application/pdf":
                        pdf_url = link.get("URL")
                        break
                # Default canonical ACM DL URL if direct PDF URL not provided in link
                if not pdf_url and doi:
                    pdf_url = f"https://dl.acm.org/doi/pdf/{doi}"

                records.append({
                    "title": title,
                    "abstract": abstract,
                    "authors": authors,
                    "publication_date": pub_date,
                    "source_database": "CrossRef (ACM Digital Library)",
                    "DOI": doi,
                    "pdf_url": pdf_url
                })

            offset += len(items)
            if offset >= total_available or len(records) >= max_records or len(items) < rows_per_page:
                break

            time.sleep(0.3)  # Polite API pacing

        except Exception as e:
            logger.error(f"Error querying CrossRef API: {e}")
            break

    logger.info(f"CrossRef ACM retrieval finished: fetched {len(records)} total records.")
    return records


# ---------------------------------------------------------------------------
# 3. Deduplication Logic
# ---------------------------------------------------------------------------
def deduplicate_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Implements strict DOI-based deduplication logic prior to export.
    - Normalizes all DOIs to lowercase for exact comparison.
    - When DOI collision occurs, merges metadata to preserve richest fields.
    - For records without DOIs, applies fallback canonicalized title deduplication.
    """
    logger.info("=" * 60)
    logger.info(f"Starting deduplication on {len(records)} collected records...")

    seen_dois: Dict[str, int] = {}
    seen_titles: Dict[str, int] = {}
    deduplicated: List[Dict[str, Any]] = []

    doi_duplicates = 0
    title_duplicates = 0

    for record in records:
        doi = record.get("DOI")
        title_key = re.sub(r"[^a-z0-9]", "", record.get("title", "").lower())

        if doi:
            doi_norm = doi.strip().lower()
            record["DOI"] = doi_norm

            if doi_norm in seen_dois:
                doi_duplicates += 1
                idx = seen_dois[doi_norm]
                existing = deduplicated[idx]

                # Merge richer fields if missing in existing entry
                if not existing.get("abstract") and record.get("abstract"):
                    existing["abstract"] = record["abstract"]
                if not existing.get("pdf_url") and record.get("pdf_url"):
                    existing["pdf_url"] = record["pdf_url"]
                if not existing.get("publication_date") and record.get("publication_date"):
                    existing["publication_date"] = record["publication_date"]
                if not existing.get("authors") and record.get("authors"):
                    existing["authors"] = record["authors"]
                if record["source_database"] not in existing["source_database"]:
                    existing["source_database"] += f" / {record['source_database']}"
            else:
                seen_dois[doi_norm] = len(deduplicated)
                if title_key:
                    seen_titles[title_key] = len(deduplicated)
                deduplicated.append(record)
        else:
            # Fallback title deduplication for preprints/items lacking official DOI
            if title_key and title_key in seen_titles:
                title_duplicates += 1
                idx = seen_titles[title_key]
                existing = deduplicated[idx]
                if not existing.get("abstract") and record.get("abstract"):
                    existing["abstract"] = record["abstract"]
                if not existing.get("pdf_url") and record.get("pdf_url"):
                    existing["pdf_url"] = record["pdf_url"]
            else:
                if title_key:
                    seen_titles[title_key] = len(deduplicated)
                deduplicated.append(record)

    logger.info(
        f"Deduplication complete: {len(records)} raw records reduced to {len(deduplicated)} unique records."
    )
    logger.info(f" - DOI collisions resolved: {doi_duplicates}")
    logger.info(f" - Title collisions resolved: {title_duplicates}")
    return deduplicated


# ---------------------------------------------------------------------------
# 4. Main Ingestion Pipeline Execution
# ---------------------------------------------------------------------------
def main():
    start_time = time.time()
    logger.info("Starting PRISMA Step 2 Academic Literature Ingestion")
    logger.info(f"Target Domain: CI Timeouts and Crash Triage in Game Development")
    logger.info(f"Query Logic: {SEARCH_QUERY_LOGIC}")

    # 1. arXiv API Querying
    arxiv_records = fetch_arxiv_literature(SEARCH_QUERY_LOGIC, max_results=100)

    # 2. CrossRef API Querying (Association for Computing Machinery)
    crossref_records = fetch_crossref_acm_literature(SEARCH_QUERY_LOGIC, max_records=1000)

    # 3. Aggregation
    combined_raw = arxiv_records + crossref_records
    logger.info(f"Aggregated raw records: {len(combined_raw)} (arXiv: {len(arxiv_records)}, CrossRef/ACM: {len(crossref_records)})")

    # 4. Strict Deduplication
    sanitized_dataset = deduplicate_records(combined_raw)

    # 5. Export to literature_raw.json
    output_path = os.path.abspath(OUTPUT_FILE)
    logger.info(f"Exporting sanitized dataset to '{output_path}'...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sanitized_dataset, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - start_time
    logger.info(f"Successfully exported {len(sanitized_dataset)} records to '{OUTPUT_FILE}' in {elapsed:.2f}s.")
    logger.info("PRISMA Step 2 Ingestion finished successfully.")


if __name__ == "__main__":
    print("=" * 80)
    print(" [WARNING: SYNTHETIC PIPELINE DEMONSTRATION]")
    print(" All data processed by this script is hallucinated/placeholder data.")
    print("=" * 80)

    main()
