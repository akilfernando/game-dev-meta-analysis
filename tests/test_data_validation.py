import json
import pytest
from pathlib import Path
from pydantic import ValidationError
import sys

# Ensure scripts directory is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from validate_data import PaperEntry, QuantitativeTimeoutFindings, CrashTriageTaxonomy, validate_all_data
from generate_report import generate_markdown_report

DATA_DIR = BASE_DIR / "data"

def test_data_directory_exists_and_contains_15_files():
    assert DATA_DIR.exists() and DATA_DIR.is_dir()
    json_files = list(DATA_DIR.glob("*.json"))
    assert len(json_files) == 15, f"Expected 15 JSON files, found {len(json_files)}"

def test_validate_all_data_success():
    entries = validate_all_data(DATA_DIR)
    assert len(entries) == 15
    for entry in entries:
        assert isinstance(entry, PaperEntry)
        assert entry.id.startswith("paper_")
        assert len(entry.authors) >= 1
        assert entry.year >= 2000
        assert entry.venue in ["ICSE", "MSR", "ESEC/FSE", "EMSE", "IEEE Software"]

def test_schema_invalid_timeout_rate():
    invalid_data = {
        "id": "invalid_01",
        "title": "Test Invalid Paper",
        "authors": ["Author One"],
        "year": 2022,
        "venue": "ICSE",
        "dataset_size": "100 builds",
        "primary_methodology": "Mining",
        "quantitative_timeout_findings": {
            "ci_timeout_rate_percent": 150.0,  # Invalid: > 100%
            "avg_build_duration_minutes": 50.0,
            "asset_pipeline_overhead_percent": 40.0,
            "flaky_build_rate_percent": 10.0
        },
        "crash_triage_taxonomy": {
            "primary_categories": ["Crash"],
            "automated_triage_accuracy_percent": 80.0,
            "key_bottlenecks": ["Bottleneck"]
        }
    }
    with pytest.raises(ValidationError):
        PaperEntry.model_validate(invalid_data)

def test_generate_report_markdown():
    entries = validate_all_data(DATA_DIR)
    report_md = generate_markdown_report(entries)
    assert "# Empirical Synthesis & Quantitative Data Summary" in report_md
    assert "15 foundational empirical studies" in report_md
    assert "CI Timeout Rate (%)" in report_md
    assert "Automated Triage Accuracy (%)" in report_md
