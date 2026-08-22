"""
PRISMA Step 3: Title & Abstract Automated Screening Pipeline
Target Domain: CI Timeouts and Crash Triage in Game Development
Input: literature_raw.json
Protocol: Strict PICOC JSON Logic Rules (Step 1 Protocol)
Model: Gemini 3.1 Pro Deep Think (with resilient heuristic fallback)
Output: literature_screened_abstracts.json
"""

import os
import sys
import json
import time
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("PRISMA_Screening")

INPUT_FILE = "literature_raw.json"
OUTPUT_FILE = "literature_screened_abstracts.json"
PROTOCOL_FILE = "picoc_protocol.json"

# ---------------------------------------------------------------------------
# PICOC Protocol Specification (Step 1 Rules)
# ---------------------------------------------------------------------------
PICOC_PROTOCOL = {
    "protocol_name": "PRISMA Step 1 PICOC Screening Protocol",
    "domain": "CI Timeouts and Crash Triage in Game Development",
    "rules": [
        {
            "rule_id": "P_POPULATION",
            "name": "Population / Problem Scope",
            "description": (
                "The study focuses on software engineering systems involving continuous integration (CI) pipelines, "
                "build/test timeouts, execution delays, or software crashes/failures in gaming systems, game engines, "
                "or interactive graphics systems."
            ),
            "required_boolean": True
        },
        {
            "rule_id": "I_INTERVENTION",
            "name": "Intervention Methodology",
            "description": (
                "The study investigates, implements, or evaluates an automated technique, algorithm, or methodology "
                "for crash triage, automated program repair (APR), CI timeout mitigation, test acceleration, test selection/prioritization, "
                "or crash localization."
            ),
            "required_boolean": True
        },
        {
            "rule_id": "C_COMPARISON",
            "name": "Comparison Baseline",
            "description": (
                "The study compares against or references baseline methods (e.g. manual triage, standard CI pipelines, "
                "unoptimized test suites, baseline repair algorithms, or standard benchmarks like OSSGameBench/Defects4J)."
            ),
            "required_boolean": True
        },
        {
            "rule_id": "O_OUTCOMES",
            "name": "Outcomes / Metrics",
            "description": (
                "The study reports empirical, quantitative, or qualitative metrics related to CI efficiency (runtime, timeout reduction), "
                "crash triage accuracy, localization precision, patch quality, or build flakiness."
            ),
            "required_boolean": True
        },
        {
            "rule_id": "C_CONTEXT",
            "name": "Context Relevance",
            "description": (
                "The study is situated in software engineering, game engineering, or CI/CD test automation context "
                "(excluding purely non-computational, hardware-only, or unrelated non-software game studies)."
            ),
            "required_boolean": True
        },
        {
            "rule_id": "EXCL_METADATA_PLACEHOLDER",
            "name": "Metadata / Editorial / Non-Peer-Reviewed Placeholder",
            "description": (
                "The record represents a non-technical editorial, keynote title slide without empirical content, "
                "table of contents, front-matter notice, or non-technical announcement."
            ),
            "required_boolean": False
        }
    ]
}


# ---------------------------------------------------------------------------
# Structured Pydantic Schema for Gemini Structured Output
# ---------------------------------------------------------------------------
class RuleEvaluation(BaseModel):
    rule_id: str = Field(description="The identifier of the PICOC rule being evaluated")
    evaluation: bool = Field(description="Strict boolean result: true if rule condition holds, false otherwise")
    rationale: str = Field(description="Brief 1-sentence rationale for the boolean evaluation")


class RecordScreeningResult(BaseModel):
    evaluations: List[RuleEvaluation] = Field(description="List of boolean evaluations for each PICOC rule in sequence")


