# Question-coverage audit: the two original briefs against the visual decision layer

**Purpose.** The two briefs that created this project (the publication/completeness/legal audit brief, and the candidate-supply and demand × supply brief) asked, between them, a large number of distinct questions. This document contrasts **every question either brief asked** with what the project can now answer, and says where the answer lives.

**How to read the status column.**

| Status | Meaning |
|---|---|
| **VISUAL** | Answered by a figure in the visual decision layer, attached to the passage it answers (`docs/visual-decision-board.md`) |
| **TEXT** | Answered in the documents and tables, but the question is not chart-shaped — an audit finding, a legal analysis or a definition. A chart would add nothing |
| **PARTIAL** | Answered for part of its scope; the remainder is registered in `docs/open-questions.md` |
| **OPEN** | Not answerable with the data this project holds. Registered in `docs/open-questions.md` with what is missing and what would close it |

**Rule applied throughout.** A question is only marked VISUAL if the figure answers *that* question, not a neighbouring one. Where a brief asked for a dimension that the data cannot support, the honest answer is OPEN, not a chart of something adjacent.

Added 2026-09-21 (DECISION_LOG D-025). Nothing in this audit changed a number, a taxonomy or a conclusion; it added figures and registered gaps.

---

## Part 1 — Brief 1: publication, completeness and legal audit

### §4-§5 Completeness and sceptical verification

| Question from the brief | Status | Where |
|---|---|---|
| Was every requirement of the original specification actually fulfilled? | TEXT | `docs/original-specification-audit.md` (requirement-by-requirement, with status and evidence) |
| Are the reported counts reproducible against the repository? | VISUAL | **BQ27** population funnel; `outputs/reports/digest.txt` prints every quoted figure. One disagreement found: the Styrian bio-declared denominator is 52 in one table and 56 in three others → **OQ-19**, closed by D-027 (56 canonical; 52 = frame-B subset) |
| Are duplicates correctly handled; what is the duplicate rate? | VISUAL | **BQ27** (source line carries the in-scope duplicate rate); `Q04`, `dedupe_summary` |
| Are cross-posted jobs identified; do sources overlap? | VISUAL | **BQ30** source coverage (20 % of core postings seen on more than one source) |
| Are reposts distinguished from separate vacancies? | TEXT | `Q04a_reposts.csv`; 51 of 761 company+title pairs carry multiple ids on one source |
| Are recruitment-agency postings identified? | VISUAL | **BQ33** employer structure (agencies are 4.5 % of named postings) |
| Are stale postings handled? | VISUAL | **BQ31** posting freshness by source |
| Does title normalisation create false positives? | VISUAL | **BQ28** classification precision per family, before and after the D-012 audit |
| What is the *recall* of the title taxonomy? | OPEN | **OQ-09** — only precision was ever measured |
| Is the skill vocabulary complete (aliases, German compounds, product names)? | PARTIAL | `Q09`, `SQ07`, D-012/D-021 revisions; residual false-negative rate unmeasured → **OQ-16** |

### §6-§8 Denominators, snapshot vs flow, small samples

| Question | Status | Where |
|---|---|---|
| "33 % of what?" — what is the denominator of every frequency claim? | VISUAL | **BQ27** — the funnel from 12,429 rows to the 720/719 denominators |
| Is a one-day stock ever presented as annual demand, vacancies or hires? | VISUAL | **BQ02** (official yearly flow, separately sourced and labelled) + **BQ27**; wording audited in `docs/methodology.md` §5 |
| Which Styrian percentages rest on cells too small to carry them? | VISUAL | **BQ29** Styrian cell sizes against the n = 30 rule |

### §9-§13 Language, salary, education, technology, co-occurrence

