# Completeness audit against the Layer 2/3 brief (2026-09-18)

Literal checklist against the brief that added Layer 2 (candidate supply) and Layer 3 (demand × supply). Status: **DONE / PARTIAL / NOT POSSIBLE / NOT APPLICABLE**. For every PARTIAL or NOT POSSIBLE item: why, what evidence is missing, whether it materially affects conclusions, and whether it is future work. Table ids refer to `outputs/tables/`.

| § | Requirement | Status | Where | Notes (why / missing / material? / future?) |
|---|---|---|---|---|
| 0–1 | Three-layer structure; Layer 1 preserved; precise terminology | DONE | AGENT_CONTEXT §22–24, docs/demand-supply-methodology.md | Layer 1 code/tables untouched; supply vocabulary ("observed", "public-profile density") used throughout |
| 2 | Inspect existing repository first | DONE | DECISION_LOG D-016 | taxonomies reused, no parallel taxonomy |
| 3 | Core research question | DONE | CAREER_SUPPLY_DEMAND_MAP.md | — |
| 4 | Candidate population per family, distributions | DONE (GitHub) | C01–C09, C10 | unit = public GitHub account; not a census |
| 5 | Raw/normalised titles, entropy, concentration, overlap | DONE | C02, C03, C04b, DS02 | raw phrases suppressed below 3 accounts |
| 6 | Seniority from explicit evidence; by family/geo/tech/education; vs Layer 1 | PARTIAL | C06, C06b–e, DS07, DS07b | years of experience/career history not on GitHub → title-to-experience mismatch not measurable; material for §27; future: LinkedIn slot |
| 7 | Geography incl. Graz/Styria; local/relocate/remote | PARTIAL | C05, C05a–c, DS05, DS05b, DS13 | states/cities done (Styria complete); relocation/remote intent not observable (hireable flag only); not material |
| 8 | Language supply with CEFR | NOT POSSIBLE (proxy only) | C07, DS06, DS06b | GitHub shows presentation language, not proficiency; **material** for the Styria English-only intersection; future: manual LinkedIn slot (languages with levels) |
| 9 | Technologies, prevalence, co-occurrence, by role/seniority/geo | DONE | C10, C10b–e, C12, DS03, DS04 | proprietary tools under-observed by nature; stated on every table |
| 10 | Capabilities with evidence strength | DONE (professional strength NOT POSSIBLE) | C11, DS10, capability_map.json | mentioned/used/demonstrated/project-demonstrated; "professionally experienced" declared unobservable |
| 11 | Education by family/seniority/geo/tech; vs employer requirements | PARTIAL | C08, C08b–e, DS08 | wording only (69 % silent); by-technology and by-transition cuts not produced (tiny cells); not material |
| 12 | Certifications; vs demand | DONE | C09, C09b–d, DS08 | wording only |
| 13 | Project supply, portfolio shares, counts with definition | DONE | C14, C15, C16 | definition in schema; Kaggle/portfolio presence as link types only |
| 14 | Project structure metadata | DONE (contributors NOT POSSIBLE) | supply_projects (private), C14c–e, C17, C19 | contributors/issues/releases not fetched (budget); not material |
| 15 | Project topics; vs demand relevance | DONE | C18, C18b–c, DS09, DS10 | two-hit README rule; 38 % untagged |
| 16 | Formats; which are useful evidence | DONE | C17, C17b, project-evidence-map.md | — |
| 17 | README/writing patterns; communication pattern | DONE | C19, C19b–e, operational-career-intelligence.md §2 | aggregate only; no quotes |
| 18 | GitHub analysis, archetypes, no ranking | DONE (open-source contribution NOT POSSIBLE) | C14, C14b–e | contributions to others' repos not fetched |
| 19 | LinkedIn analysis | NOT POSSIBLE (by automation) | supply_linkedin.json, docs/supply-methodology.md §7, ingest_linkedin_manual.py | terms/robots (D-013, D-018); **material** for positioning/titles/languages/transitions; future: manual slot (templates exist) |
| 20 | Keyword/vocabulary alignment, four term classes | DONE | DS03, DS10, operational_career_context.json → vocabulary_bridge | — |
| 21 | Candidate density with documented denominators | DONE | DS01, DS05, DS05b, DS13, SQ01 | search universe/query/date/dedup documented |
| 22 | Demand × supply matrix | DONE | DS01–DS08, demand_supply_matrix.json | no single score |
| 23 | Quadrants | DONE | DS01, DS03, DS10, figure BQ22 (legacy DSF04) | medians as thresholds; no good/bad labels |
| 24 | Demand × supply × evidence | DONE (professional evidence NOT POSSIBLE) | DS09, DS10 | demonstration opportunities labelled, with validation rule |
| 25 | Demand × supply × language incl. Styria/Graz | PARTIAL | DS06, DS06b | demand side complete; supply proficiency missing (see §8) |
| 26 | Demand × supply × location | DONE (frame-aware) | DS05, DS05b, DS13, BQ37 (legacy DSF05) | Vienna lower bounds |
| 27 | Demand × supply × seniority; mismatch signals | PARTIAL | DS07, DS07b | mismatch signal not measurable (no years) |
| 28 | Demand × supply × education; marketing→data rarity | DONE | DS08, C22, C22b–d | measured: marketing named in 10 of 872 bios, no explicit transition |
| 29 | Demand × supply × portfolio per family | DONE | project-evidence-map.md/.json, DS09 | no project count prescribed |
| 30 | Positioning clusters | DONE | C23, DS11 | 8 k-means archetypes, descriptive |
| 31 | Transition-candidate analysis | PARTIAL | C22, C22b–d | frequency/destination measured; time/history/skills acquired not observable (bios) |
| 32 | Marketing × data intersection | DONE | C22d, C24, DS12, figure BQ26 (legacy SF13) | small counts, stated |
| 33 | Project opportunity engine | DONE (transparent dimensions, no score) | DS10 labels, project_evidence_map.json, operational-career-intelligence.md | — |
| 34 | Portfolio evidence matrix | DONE | project-evidence-map.md, profile-specific §3 | "need for stronger evidence" derived from DS10 |
| 35 | Writing/communication intelligence (evidence only) | DONE | operational-career-intelligence.md §1–5 | no artefacts written |
| 36 | Raw data preserved; private/public separation; per-source record | DONE | data-sources.md Tier 4, legal audit §10, .gitignore, export script | — |
| 37 | Normalised data model | DONE | schemas/supply_schema.md | — |
| 38 | Source strategy (multiple classes) | DONE / PARTIAL | data-sources.md | GitHub, Eurostat, Stack Overflow used; LinkedIn/Kaggle/portfolio/communities/job platforms documented as not usable |
| 39 | Source-quality tags on metrics | DONE | every table has source/quality columns or a stated population | — |
| 40 | Temporal analysis | PARTIAL (single snapshot) | C14d, SQ05 | push dates/account ages only; no series — stated |
| 41 | Sample-bias analysis | DONE | docs/supply-data-quality.md §7–8, SQ09 | — |
| 42 | Deduplication, cross-platform | DONE / NOT APPLICABLE | SQ02 | single automated source; conservative by design |
| 43 | Privacy/legal/ethical review | DONE | legal audit §10, PUBLICATION_DECISION §8 | not legal advice |
| 44 | No individual ranking | DONE | — | no individual outputs anywhere public; clusters only |
| 45 | Uncertainty (n, denominators, CIs) | DONE | all C/DS tables (Wilson CIs) | — |
| 46 | Statistical methods fit for purpose | DONE | proportions/CIs, entropy/HHI, co-occurrence/lift, k-means | no method used without a question |
| 47 | Multiple demand/supply metrics | DONE | DS tables: shares, difference, ratio, density, evidence gap | — |
| 48 | No fake composite score | DONE | — | none computed |
| 49 | CAREER_SUPPLY_DEMAND_MAP.md with 20 questions | DONE | root | — |
| 50 | AGENT_CONTEXT.md updated | DONE | §22–24 | — |
| 51 | operational-career-intelligence.md | DONE | docs/ | — |
| 52 | project-evidence-map.md | DONE | docs/ + JSON | — |
| 53 | Machine-readable JSON outputs (20 files) | DONE | outputs/*.json | schemas described in supply_schema.md §demand_supply_join and in each JSON's meta |
| 54 | C01–C21 and DS01–DS11 tables | DONE (+ C22–C24, DS12–DS13, SQ, O) | outputs/tables | naming consistent with Layer 1 |
| 55 | Figures | DONE | BQ20–BQ26, BQ36–BQ44 (legacy SF01, SF02, SF05–SF16, DSF01–DSF08; S03/S04 retired) | n/source/date on every figure; CIs where meaningful; legacy index in README |
| 56 | Publication audit | DONE | legal audit §10, PUBLICATION_DECISION §8, export script | — |
| 57 | README update | DONE | README.md | — |
| 58 | Supply data-quality doc with formal checks | DONE | docs/supply-data-quality.md, SQ01–SQ11 | — |
| 59 | Research audit | DONE | docs/supply-research-audit.md | — |
| 60 | Completeness checklist | DONE | this file | — |
| 61 | Quality bar (no invented data, denominators, reproducibility, skepticism) | DONE | — | every number traceable via digest |
| 62 | "Do not" list | DONE | — | no scraping against terms, no candidate scoring, no causal claims |
| 63 | Deliverable structure | DONE (adapted) | repository map in README | — |
| 64–65 | Autonomous phased execution | DONE | this session | LinkedIn: not circumvented; dark slot instead |
| 66 | Versioning | DONE | supply_build_manifest.json, methodology §8 | Demand v1 / Supply v1 / D×S v1 |
| 67 | Executive report A–P | DONE | final session report + CAREER_SUPPLY_DEMAND_MAP.md | — |
| 68 | "So what" layer | DONE | CAREER_SUPPLY_DEMAND_MAP.md §20 | — |
| 69–70 | Neutral analysis first; profile layer separate | DONE | docs/profile-specific-demand-supply-analysis.md (private) | — |
| 71 | Future-operations data model | DONE | schema, dated folders, table-to-table comparison rules | — |
| 72 | Completion criteria | DONE except items marked PARTIAL/NOT POSSIBLE above | — | LinkedIn positioning and language proficiency are the two material gaps |

**Material gaps (affect conclusions):** (1) language proficiency of candidates (§8, §25) — the Styria English-only intersection remains a demand-side-only statement; (2) LinkedIn positioning (§19) — titles as employers see them, career histories and transition narratives are unmeasured; both are covered by the manual slot, which the owner can fill. **Non-material gaps:** contributors/issues per repository, relocation intent, education by technology, time series.

**Closing action per PARTIAL / NOT POSSIBLE item (2026-09-30).** §6, §27, §31 (experience, mismatch, transition history) → OQ-11, open (LinkedIn slot). §7 relocation/remote intent → will-not-do: not observable on GitHub beyond the hireable flag. §8, §25 (language proficiency) → OQ-02, open. §11 education by technology/transition → will-not-do: tiny cells (69 % of P_data show no education wording), not material. §14, §18 (contributors, issues, releases, contributions to others' repositories) → OQ-24, open (next GitHub collection). §19 (LinkedIn) → OQ-02/OQ-13, open. §38 (Kaggle and other sources) → OQ-14, closed (D-030: terms forbid it; no permitted channel carries location). §40 (time series) → OQ-07, open. Register: `docs/open-questions.md`.
