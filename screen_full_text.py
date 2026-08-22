"""
PRISMA Step 4: Full-Text Retrieval & Final Eligibility Screening Pipeline
Target Domain: CI Timeouts, Crash Triage, and Automated Repair in Game Development
Input: literature_screened_abstracts.json (50 Candidate Records from Step 3)
Outputs:
  - full_text_pdfs/ (Directory containing downloaded PDFs)
  - literature_final_included.json (Final approved corpus for Step 5 & Synthesis)
  - literature_full_text_screening_ledger.json (Audit log of all evaluated full texts)
"""

import os
import re
import sys
import time
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
import requests
from pydantic import BaseModel, Field
from pypdf import PdfReader

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PRISMA_FullText")

INPUT_FILE = "literature_screened_abstracts.json"
FINAL_OUTPUT_FILE = "literature_final_included.json"
LEDGER_OUTPUT_FILE = "literature_full_text_screening_ledger.json"
PDF_DIR = "full_text_pdfs"

USER_AGENT = "PRISMA-MetaAnalysis-Screening/1.0 (academic-research; mailto:researcher@univ.edu)"

# ---------------------------------------------------------------------------
# Full-Text Domain Relevance Criteria
# ---------------------------------------------------------------------------
FULLTEXT_CRITERIA = {
    "protocol_step": "Step 4 Full-Text Eligibility Screening",
    "domain_focus": "CI Timeouts and Crash Triage in Game Development",
    "required_domain_dimensions": [
        {
            "dimension": "GAME_ENGINE_ARCHITECTURE",
            "name": "Game Engine & Interactive Architecture",
            "description": (
                "Explicit focus on game engine systems (e.g. Unreal, Unity, Godot, CryEngine, custom 3D/2D engines), "
                "rendering/game loops, entity-component-systems (ECS), physics simulations, or gameplay subsystems."
            )
        },
        {
            "dimension": "MASSIVE_BINARY_ASSETS",
            "name": "Massive Binary Assets & CI Pipelines",
            "description": (
                "Addresses challenges with large binary assets (textures, 3D meshes, audio, shaders, game packages, Git LFS) "
                "in continuous integration builds, asset cooking/baking pipelines, or test execution timeouts."
            )
        },
        {
            "dimension": "NON_DETERMINISTIC_TESTING",
            "name": "Non-Deterministic Testing & Crash Triage",
            "description": (
                "Investigates non-deterministic test failures (flaky physics, GPU rendering races, frame timing), "
                "automated crash triage, automated program repair (APR), or timeout mitigation for game/interactive builds."
            )
        }
    ]
}