| Question | Status | Where |
|---|---|---|
| Does the project distinguish German required / preferred / mentioned / level / silent? | VISUAL | **BQ12** addressable scenarios, **BQ34** level distribution |
| Which German level is actually demanded when one is stated? | VISUAL | **BQ34** |
| Is "English-only" conflated with "written in English"? | VISUAL | **BQ12** — three explicitly separated readings, never one number |
| Are legal minimum, advertised range and actual compensation distinguished? | VISUAL | **BQ32** what a salary figure actually is; **BQ15-BQ17** are labelled advertised floors throughout |
| What is actual (not advertised) compensation? | OPEN | **OQ-05** |
| Does a stated skill premium survive the obvious confounders? | VISUAL | **BQ45** — OLS with controls; 14 of 16 premiums vanish |
| Are degree levels and fields distinguished as required / preferred / mentioned? | VISUAL | **BQ14** degree requirement strength by family |
| Are certifications rare, or merely rarely extracted? | VISUAL | **BQ36** — both sides, after the vocabulary was extended with exam codes |
| Are technologies, frameworks and libraries genuinely separate dimensions? | VISUAL | **BQ35** — they are separate vocabularies, and the library layer barely appears in ads |
| Are recurring technology combinations identified, not just rankings? | VISUAL | **BQ10** co-occurrence matrix; `T06b` three-item stacks |

### §14-§17 Career fit, the German lever, coverage, employers

| Question | Status | Where |
|---|---|---|
| Is the "87 % skill overlap" claim traceable and honestly bounded? | VISUAL | **BQ05** — overlap plotted against market size, with the n < 30 rule applied and the self-declared basis stated |
| Is the family ranking an artefact of the weighting? | VISUAL | **BQ07** rank stability across four weightings |
| Does German proficiency *cause* better hiring outcomes? | OPEN | **OQ-01** — the dataset measures stated requirements, never outcomes |
| How much does German change the *addressable set* (not the outcome)? | VISUAL | **BQ12**, **BQ34** |
| What portion of the Austrian market is invisible to this dataset? | PARTIAL | **BQ30** names what is missing and why; the size of the gap is **OQ-03** |
| Are additional high-value sources available? | TEXT | `docs/data-sources.md` (tiers, status, terms); blocked and unattempted sources listed |
| How concentrated are employers; what does "387 named employers" mean? | VISUAL | **BQ33** — named vs represented, concentration, agencies, anonymous rows |
| Which Styrian employers actually advertise? | VISUAL | **BQ04** |

### §18-§34 Legal, privacy, database rights, terms, publication

Every question in this block is an evidence-gathering and risk-classification task whose answer is a documented analysis, not a measurement. None of them is chart-shaped, and none is marked VISUAL for that reason.

| Question | Status | Where |
|---|---|---|
| Does the dataset contain personal data under GDPR, including indirectly identifiable data? | TEXT | `docs/legal-and-publication-audit.md` §3-§5, §10; `docs/data-quality.md` §10 |
| Does publishing differ from collecting? | TEXT | `docs/legal-and-publication-audit.md` §7; `PUBLICATION_DECISION.md` |
| Do sui generis database rights apply to the sources? | TEXT | `docs/legal-and-publication-audit.md` §4 |
| Does retaining or publishing full job descriptions create copyright exposure? | TEXT | same, §5; enforced by `src/publish/export_public.py` (free-text columns abort the export) |
| What do the platforms' terms actually say, clause by clause? | TEXT | `docs/data-sources.md` and `docs/legal-and-publication-audit.md` §2/§6 (quoted clauses, fetch dates) |
| Does a TDM exception authorise republication? | TEXT | `docs/legal-and-publication-audit.md` §8 — analysed and *not* relied on for republication |
| What is the source-by-source publication matrix and the risk model? | TEXT | `docs/legal-and-publication-audit.md` §9; `PUBLICATION_DECISION.md` |
| Are there secrets or personal data in the tree or git history? | TEXT | publication scan in `src/publish/export_public.py`; the export aborts on an e-mail, phone number or free-text column |
| Could a rights-holder be asked for a research licence instead? | OPEN | **OQ-17** — never attempted |

### §35-§47 Credibility, agent context, decision map, final report

| Question | Status | Where |
|---|---|---|
| Can a sceptical reader audit methodology, provenance, limitations and conclusions? | TEXT | `README.md`, `docs/methodology.md`, `docs/limitations.md`; the visual layer now carries n, units, source and caveat on every figure |
| Can an agent retrieve the key facts without reading everything? | TEXT | `AGENT_CONTEXT.md`; `outputs/visual_questions.json` maps question → answer → chart → tables |
| Does the decision map state what would change it? | TEXT | `CAREER_DECISION_MAP.md` "What would change this map?"; `CAREER_SUPPLY_DEMAND_MAP.md` equivalent |