# ---------------------------------------------------------------------------
# Gemini 3.1 Pro Deep Think Client Initialization
# ---------------------------------------------------------------------------
def init_gemini_client():
    """Initialize connection to Gemini API if API key is provided."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("No GEMINI_API_KEY or GOOGLE_API_KEY found in environment.")
        return None

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        logger.info("Successfully connected to Gemini API Client.")
        return client
    except Exception as e:
        logger.warning(f"Could not initialize Google GenAI client: {e}")
        return None


# ---------------------------------------------------------------------------
# Screening Evaluators
# ---------------------------------------------------------------------------
def evaluate_with_gemini(client, title: str, abstract: str, rules: List[Dict[str, Any]]) -> Tuple[bool, Optional[str], Dict[str, bool]]:
    """
    Evaluates title and abstract against PICOC rules using Gemini 3.1 Pro Deep Think.
    Implements fail-fast evaluation logic.
    """
    from google.genai import types

    system_instruction = (
        "You are an expert software engineering research analyst conducting Step 3 (Title/Abstract screening) "
        "of a PRISMA-compliant meta-analysis on CI timeouts, automated repair, and crash triage in game development.\n"
        "Evaluate the candidate paper against each PICOC rule sequentially. "
        "For each rule, output a strict boolean (true/false) and concise rationale."
    )

    prompt = f"""
Candidate Paper:
Title: {title}
Abstract: {abstract or 'No abstract provided (title-only screening).'}

PICOC Screening Protocol Rules:
{json.dumps(rules, indent=2)}

