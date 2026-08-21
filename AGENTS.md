# Agent Instructions & Project Guidelines

This repository hosts an academic meta-analysis dataset and toolchain examining Continuous Integration (CI) timeouts, build failure triage, and crash reporting in game software engineering.

## Environment Requirements
- **Python Version**: Python 3.11+
- **Dependencies**: Managed via `requirements.txt` (`pydantic`, `pytest`).

## Setup Instructions
```bash
pip install -r requirements.txt
```

## Validation & Testing Commands
To validate the JSON dataset against Pydantic schema models:
```bash
python scripts/validate_data.py
```

To run report generation:
```bash
python scripts/generate_report.py
```

To run the Pytest test suite:
```bash
pytest
```

## Code Quality & Standards
- Ensure all dataset files in `data/` conform strict to the schema models defined in `scripts/validate_data.py`.
- Maintain clean, modular Python code with type hints.