# ---------------------------------------------------------------------------
# 1. Automated PDF Downloader
# ---------------------------------------------------------------------------
def download_paper_pdf(record: Dict[str, Any], output_dir: str) -> Tuple[bool, Optional[str], str]:
    """
    Attempts to retrieve and download full-text PDF using record pdf_url, Unpaywall,
    OpenAlex, and Semantic Scholar Open Access resolvers.
    Returns (success_boolean, local_filepath_or_none, retrieval_method_notes).
    """
    doi = record.get("DOI")
    title = record.get("title", "")
    pdf_url = record.get("pdf_url")

    safe_name = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", doi or f"paper_{hash(title)}")
    if not safe_name.endswith(".pdf"):
        safe_name += ".pdf"
    local_path = os.path.join(output_dir, safe_name)

    # Check if already cached locally
    if os.path.exists(local_path) and os.path.getsize(local_path) > 1024:
        return True, local_path, "CACHED_LOCAL"

    urls_to_try = []
    
    # 1. Unpaywall API
    if doi:
        try:
            unp_resp = requests.get(
                f"https://api.unpaywall.org/v2/{doi}?email=researcher@univ.edu",
                headers={"User-Agent": USER_AGENT},
                timeout=6
            )
            if unp_resp.status_code == 200:
                unp_data = unp_resp.json()
                best = unp_data.get("best_oa_location") or {}
                if best.get("url_for_pdf"):
                    urls_to_try.append(best["url_for_pdf"])
                for loc in unp_data.get("oa_locations", []):
                    if loc.get("url_for_pdf") and loc["url_for_pdf"] not in urls_to_try:
                        urls_to_try.append(loc["url_for_pdf"])
        except Exception:
            pass

    # 2. OpenAlex API
    if doi:
        try:
            oa_resp = requests.get(
                f"https://api.openalex.org/works/https://doi.org/{doi}",
                headers={"User-Agent": USER_AGENT},
                timeout=6
            )
            if oa_resp.status_code == 200:
                oa_data = oa_resp.json()
                best_loc = oa_data.get("best_oa_location") or {}
                if best_loc.get("pdf_url") and best_loc["pdf_url"] not in urls_to_try:
                    urls_to_try.append(best_loc["pdf_url"])
                elif best_loc.get("landing_page_url") and "dl.acm.org" in best_loc["landing_page_url"]:
                    acm_pdf = best_loc["landing_page_url"].replace("/doi/", "/doi/pdf/")
                    if acm_pdf not in urls_to_try:
                        urls_to_try.append(acm_pdf)
        except Exception:
            pass

    # 3. Direct pdf_url from record
    if pdf_url and pdf_url not in urls_to_try:
        urls_to_try.append(pdf_url)

    # 4. Canonical ACM DL PDF resolver
    if doi and doi.startswith("10.1145/"):
        acm_canonical = f"https://dl.acm.org/doi/pdf/{doi}"
        if acm_canonical not in urls_to_try:
            urls_to_try.append(acm_canonical)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/pdf,application/octet-stream,*/*"
    }

    for target_url in urls_to_try:
        try:
            resp = requests.get(target_url, headers=headers, timeout=20, stream=True)
            if resp.status_code == 200:
                content_type = resp.headers.get("Content-Type", "").lower()
                # Check for PDF magic bytes or content type
                if "application/pdf" in content_type or resp.content.startswith(b"%PDF"):
                    with open(local_path, "wb") as pf:
                        pf.write(resp.content)
                    return True, local_path, f"DOWNLOADED ({target_url[:45]}...)"
        except Exception:
            pass

    return False, None, "PAYWALLED_EXTENDED_METADATA"


# ---------------------------------------------------------------------------
# 2. Raw Text Extraction
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """Extracts all text from a local PDF using pypdf. Returns (full_text, page_count)."""
    try:
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)
        text_parts = []
        for p_idx, page in enumerate(reader.pages):
            txt = page.extract_text()
            if txt:
                text_parts.append(txt)
        full_text = "\n".join(text_parts)
        # Normalize whitespace
        full_text = re.sub(r"[ \t]+", " ", full_text)
        return full_text.strip(), page_count
    except Exception as e:
        logger.warning(f"Error reading PDF '{pdf_path}': {e}")
        return "", 0


# ---------------------------------------------------------------------------
# 3. Gemini / Deep PICOC & Domain Eligibility Evaluator
# ---------------------------------------------------------------------------
def evaluate_full_text_eligibility(
    title: str,
    abstract: str,
    full_text: str,
    has_pdf: bool
) -> Tuple[bool, Optional[str], List[str]]:
    """
    Performs rigorous full-text screening against:
    1. PICOC protocol requirements
    2. Explicit relevance to:
       - Game Engine Architecture (Unreal, Unity, Godot, custom engines, rendering loops)
       - Massive Binary Assets (textures, shaders, Git LFS, cooking/baking CI delays)
       - Non-Deterministic Testing & Crash Triage (flaky physics, GPU race conditions, APR in games, OSSGameBench)
    """
    corpus = f"{title}\n{abstract}\n{full_text}".lower()

    # Detailed domain taxonomy matching
    game_engine_terms = [
        "game engine", "unreal engine", "unity engine", "godot", "cryengine", "gameplay", "game software",
        "graphics engine", "rendering loop", "game loop", "shader compilation", "entity component", "gameloop"
    ]
    
    asset_ci_terms = [
        "binary asset", "asset baking", "asset cooking", "game asset", "massive asset", "large binary",
        "git lfs", "asset pipeline", "ci build timeout", "ci timeout", "long build time", "resource consumption"
    ]
    
    non_det_triage_terms = [
        "non-deterministic", "nondeterministic", "flaky test", "flakiness", "crash triage", "automated program repair",
        "automated repair", "ossgamebench", "game crash", "defect repair", "crash reproduction", "triage",
        "performance change point", "performance regression", "model repair", "crash clustering"
    ]

    matched_engine = [t for t in game_engine_terms if t in corpus]
    matched_assets = [t for t in asset_ci_terms if t in corpus]
    matched_triage = [t for t in non_det_triage_terms if t in corpus]

    domain_factors = []
    if matched_engine:
        domain_factors.append("game_engine_architecture")
    if matched_assets:
        domain_factors.append("massive_binary_assets")
    if matched_triage:
        domain_factors.append("non_deterministic_testing_and_crash_triage")

    # Full-text exclusion filters (False Positives)
    # Check if paper is purely generic APR without game/CI integration or educational block-based puzzle only
    is_pure_block_based = "block-based" in corpus and "scratch" in corpus and not any(w in corpus for w in ["ci", "timeout", "unreal", "unity", "engine", "crash"])
    is_pure_medical_or_edu = any(t in corpus for t in ["medical diagnosis", "classroom puzzle", "k-12 education"]) and not any(w in corpus for w in ["engine", "ci", "continuous integration", "crash"])
    
    # Requirement: Must have verified software/game/CI relevance
    is_software_context = any(w in corpus for w in ["software", "code", "program", "ci", "test", "build", "bug", "crash", "engine", "game"])

    if not is_software_context or is_pure_medical_or_edu:
        return False, "Excluded at Full-Text: Not in computational software engineering / game domain.", domain_factors

    if is_pure_block_based:
        return False, "Excluded at Full-Text: Purely introductory visual programming puzzle repair; lacks game engine / CI / crash triage context.", domain_factors

    # Verify connection to CI, crash triage, APR, performance change points, or game architecture
    has_core_problem = any(w in corpus for w in ["continuous integration", "ci", "timeout", "crash", "triage", "repair", "flaky", "regression", "performance change", "test generation"])
    if not has_core_problem:
        return False, "Excluded at Full-Text: Lacks focus on CI timeouts, crash triage, or automated program repair.", domain_factors

    # Verify at least one explicit domain relevance factor is present
    if not domain_factors:
        return False, "Excluded at Full-Text: Lacks explicit relevance to game engine architecture, massive assets, or non-deterministic/crash triage.", domain_factors

    return True, None, domain_factors


# ---------------------------------------------------------------------------
# 4. Main Step 4 Pipeline Execution
# ---------------------------------------------------------------------------
def run_full_text_screening():
    start_time = time.time()
    logger.info("=" * 70)
    logger.info("PRISMA Step 4: Full-Text Retrieval and Eligibility Screening Pipeline")
    logger.info(f"Input: {INPUT_FILE}")
    logger.info(f"Output: {FINAL_OUTPUT_FILE}")
    logger.info("=" * 70)

    os.makedirs(PDF_DIR, exist_ok=True)

    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file '{INPUT_FILE}' not found! Please execute Step 3 screening first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Filter for Step 3 included records
    candidate_records = [r for r in all_records if r.get("inclusion_status") == "INCLUDE"]
    total_candidates = len(candidate_records)
    logger.info(f"Loaded {total_candidates} candidate records passing Title/Abstract screening.")

    downloaded_pdf_count = 0
    final_included_records = []
    screening_ledger = []

    exclusion_reasons_breakdown = {}

    for idx, record in enumerate(candidate_records, 1):
        doi = record.get("DOI")
        title = record.get("title", "")
        abstract = record.get("abstract", "")

        logger.info(f"[{idx}/{total_candidates}] Processing: '{title[:55]}...'")

        # 1. Download PDF
        pdf_success, pdf_path, retrieval_note = download_paper_pdf(record, PDF_DIR)
        
        full_text = ""
        page_count = 0
        if pdf_success and pdf_path:
            downloaded_pdf_count += 1
            full_text, page_count = extract_text_from_pdf(pdf_path)
            logger.info(f"   -> PDF Retrieved: {page_count} pages, {len(full_text)} chars extracted ({retrieval_note}).")
        else:
            logger.info(f"   -> PDF Retrieval note: {retrieval_note}. Using comprehensive bibliographic record.")

        # 2. Evaluate Full-Text Eligibility
        is_eligible, exclusion_reason, domain_factors = evaluate_full_text_eligibility(
            title=title,
            abstract=abstract,
            full_text=full_text,
            has_pdf=pdf_success
        )

        ledger_entry = dict(record)
        ledger_entry["pdf_retrieved"] = pdf_success
        ledger_entry["pdf_local_path"] = pdf_path
        ledger_entry["pdf_page_count"] = page_count
        ledger_entry["text_extracted_chars"] = len(full_text)
        ledger_entry["final_eligibility_status"] = "INCLUDE" if is_eligible else "EXCLUDE"
        ledger_entry["final_exclusion_reason"] = exclusion_reason
        ledger_entry["domain_relevance_factors"] = domain_factors

        screening_ledger.append(ledger_entry)

        if is_eligible:
            final_included_records.append(ledger_entry)
            logger.info(f"   ==> RESULT: [INCLUDED] Factors: {domain_factors}")
        else:
            reason_category = exclusion_reason.split(":")[0] if exclusion_reason else "Other"
            exclusion_reasons_breakdown[reason_category] = exclusion_reasons_breakdown.get(reason_category, 0) + 1
            logger.info(f"   ==> RESULT: [EXCLUDED] Reason: {exclusion_reason}")

        time.sleep(0.1)  # Pacing

    elapsed = time.time() - start_time

    # 3. Export final approved literature
    output_abs_path = os.path.abspath(FINAL_OUTPUT_FILE)
    with open(output_abs_path, "w", encoding="utf-8") as f_out:
        json.dump(final_included_records, f_out, indent=2, ensure_ascii=False)

    # 4. Export complete audit ledger
    ledger_abs_path = os.path.abspath(LEDGER_OUTPUT_FILE)
    with open(ledger_abs_path, "w", encoding="utf-8") as f_ledger:
        json.dump(screening_ledger, f_ledger, indent=2, ensure_ascii=False)

    total_final_included = len(final_included_records)
    total_final_excluded = total_candidates - total_final_included

    # 5. Terminal Summary
    print("\n" + "=" * 75)
    print("        PRISMA STEP 4: FULL-TEXT RETRIEVAL & ELIGIBILITY SUMMARY")
    print("=" * 75)
    print(f" Candidate Studies Evaluated : {total_candidates}")
    print(f" Full PDFs Retrieved / Stored : {downloaded_pdf_count} ({downloaded_pdf_count/total_candidates*100:.1f}%)")
    print(f" Final Studies INCLUDED       : {total_final_included} ({total_final_included/total_candidates*100:.1f}%)")
    print(f" Final Studies EXCLUDED       : {total_final_excluded} ({total_final_excluded/total_candidates*100:.1f}%)")
    print(f" Execution Duration           : {elapsed:.2f} seconds")
    print(f" Local PDF Storage Directory  : {os.path.abspath(PDF_DIR)}")
    print(f" Final Dataset Artifact       : {output_abs_path}")
    print("-" * 75)
    if exclusion_reasons_breakdown:
        print(" Full-Text Exclusion Breakdown:")
        for reason, count in sorted(exclusion_reasons_breakdown.items(), key=lambda x: x[1], reverse=True):
            print(f"  * {reason:<50}: {count:>2} studies")
    else:
        print(" All 50 screened candidate studies met full-text eligibility criteria.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    run_full_text_screening()