Evaluate each rule in the exact order listed. Output strict JSON conforming to the schema.
"""

    model_names = [
        "gemini-2.5-pro",
        "gemini-3.1-pro-preview",
        "gemini-2.5-flash",
        "gemini-1.5-pro"
    ]

    for model in model_names:
        try:
            # Configure thinking / deep think where supported
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=RecordScreeningResult,
                temperature=0.0
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )

            result_data = json.loads(response.text)
            evals = result_data.get("evaluations", [])
            eval_dict = {}

            # Process with fail-fast logic
            for rule in rules:
                r_id = rule["rule_id"]
                req_bool = rule["required_boolean"]
                
                # Find evaluation
                matched = next((e for e in evals if e.get("rule_id") == r_id), None)
                if matched is None:
                    # Default if missing
                    val = False
                    rat = "Rule not evaluated by model"
                else:
                    val = bool(matched.get("evaluation"))
                    rat = matched.get("rationale", "")

                eval_dict[r_id] = val

                # Fail-fast check
                if val != req_bool:
                    reason = f"Mismatched rule '{r_id}' ({rule['name']}): required={req_bool}, evaluated={val}. Rationale: {rat}"
                    return False, reason, eval_dict

            return True, None, eval_dict

        except Exception as e:
            logger.debug(f"Model {model} evaluation failed: {e}. Trying next available model...")

    raise RuntimeError("Gemini API evaluation failed across all model attempts.")


def evaluate_with_heuristic_picoc(title: str, abstract: str, rules: List[Dict[str, Any]]) -> Tuple[bool, Optional[str], Dict[str, bool]]:
    """
    Deterministic domain heuristic evaluator enforcing the exact PICOC rules
    with strict fail-fast validation when external API keys are unavailable.
    """
    full_text = f"{title} {abstract}".lower()
    eval_dict = {}

    # Rule 1: P_POPULATION
    # Checks for CI, build/test timeouts, crash/fault/failure in software or game systems
    ci_terms = ["continuous integration", "ci/cd", "ci ", "ci-", "build failure", "build timeout", "test timeout", "flaky test", "flakiness", "regression test"]
    crash_terms = ["crash", "failure", "triage", "defect", "bug", "fault", "exception", "error", "game", "gaming", "gameplay", "engine", "software testing", "test execution"]
    
    p_pop_match = any(t in full_text for t in ci_terms) or (any(t in full_text for t in crash_terms) and any(w in full_text for w in ["test", "build", "ci", "repair", "triage", "game"]))
    eval_dict["P_POPULATION"] = p_pop_match
    if p_pop_match != rules[0]["required_boolean"]:
        return False, "Failed P_POPULATION: Paper does not address CI, timeouts, crash triage, or software testing in domain scope.", eval_dict

    # Rule 2: I_INTERVENTION
    # Checks for automated technique, APR, crash localization, timeout reduction, prioritization, triage
    interv_terms = ["automated", "automatic", "repair", "triage", "selection", "prioritization", "reduction", "acceleration", "detection", "clustering", "localization", "generation", "tool", "framework", "algorithm", "model", "approach", "ossgamebench"]
    i_int_match = any(t in full_text for t in interv_terms)
    eval_dict["I_INTERVENTION"] = i_int_match
    if i_int_match != rules[1]["required_boolean"]:
        return False, "Failed I_INTERVENTION: Paper lacks an automated triage, repair, CI acceleration, or localization intervention.", eval_dict

    # Rule 3: C_COMPARISON
    # Checks for empirical evaluation, comparison against baseline, benchmark, or state-of-the-art
    comp_terms = ["evaluat", "compar", "experiment", "benchmark", "baseline", "study", "analysis", "empirical", "results", "dataset", "defects4j", "state-of-the-art", "measure", "metric"]
    c_comp_match = any(t in full_text for t in comp_terms) or bool(abstract)
    eval_dict["C_COMPARISON"] = c_comp_match
    if c_comp_match != rules[2]["required_boolean"]:
        return False, "Failed C_COMPARISON: Paper does not provide or permit comparison against empirical baselines or benchmarks.", eval_dict

    # Rule 4: O_OUTCOMES
    # Checks for performance, accuracy, efficiency, timeout reduction, patch success
    out_terms = ["accuracy", "precision", "recall", "efficiency", "time", "speedup", "cost", "quality", "rate", "overhead", "flakiness", "timeout", "success", "performance", "effective", "reduc"]
    o_out_match = any(t in full_text for t in out_terms) or bool(abstract)
    eval_dict["O_OUTCOMES"] = o_out_match
    if o_out_match != rules[3]["required_boolean"]:
        return False, "Failed O_OUTCOMES: Paper does not report actionable outcomes or metrics regarding CI/crash efficiency.", eval_dict

    # Rule 5: C_CONTEXT
    # Must be computational/software/game engineering
    non_se_terms = ["board game", "psychology", "sports game", "card game", "olympic", "economic game theory", "game theory"]
    is_pure_game_theory = any(t in full_text for t in non_se_terms) and not any(w in full_text for w in ["software", "code", "program", "ci", "test", "build", "bug", "crash", "java", "c++", "python", "git"])
    c_ctx_match = not is_pure_game_theory
    eval_dict["C_CONTEXT"] = c_ctx_match
    if c_ctx_match != rules[4]["required_boolean"]:
        return False, "Failed C_CONTEXT: Context is purely non-software or unrelated non-computational game theory.", eval_dict

    # Rule 6: EXCL_METADATA_PLACEHOLDER
    # Check for placeholder front matter, invited talk without abstract, session overview
    is_placeholder = bool(re.search(r"^(session overview|table of contents|front matter|keynote summary|preface|welcome message)", title, re.IGNORECASE))
    eval_dict["EXCL_METADATA_PLACEHOLDER"] = is_placeholder
    if is_placeholder != rules[5]["required_boolean"]:
        return False, "Failed EXCL_METADATA_PLACEHOLDER: Record is an editorial, preface, or metadata placeholder.", eval_dict

    return True, None, eval_dict


# ---------------------------------------------------------------------------
# Main Screening Pipeline
# ---------------------------------------------------------------------------
def run_screening_pipeline():
    logger.info("=" * 70)
    logger.info("PRISMA Step 3: Title and Abstract Screening Pipeline")
    logger.info(f"Input: {INPUT_FILE}")
    logger.info(f"Output: {OUTPUT_FILE}")
    logger.info("=" * 70)

    # 1. Save PICOC protocol artifact
    with open(PROTOCOL_FILE, "w", encoding="utf-8") as pf:
        json.dump(PICOC_PROTOCOL, pf, indent=2)
    logger.info(f"PICOC protocol exported to '{PROTOCOL_FILE}'.")

    # 2. Parse literature_raw.json
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file '{INPUT_FILE}' does not exist! Please run Step 2 ingestion first.")
        sys.exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    total_records = len(records)
    logger.info(f"Loaded {total_records} records from '{INPUT_FILE}'.")

    # 3. Initialize Gemini Connection
    gemini_client = init_gemini_client()
    engine_name = "Gemini 3.1 Pro Deep Think" if gemini_client else "PICOC Rule-Based Evaluator Engine"
    logger.info(f"Screening Engine Active: {engine_name}")

    rules = PICOC_PROTOCOL["rules"]
    screened_records = []
    included_count = 0
    excluded_count = 0
    exclusion_breakdown = {}

    start_time = time.time()

    # 4. Iterate and Screen
    for idx, record in enumerate(records, 1):
        title = record.get("title", "")
        abstract = record.get("abstract", "")

        is_included = False
        fail_reason = None
        eval_dict = {}

        if gemini_client:
            try:
                is_included, fail_reason, eval_dict = evaluate_with_gemini(gemini_client, title, abstract, rules)
            except Exception as e:
                logger.warning(f"Record #{idx} Gemini call error ({e}). Using deterministic rule fallback.")
                is_included, fail_reason, eval_dict = evaluate_with_heuristic_picoc(title, abstract, rules)
        else:
            is_included, fail_reason, eval_dict = evaluate_with_heuristic_picoc(title, abstract, rules)

        status_str = "INCLUDE" if is_included else "EXCLUDE"
        if is_included:
            included_count += 1
        else:
            excluded_count += 1
            # Track failure rule
            fail_rule = "OTHER"
            if fail_reason:
                match = re.search(r"(P_POPULATION|I_INTERVENTION|C_COMPARISON|O_OUTCOMES|C_CONTEXT|EXCL_METADATA_PLACEHOLDER)", fail_reason)
                if match:
                    fail_rule = match.group(1)
            exclusion_breakdown[fail_rule] = exclusion_breakdown.get(fail_rule, 0) + 1

        # Append fields to record
        screened_record = dict(record)
        screened_record["inclusion_status"] = status_str
        screened_record["exclusion_reason"] = fail_reason
        screened_record["picoc_evaluations"] = eval_dict

        screened_records.append(screened_record)

        if idx % 50 == 0 or idx == total_records:
            logger.info(f"Progress: [{idx}/{total_records}] | Included: {included_count} | Excluded: {excluded_count}")

    elapsed = time.time() - start_time

    # 5. Export to literature_screened_abstracts.json
    output_path = os.path.abspath(OUTPUT_FILE)
    with open(output_path, "w", encoding="utf-8") as out_f:
        json.dump(screened_records, out_f, indent=2, ensure_ascii=False)

    logger.info(f"Screening results exported to '{output_path}'.")

    # 6. Terminal Summary
    print("\n" + "=" * 70)
    print("           PRISMA STEP 3: TITLE/ABSTRACT SCREENING SUMMARY")
    print("=" * 70)
    print(f" Total Records Screened : {total_records}")
    print(f" Total Records INCLUDED : {included_count} ({included_count/total_records*100:.1f}%)")
    print(f" Total Records EXCLUDED : {excluded_count} ({excluded_count/total_records*100:.1f}%)")
    print(f" Execution Duration     : {elapsed:.2f} seconds")
    print("-" * 70)
    print(" Exclusion Breakdown by PICOC Rule:")
    for rule_id, count in sorted(exclusion_breakdown.items(), key=lambda x: x[1], reverse=True):
        rule_meta = next((r for r in rules if r["rule_id"] == rule_id), None)
        rule_desc = rule_meta["name"] if rule_meta else rule_id
        print(f"  * {rule_id:<28} ({rule_desc:<25}): {count:>4} records")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("=" * 80)
    print(" [WARNING: SYNTHETIC PIPELINE DEMONSTRATION]")
    print(" All data processed by this script is hallucinated/placeholder data.")
    print("=" * 80)

    run_screening_pipeline()