---

## Part 2 — Brief 2: candidate supply and demand × supply

### §4-§8 Population, titles, seniority, geography, language

| Question | Status | Where |
|---|---|---|
| How large is the observable candidate population per role family? | VISUAL | **BQ20** candidate density per posting; `C04`, `DS01` |
| What titles do candidates use, and how fragmented is that vocabulary? | VISUAL | **BQ39** — 574 raw self-descriptions collapse to 13 normalised titles |
| How senior is the observable pool against advertised seniority? | VISUAL | **BQ25** |
| Do titles match experience (title-to-experience mismatch)? | OPEN | **OQ-11** — years of experience are not observable on GitHub |
| Where is candidate supply located, against where demand is? | VISUAL | **BQ37** (with the frame caveat: only Styria is a complete frame) |
| What German/English capability does the candidate pool hold? | OPEN | **OQ-02** — 99 % of bios are English; proficiency is not observable in public code |
| What is the English-only addressable market *intersection* (demand × supply)? | OPEN | **OQ-02** — the demand side is measured (**BQ12**), the supply side is not |

### §9-§12 Technologies, capabilities, education, certifications

| Question | Status | Where |
|---|---|---|
| Which technologies are prevalent among candidates? | VISUAL | **BQ22** crowded vs scarce |
| Are capabilities distinguished from tools, and evidence strength from mention? | VISUAL | **BQ21** — demand against *project-demonstrated* evidence, with observability marked |
| How does candidate education compare with employer requirements? | VISUAL | **BQ38** |
| How prevalent are certifications on each side? | VISUAL | **BQ36** |

### §13-§19 Projects, formats, READMEs, GitHub, LinkedIn

| Question | Status | Where |
|---|---|---|
| What share of candidates show a public portfolio, and how many projects? | VISUAL | **BQ40** |
| What do candidate projects look like structurally? | VISUAL | **BQ23** formats, **BQ42** repository archetypes |
| What topics do candidates build on? | VISUAL | **BQ41** |
| What do candidate READMEs contain? | VISUAL | **BQ24** |
| What is the *quality* of those projects, not just their structure? | OPEN | **OQ-12** — only rule-detectable structure is observable |
| What does LinkedIn positioning look like (headlines, About, skills sections)? | OPEN | **OQ-02**/**OQ-13** — LinkedIn members were not collected; terms forbid automation; private slot empty (D-026) |
| Kaggle supply? | TEXT | **OQ-14**, closed by D-030: terms forbid scraping, no permitted channel carries location; the 9 % Kaggle-link share (C15) is the only measure (`docs/kaggle-terms-review.md`) |

### §20-§32 Demand × supply, quadrants, evidence, language, geography, seniority, education, portfolio, positioning, transitions, marketing × data

| Question | Status | Where |
|---|---|---|
| Where do demand and supply overlap and diverge? | VISUAL | **BQ21**, **BQ22**, **BQ20** |
| Which capabilities are demanded but rarely demonstrated? | VISUAL | **BQ21** — with GitHub-blind capabilities marked as blindness, not absence |
| Which technologies are common but not differentiating? | VISUAL | **BQ22** |
| Which positioning clusters exist, and how crowded is each? | VISUAL | **BQ43** |
| How common is a transition into data, and from marketing specifically? | VISUAL | **BQ44** (and the silence that surrounds it is stated in the figure) |
| What does the marketing × data intersection actually contain? | VISUAL | **BQ26** |
| Are candidates the same people across platforms? | OPEN | **OQ-10** — cross-platform identity resolution was deliberately not performed |

### §33-§35 Project opportunity, portfolio architecture, vocabulary

| Question | Status | Where |
|---|---|---|
| What should the next project demonstrate? | VISUAL | **BQ21** (demand against demonstrated evidence) + **BQ23**/**BQ24** (format and documentation gaps); `docs/project-evidence-map.md` |
| What portfolio architecture does the evidence support? | VISUAL | **BQ40** (how many), **BQ23** (which formats), **BQ24** (what to write) |
| Which vocabulary bridges employer and candidate language? | PARTIAL | **BQ35** (what employers name), **BQ39** (what candidates call themselves); the bridge itself is prose in `docs/operational-career-intelligence.md` |

