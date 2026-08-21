import sys
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field, ValidationError

class QuantitativeTimeoutFindings(BaseModel):
    ci_timeout_rate_percent: float = Field(..., ge=0.0, le=100.0)
    avg_build_duration_minutes: float = Field(..., gt=0.0)
    asset_pipeline_overhead_percent: float = Field(..., ge=0.0, le=100.0)
    flaky_build_rate_percent: float = Field(..., ge=0.0, le=100.0)

class CrashTriageTaxonomy(BaseModel):
    primary_categories: List[str] = Field(..., min_length=1)
    automated_triage_accuracy_percent: float = Field(..., ge=0.0, le=100.0)
    key_bottlenecks: List[str] = Field(..., min_length=1)

class PaperEntry(BaseModel):
    id: str = Field(...)
    title: str = Field(...)
    authors: List[str] = Field(..., min_length=1)
    year: int = Field(..., ge=2000, le=2030)
    venue: str = Field(...)
    dataset_size: str = Field(...)
    primary_methodology: str = Field(...)
    quantitative_timeout_findings: QuantitativeTimeoutFindings
    crash_triage_taxonomy: CrashTriageTaxonomy

def validate_all_data(data_dir: Path) -> List[PaperEntry]:
    json_files = list(data_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found in {data_dir}")

    entries = []
    errors = []

    for file_path in sorted(json_files):
        try:
            content = file_path.read_text(encoding="utf-8")
            entry = PaperEntry.model_validate_json(content)
            entries.append(entry)
            print(f"✓ Validated: {file_path.name}")
        except ValidationError as ve:
            errors.append((file_path.name, str(ve)))
        except Exception as e:
            errors.append((file_path.name, str(e)))

    if errors:
        print("\n❌ Validation failed for the following file(s):", file=sys.stderr)
        for filename, err in errors:
            print(f" - {filename}: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"\nSuccessfully validated {len(entries)} paper entries.")
    return entries

if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    data_directory = base_dir / "data"
    validate_all_data(data_directory)
