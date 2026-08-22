# PRISMA 2020 Flow Diagram

**Systematic Review Title**: CI Timeouts, Automated Repair, and Crash Triage in Game Development  
**Protocol Reference**: Step 1 PICOC Specification  
**Standard**: PRISMA 2020 Statement for Systematic Reviews  

```mermaid
flowchart TD
    subgraph Identification ["1. Identification"]
        A1["Records identified from databases (n = 482)<br/>• CrossRef / ACM Digital Library: 482<br/>• arXiv API: 0 (Throttled/Rate Limited)"]
        A2["Duplicates removed prior to screening (n = 0)<br/>(Strict DOI normalization applied)"]
        A1 --> A2
    end

    subgraph Screening ["2. Screening"]
        B1["Records screened via Title/Abstract (n = 482)"]
        B2["Records excluded based on PICOC rules (n = 432)<br/>• Outside target population: 246<br/>• No automated triage/repair intervention: 91<br/>• Lacks empirical baseline/comparison: 81<br/>• Lacks actionable efficiency/accuracy metrics: 14"]
        B3["Reports sought for retrieval (n = 50)"]
        A2 --> B1
        B1 -->|Fail-Fast Exclusions| B2
        B1 -->|Passed Screening| B3
    end

    subgraph Retrieval ["3. Retrieval"]
        C1["Full-text reports retrieved & stored (n = 6)"]
        C2["Reports assessed via comprehensive metadata (n = 44)<br/>(Open Access PDF unavailable / paywalled)"]
        B3 --> C1
        B3 --> C2
    end

    subgraph Eligibility ["4. Eligibility"]
        D1["Full-text reports assessed for eligibility (n = 50)"]
        D2["Full-text reports excluded with reasons (n = 22)<br/>• Lacks explicit game engine architecture, massive assets,<br/>  or non-deterministic crash triage focus: 22"]
        C1 --> D1
        C2 --> D1
        D1 -->|Domain Filters| D2
    end

    subgraph Included ["5. Included"]
        E1["Total studies included in synthesis & taxonomy (n = 28)<br/>• Automated Program Repair (APR): 24 studies (85.7%)<br/>• Crash Localization & Triage: 13 studies (46.4%)<br/>• Flaky / Non-Determinism Mitigation: 6 studies (21.4%)<br/>• CI Scheduler Optimization: 3 studies (10.7%)"]
        D1 -->|Approved Studies| E1
    end

    classDef stage fill:#f8f9fa,stroke:#343a40,stroke-width:2px;
    classDef box fill:#e9ecef,stroke:#495057,stroke-width:1px;
    classDef highlight fill:#d4edda,stroke:#28a745,stroke-width:2px;
    classDef exclude fill:#f8d7da,stroke:#dc3545,stroke-width:1px;

    class A1,A2,B1,B3,C1,C2,D1 box;
    class B2,D2 exclude;
    class E1 highlight;
```

---

## Phase-by-Phase Numerical Breakdown

| PRISMA 2020 Phase | Stage Description | Record Count | Percentage |
| :--- | :--- | :---: | :---: |
| **Identification** | Records harvested from primary academic APIs (CrossRef / ACM, arXiv) | **482** | 100.0% |
| **Deduplication** | Strict lowercase DOI-based deduplication | **482** | 100.0% |
| **Title/Abstract Screening** | Records screened against strict PICOC rules | **482** | 100.0% |
| | *Excluded at Title/Abstract level (Fail-Fast)* | *432* | *89.6%* |
| | *Candidate records passed to Full-Text phase* | *50* | *10.4%* |
| **Full-Text Retrieval** | Full-text PDFs downloaded & stored in local repository (`full_text_pdfs/`) | **6** | 12.0% |
| | Comprehensive bibliographic records assessed | **44** | 88.0% |
| **Eligibility Assessment** | Full texts evaluated for game engine architecture, massive assets, & crash triage | **50** | 100.0% |
| | *Excluded due to lack of domain-specific relevance (generic APR)* | *22* | *44.0%* |
| **Included Studies** | **Final approved studies synthesized in Taxonomy Matrix** | **28** | **5.8%** |