### §40-§48, §58-§62, §71 Temporal, bias, duplication, quality bars, future operations

| Question | Status | Where |
|---|---|---|
| How is the market changing over time? | OPEN | **OQ-07** — Layer 1 is one day, Layer 2 one collection |
| What is the sample bias of the supply side? | TEXT | `docs/supply-methodology.md` §9, `docs/supply-data-quality.md` §8; encoded in every joint figure's note line |
| How reliable is candidate deduplication? | TEXT | `SQ02`; GitHub-internal only |
| Does the observable pool represent the Austrian workforce? | OPEN | **OQ-08** — it is a public-profile sample and says so everywhere |
| Can future agents answer "has the market become more crowded since 2026-09?" | OPEN | **OQ-07** — the schema supports it; the second snapshot does not exist yet |

### Answer-raised and later-registered questions (not asked in these words by either brief)

Raised by the answers above or registered from `docs/original-specification-audit.md` and `docs/supply-completeness-audit.md` on 2026-09-30.

| Question | Status | Where |
|---|---|---|
| Are stated requirements (German, degree) negotiable in screening? | OPEN | **OQ-04** |
| Does closing a portfolio evidence gap change interview rates? | OPEN | **OQ-06** |
| Which employers hire repeatedly; how long do roles stay open? | OPEN | **OQ-15** — needs the second snapshot of OQ-07 |
| Do the 140 anonymous postings belong to the 387 named employers? | OPEN | **OQ-18** — structural; "387" is a lower bound (**BQ33**) |
| Which Styrian bio-declared count is the denominator? | TEXT | **OQ-19**, closed by D-027 (`DECISION_LOG.md`) |
| Which industries carry the demand? | PARTIAL | `T04c` (LinkedIn rows only), business-domain wording in `T05`; remainder **OQ-20** |
| Do agency ads double-count client vacancies? | OPEN | **OQ-21** — structural |
| How accurate are the German-requirement and salary extractors? | OPEN | **OQ-22** — spot checks only |
| Do multinational and Austrian employers ask for different things? | OPEN | **OQ-23** — no ownership attribute |
| Do candidates show collaboration evidence (contributors, issues, contributions)? | OPEN | **OQ-24** — not fetched in the 2026-09-17 collection |

---

## Summary

| | Count |
|---|---|
| Question rows answered by a figure (VISUAL) | 43 rows, answered by the 45 figures |
| Question rows answered in text because a chart would add nothing (TEXT) | 18 |
| Question rows answered only in part (PARTIAL) | 4 |
| Question rows that cannot be answered with the data held (OPEN) | 21 |

Counted from the status cells of the tables above (2026-09-30). Several rows share one register entry (OQ-02 carries three, OQ-07 two), so the rows map onto the **24 entries of `docs/open-questions.md`: 22 unresolved, OQ-14 and OQ-19 closed**.

**The most important thing this audit found.** Every register entry falls into one of five groups, and the groups matter more than the count:

1. **Outcome questions** (OQ-01, OQ-04, OQ-06) — the project measures what employers *state* and what candidates *show*, and never what happens when someone applies. No amount of further collection from advertisements or profiles will answer them; only an application-outcome log will.
2. **Blocked-source questions** (OQ-02, OQ-03, OQ-13, OQ-17; OQ-14 closed by D-030) — the missing evidence exists but sits behind terms that forbid automated collection. The remediation is manual entry or a permission request, not a better scraper.
3. **Cheap-to-close questions** (OQ-09, OQ-12, OQ-16, OQ-20, OQ-22, OQ-23) — answerable with the data already retained privately, needing only hand-labelling or hand-coding effort. These are the highest-value next work.
4. **Structural questions** (OQ-05, OQ-07, OQ-08, OQ-10, OQ-11, OQ-15, OQ-18, OQ-21, OQ-24) — the observation cannot contain the answer, needs a second snapshot, or is deliberately not done (OQ-10).
5. **Definitions** (OQ-19) — closed by D-027 on 2026-09-30.
