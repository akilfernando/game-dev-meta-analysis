import os
import sys
import statistics
from pathlib import Path
from validate_data import validate_all_data, PaperEntry

def generate_markdown_report(entries: list[PaperEntry]) -> str:
    lines = []
    lines.append("# Empirical Synthesis & Quantitative Data Summary")
    lines.append("")
    lines.append(f"This summary aggregates findings from **{len(entries)} foundational empirical studies** in game continuous integration and failure triage.")
    lines.append("")

    # Statistical Summaries
    timeout_rates = [e.quantitative_timeout_findings.ci_timeout_rate_percent for e in entries]
    build_durations = [e.quantitative_timeout_findings.avg_build_duration_minutes for e in entries]
    asset_overheads = [e.quantitative_timeout_findings.asset_pipeline_overhead_percent for e in entries]
    flaky_rates = [e.quantitative_timeout_findings.flaky_build_rate_percent for e in entries]
    triage_accuracies = [e.crash_triage_taxonomy.automated_triage_accuracy_percent for e in entries]

    lines.append("## Statistical Aggregations")
    lines.append("")
    lines.append("| Metric | Mean | Median | Min | Max | Std Dev |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    lines.append(f"| **CI Timeout Rate (%)** | {statistics.mean(timeout_rates):.2f}% | {statistics.median(timeout_rates):.2f}% | {min(timeout_rates):.2f}% | {max(timeout_rates):.2f}% | {statistics.stdev(timeout_rates):.2f}% |")
    lines.append(f"| **Avg Build Duration (min)** | {statistics.mean(build_durations):.2f} | {statistics.median(build_durations):.2f} | {min(build_durations):.2f} | {max(build_durations):.2f} | {statistics.stdev(build_durations):.2f} |")
    lines.append(f"| **Asset Pipeline Overhead (%)** | {statistics.mean(asset_overheads):.2f}% | {statistics.median(asset_overheads):.2f}% | {min(asset_overheads):.2f}% | {max(asset_overheads):.2f}% | {statistics.stdev(asset_overheads):.2f}% |")
    lines.append(f"| **Flaky Build Rate (%)** | {statistics.mean(flaky_rates):.2f}% | {statistics.median(flaky_rates):.2f}% | {min(flaky_rates):.2f}% | {max(flaky_rates):.2f}% | {statistics.stdev(flaky_rates):.2f}% |")
    lines.append(f"| **Automated Triage Accuracy (%)** | {statistics.mean(triage_accuracies):.2f}% | {statistics.median(triage_accuracies):.2f}% | {min(triage_accuracies):.2f}% | {max(triage_accuracies):.2f}% | {statistics.stdev(triage_accuracies):.2f}% |")
    lines.append("")

    # Distribution by Venue
    venue_counts = {}
    for e in entries:
        venue_counts[e.venue] = venue_counts.get(e.venue, 0) + 1

    lines.append("## Distribution by Publication Venue")
    lines.append("")
    lines.append("| Venue | Paper Count | Percentage |")
    lines.append("| :--- | :---: | :---: |")
    for venue, count in sorted(venue_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(entries)) * 100
        lines.append(f"| **{venue}** | {count} | {pct:.1f}% |")
    lines.append("")

    # Primary Methodologies
    methodology_counts = {}
    for e in entries:
        methodology_counts[e.primary_methodology] = methodology_counts.get(e.primary_methodology, 0) + 1

    lines.append("## Distribution by Primary Research Methodology")
    lines.append("")
    lines.append("| Methodology | Paper Count |")
    lines.append("| :--- | :---: |")
    for meth, count in sorted(methodology_counts.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"| {meth} | {count} |")
    lines.append("")

    # Comparative Summary Table of All Studies
    lines.append("## Comparative Paper Summary Table")
    lines.append("")
    lines.append("| ID | Title | Authors | Year | Venue | Dataset Size | Timeout Rate | Avg Duration | Triage Accuracy |")
    lines.append("| :--- | :--- | :--- | :---: | :---: | :--- | :---: | :---: | :---: |")
    for e in entries:
        authors_str = ", ".join(e.authors)
        if len(authors_str) > 30:
            authors_str = authors_str[:27] + "..."
        title_str = e.title if len(e.title) <= 45 else e.title[:42] + "..."
        lines.append(
            f"| `{e.id}` | {title_str} | {authors_str} | {e.year} | {e.venue} | {e.dataset_size} | "
            f"{e.quantitative_timeout_findings.ci_timeout_rate_percent:.1f}% | {e.quantitative_timeout_findings.avg_build_duration_minutes:.1f}m | "
            f"{e.crash_triage_taxonomy.automated_triage_accuracy_percent:.1f}% |"
        )
    lines.append("")

    # Taxonomy Matrix
    lines.append("## Comparative Taxonomy & Key Bottlenecks")
    lines.append("")
    for e in entries:
        lines.append(f"### {e.id}: {e.title}")
        lines.append(f"- **Primary Triage Categories**: {', '.join(e.crash_triage_taxonomy.primary_categories)}")
        lines.append(f"- **Key Bottlenecks**: {', '.join(e.crash_triage_taxonomy.key_bottlenecks)}")
        lines.append("")

    return "\n".join(lines)

def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    sys.path.insert(0, str(base_dir / "scripts"))

    entries = validate_all_data(data_dir)
    report_md = generate_markdown_report(entries)

    output_file = base_dir / "data" / "summary_report.md"
    output_file.write_text(report_md, encoding="utf-8")
    print(f"Generated statistical summary report at {output_file}")

if __name__ == "__main__":
    main()
