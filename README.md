# Meta-Analysis of CI Timeouts, Build Failure Triage, and Crash Reporting in Game Software Engineering

[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

## Overview
This repository contains a structured dataset, validation tools, automated report generation scripts, and a formal academic meta-analysis report examining Continuous Integration (CI) timeouts, build failure triage, and crash reporting in game software engineering. The analysis synthesizes empirical evidence from 15 foundational papers published in leading software engineering venues (ICSE, MSR, ESEC/FSE, EMSE, IEEE Software).

## Research Methodology
We conducted a systematic meta-analysis following established guidelines for software engineering research:
1. **Primary Study Selection**: Identified 15 empirical studies published across premier venues focusing on game engines, multi-platform build matrices, asset pipeline compilation, CI flaky failures, and automated crash dump triage.
2. **Data Extraction**: Formatted qualitative and quantitative findings into structured JSON models adhering to strict Pydantic schema validation.
3. **Synthesis & Taxonomy Creation**: Aggregated metric distributions (e.g., timeout percentages, triage accuracy, build duration) and established comparative taxonomies for game CI bottlenecks and crash reporting categories.

## Repository Layout
- `data/`: JSON files containing extracted empirical metrics from 15 foundational papers.
- `scripts/validate_data.py`: Schema validator powered by Pydantic verifying data integrity.
- `scripts/generate_report.py`: Script compiling dataset metrics into Markdown summary tables and statistical aggregations.
- `content/meta-analysis-report.md`: Formal academic meta-analysis report (Abstract, Introduction, RQs, Taxonomy, Synthesis, Research Gaps, References).
- `tests/`: Pytest suite validating schema compliance and script outputs.

## Data Schema
Each JSON file in `data/` must adhere to the following schema structure:
- **`id`**: Unique string identifier (e.g., `paper_01`).
- **`title`**: Full title of the paper.
- **`authors`**: List of author names.
- **`year`**: Publication year (integer).
- **`venue`**: Conference or journal venue (e.g., ICSE, MSR, ESEC/FSE, EMSE, IEEE Software).
- **`dataset_size`**: Description or count of projects/builds/crash logs analyzed.
- **`primary_methodology`**: Primary empirical method (e.g., Mining Software Repositories, Case Study, Survey).
- **`quantitative_timeout_findings`**: Object containing:
  - `ci_timeout_rate_percent`: Percentage of build failures or runs attributed to timeouts.
  - `avg_build_duration_minutes`: Average or median CI build duration.
  - `asset_pipeline_overhead_percent`: Estimated percentage of build time spent on asset compilation/cooking.
  - `flaky_build_rate_percent`: Percentage of build failures classified as non-deterministic/flaky.
- **`crash_triage_taxonomy`**: Object containing:
  - `primary_categories`: List of crash/failure categories (e.g., Memory Leaks, GPU Driver Incompatibility, Asset Corruption, Thread Deadlocks).
  - `automated_triage_accuracy_percent`: Accuracy or F1-score of automated triage methods reported.
  - `key_bottlenecks`: List of primary operational or architectural bottlenecks identified.

## Reproduction Steps
1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Validate Data**:
   ```bash
   python scripts/validate_data.py
   ```
3. **Generate Summary Report Tables**:
   ```bash
   python scripts/generate_report.py
   ```
4. **Run Test Suite**:
   ```bash
   pytest
   ```

## License
This work and dataset are licensed under a [Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
