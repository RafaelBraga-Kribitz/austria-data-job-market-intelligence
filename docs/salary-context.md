# Salary context: third-party references (kept separate from posting evidence)

The posting-level salary statistics in `outputs/tables/T09*` are **advertised minimums** (Austrian ads must state the collective-agreement minimum, and most state only that) converted to annual gross with the 14-payment convention. They are not offers and not survey medians. The references below are the only external Austrian figures verified by fetching the page on 2026-09-16; each is labelled by what it measures. Numbers were copied from the fetched pages stored under `data/external/salary_references/`.

| Reference | What it measures | Figure (as published) | Annualised (×14) | Verified | Use |
|---|---|---|---|---|---|
| AMS Berufslexikon, "Data Scientist" (berufslexikon.at/berufe/3852-DataScientist/) | Collective-agreement based **entry** salary range, monthly gross, Stand 2025 | € 2,800 – € 4,350 / month | ≈ € 39,200 – € 60,900 | Yes (page fetched) | Official floor for entry-level; not a market median |
| karriere.at Gehalt page "Analyst*in in Österreich" (karriere.at/gehalt/analyst) | karriere.at internal data (method not disclosed on page), monthly gross range shown for the generic "Analyst" occupation | € 2,640 – € 4,400 / month (page also shows "ab 26,000 € jährlich" / "ab 60,000 € jährlich" bands) | ≈ € 37,000 – € 61,600 | Yes (page fetched) | Generic "Analyst", not data-specific; Bundesland breakdown only via interactive form |
| Hays Austria job profile "Data Scientist" (hays.at/jobprofile/data-scientist) | Recruiter's stated averages, annual gross, undated, no sample | ≈ € 54,800 average; junior ≈ € 50,000; senior (10+ yrs) from € 70,000 | – | Fetched by the research agent (see docs/research-landscape.md) | Indicative only; no methodology |
| StepStone Gehaltsreport 2025 (AT) | Employer/employee survey report | not verified (fetch timed out; role pages on stepstone.at redirect to German data) | – | No | Do not cite until the AT PDF is obtained |
| Glassdoor AT | Self-reported | not verified (403) | – | No | Do not cite |
| Statistik Austria Verdienststrukturerhebung 2022 | Official earnings by ISCO-08 2-digit (e.g. 25 ICT professionals), NUTS-1 in open data | see docs/research-landscape.md | – | Partially | Too coarse for data roles |

## How to read our posting-level figures against these

* Our median advertised **minimum** for core data roles (T09b) should sit close to the collective-agreement entry bands above for junior/unspecified postings and above them for senior postings. If it does, the parser is behaving; if a family median is far below € 35,000, suspect part-time or parsing artefacts (check `salary_snippet` in T09e).
* "Überzahlung möglich" (willingness to pay above the minimum) is flagged in `salary_overpay_mention`; it signals that the stated figure is a floor.
* Ranges (`salary_basis = range`) are the only advertised figures that approximate an offer band; their upper ends are reported separately (`max_median`).
* Third-party medians (Hays, StepStone) are typically 20–40% above collective-agreement floors; do not mix them with T09 tables.

Regenerate this file's posting-side comparison after each pipeline run; the reference rows only change when a new report is fetched and stored.
