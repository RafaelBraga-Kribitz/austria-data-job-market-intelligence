# Supply data-quality report (Layer 2, collection 2026-09-17, build 2026-09-18)

Tables `outputs/tables/SQ01–SQ11`, `C01`; JSON `outputs/supply_data_quality.json`. Private review files (bios, repository descriptions, labels) stay in `data/processed/supply_quality_*` and are never exported.

## 1. What was collected

| Stage | Count | Note |
|---|---|---|
| user searches | 1,075 (frame A 975, B 40, C 60) | 10 queries hit the 1,000-result cap; 17 frame-C slices truncated at the 120 cap (34,813 available → 6,187 retrieved) |
| search rows → unique accounts | 14,104 → 9,464 | 662 accounts appear in ≥ 2 frames; organisations excluded by `type:user` |
| profiles fetched | 9,464 (0 failures) | names/e-mails never requested |
| candidate accounts built | 9,457 | 7 profiles dropped by `build_supply.py` (account type not `User`, or a bot login); this is the "all" row of C01 and the base of the frame overlap below |
| accounts with an Austrian location signal (P_all) | 9,409 | 48 dropped (foreign place named, no Austrian signal); 1,322 name only "Austria" |
| repositories listed (owner, incl. forks) | 126,013 | up to 300 per account |
| data repositories (owned, non-fork) | 9,347 in the analysed population (12,493 before tier restriction) | reasons: language 51 %, keyword 40 %, topic 9 % |
| READMEs + trees fetched | 11,798 (README missing/404 for 1,915) | capped at 15 most recently pushed data repos per owner |
| social accounts fetched | data-signal users (4,625 targeted) | link types only |

## 2. Duplicates and overlap (SQ02)

0 duplicate account ids, 0 duplicate repository ids. Frame overlap: A only 1,832 · B only 1,807 · C only 5,156 · A+C 443 · A+B 144 · B+C 74 · all three 1. Cross-platform deduplication is not applicable (single automated source).

## 3. Missingness (SQ03, P_data n = 1,818)

| Field | Missing | Share |
|---|---|---|
| bio | 295 | 16.2 % |
| company field | 904 | 49.7 % |
| location resolving to a Bundesland | 304 | 16.7 % (country only) |
| website/blog | 1,030 | 56.7 % |
| owned repository | 147 | 8.1 % |
| education wording (bio/README) | 1,259 | 69.3 % |
| seniority wording | 1,354 | 74.5 % |
| any skill evidence | 78 | 4.3 % |

Absence of wording is reported as such and never read as absence of the attribute.

## 4. Geography (SQ04)

8,012 accounts resolve to state and city, 119 to a state only, 1,322 to "Austria" only; 89 also name a foreign place and 112 are multi-location strings. Eleven frame-B (Styrian-token) accounts resolved to another state and are excluded from Styrian counts. Location strings are self-reported and can be stale (§5).

## 5. Staleness (SQ05)

| Population | Profile updated within 12 months | Any push within 12 months | No push for 3+ years | Median account age |
|---|---|---|---|---|
| P_all (9,409) | 79.1 % | 45.6 % | 2,194 | 7.7 years |
| P_data (1,818) | 89.0 % | 65.3 % | 209 | 7.2 years |

Among data repositories, 44 % were last pushed more than three years ago and 67 % have no stars (C14d/e).

## 6. Classification precision (SQ06, SQ10, SQ11, D-021)

* Bios with a data word: 1,940; bio-declared core family 863 of them; the rest carry generic wording (adjacent bucket or no rule). Rule provenance of T1: overrides 833, after-transition reclassification 28, Layer 1 title rules 11.
* **Bio → family** (40 random T1, reviewed by the author): strict 78 %, lenient 90 %. Error types: organisation accounts read as people; engineering bios with ML words; finance/quant wording; students/researchers counted as declared roles (lenient).
* **Repository → data project** (40 random substantive projects): strict 75 %, lenient 92.5 %. Lenient cases are data-adjacent tooling (SQL guides, dataset collections, exporters, visualisation components).
* **Skills from README prose**: after D-021, generic entries need repeated or stricter matches; residual risk list in SQ07 (generic "AI", "Cloud", "Data Visualization", "Statistics" remain indicative). Git is not counted (true by construction).
* Themes: two-hit README rule; 38 % of projects carry no theme (C18c). Formats: bare "pipeline"/"paper" triggers removed.

## 7. Frame selection effects (SQ09)

| Frame | n | has bio | T1 share | data-signal share | median owned repos | push in 12 m |
|---|---|---|---|---|---|---|
| A bio-signal | 2,395 | 94 % | 36 % | 53 % | 4 | 54 % |
| B Styria complete | 2,023 | 41 % | 2.6 % | 12.2 % | 3 | 43 % |
| C base-rate sample | 5,649 | 41 % | 2.9 % | 11.3 % | 3 | 45 % |

Reading: among *all* Austrian GitHub accounts with a repository, about one in nine carries a data signal and about one in 35 declares a data role in the bio; frame A exists to find the latter across regions. Shares computed on P_data or P_T1 therefore describe a population that is ~50 % keyword-found; frame-B-only shares (Styria) are the unbiased ones.

## 8. Known biases (not measurable here)

GitHub over-represents engineers, researchers and students; under-represents BI/Excel/SAP/Power BI practitioners and anyone whose work is private; English is the platform language (99 % of bios, 95 % of READMEs are English), so the language signal says nothing about German ability; the hireable flag is rarely set (17 %); educational repositories inflate raw project counts (55 % of P_data own one); multi-account people and accounts of people who left Austria are not detectable.

## 9. What this dataset can and cannot say

Can: how Austrian-located public GitHub accounts with a data signal describe themselves, what they build, how they document it, which tools and methods their public work shows, and how that compares in ranking and order of magnitude with advertised demand. Cannot: workforce size, proficiency, experience, hiring outcomes, anything about people without public code, or exact shares of the labour supply.
