# Seasonality: when in the year is Austrian labour demand strongest?

**Purpose.** To plan study/build periods against application periods. **Added 2026-09-16 (DECISION_LOG D-015).** Tables `outputs/tables/S01`–`S06`, figure `F13_seasonality.png`, machine-readable `outputs/seasonality.json`, script `src/analysis/seasonality.py`, collector `src/acquisition/collect_eurostat_jvs.py`.

**Bottom line in three sentences.** The fourth quarter (October–December) is the weakest quarter for open vacancies in every Austrian sector aggregate, in both estimation methods and in every sub-sample — this is the one robust seasonal fact. The amplitude is small: 5–14 % between the best and the worst quarter, against 255–567 % between the best and worst *year*, so which year you are searching in matters roughly 19–49 times more than which quarter. Nothing in this analysis is specific to data roles or to Styria, and the apparent Q3 peak in market services is confounded with tourism, so it must not be read as demand for data jobs.

---

## 1. Why this could not be answered from this project's own postings

The project's posting layer is a **one-day snapshot** (2026-09-16). A snapshot observes an advertisement only if it is still open on that day, so the distribution of first-publish dates is *posting volume × probability of still being open* — a survival curve, not a calendar. The data show this directly (S05):

| First published within | Core postings | Share of 720 |
|---|---|---|
| 7 days | 253 | 35 % |
| 14 days | 360 | 50 % |
| 30 days | 492 | 68 % |
| 90 days | 650 | 90 % |
| 180 days | 691 | 96 % |

376 of the 720 core postings (52 %) were first published in the collection month itself, 167 in August, 90 in July, then a long thin tail. That monotone decay is survival, not seasonality: it would look the same whichever month the collection had happened. Separating the two would require either repeated collections over a year or the duration distribution of advertisements, and the project has neither. **No seasonal claim is made from the posting snapshot.**

One thing the snapshot *does* support, which is useful for the same planning question: **the visible market turns over fast.** Half of the open core advertisements were less than 14 days old, and median age at collection was 5 days on karriere.at, 14 on LinkedIn, 19 on jobs.at, 34 on willhaben and 41 on the AMS/EURES feed (the last two carry long-running and evergreen ads). Reacting within days is worth more than choosing a month.

## 2. The source that can answer it

| | |
|---|---|
| Series | Eurostat **`jvs_q_nace2`**, Job Vacancy Statistics by NACE Rev. 2 activity, quarterly |
| Behind it | Statistik Austria **Offene-Stellen-Erhebung**, compiled under Regulation (EU) 2019/2152 |
| Definition of a vacancy | *"Eine neu geschaffene, nicht besetzte oder demnächst frei werdende bezahlte Stelle, zu deren Besetzung aktive Schritte unternommen werden"* (Statistik Austria, fetched 2026-09-16) — a paid post under **active recruitment**, which is close to "an advertisement is open" |
| Geography / grain | Austria only (no NUTS-2, so **Styria is not separable**); quarter; NACE aggregates only |
| Sectors available for Austria | B-F industry & construction · G-N market services · O-S public sector, education, health · B-N business economy · B-S total economy. **No occupation detail**, so no "data roles" |
| Coverage | 2009-Q1 … 2025-Q4 = 17 complete years, 336 observations, non-seasonally-adjusted (seasonal adjustment would erase the signal) |
| Unit | **Stock** of vacancies open in the reference period — not new postings, not hires |
| Access & licence | Documented public REST API, no key, no restriction on automated access; Eurostat content is reusable with attribution (Commission Decision 2011/833/EU). This is the one acquisition step in the project that anyone can re-run (DECISION_LOG D-013 lists it as a permitted channel), so the whole seasonality layer is reproducible from the public repository. |

## 3. Method

Seasonal index, computed two independent ways and reported side by side; agreement between them is the robustness check.

* **Method A — ratio to own-year mean.** Each quarter's value divided by the mean of its own calendar year. Removes every between-year level and trend effect by construction. Confidence intervals are t-based across the 17 years.
* **Method B — ratio to centred moving average.** Classical multiplicative decomposition: value ÷ the 2×4 centred moving average `(0.5·x₋₂ + x₋₁ + x₀ + x₊₁ + 0.5·x₊₂)/4`. Handles within-year trend; loses two quarters at each end.

An index of **1.00 is an average quarter**. Sensitivity: the same indices are recomputed excluding 2020–2021 (COVID) and on 2015 onwards only (S03).

## 4. Results (S01, full sample 2009–2025)

| Sector | Q1 Jan–Mar | Q2 Apr–Jun | Q3 Jul–Sep | Q4 Oct–Dec |
|---|---|---|---|---|
| **G-N market services** (ICT, finance, professional, trade, transport, hospitality) | 1.007 | 0.979 | **1.038** (CI 1.005–1.070) | **0.976** |
| — cross-check, method B | 1.016 | 0.990 | 1.031 | 0.959 |
| — years above the year average | 10/17 | 8/17 | 12/17 | 5/17 |
| **B-F industry & construction** | **1.072** (CI 0.993–1.151) | 0.993 | 0.978 | **0.957** |
| — cross-check, method B | 1.084 | 0.997 | 0.970 | 0.930 |
| — years above the year average | 10/17 | 8/17 | 4/17 | 6/17 |
| **O-S public sector, education, health** | 0.989 | **1.058** (CI 1.004–1.112) | 1.023 | **0.930** |
| — cross-check, method B | 1.000 | 1.058 | 1.016 | 0.915 |
| — years above the year average | 7/17 | 12/17 | 10/17 | 5/17 |
| **B-S total economy** | 1.014 | 0.995 | **1.022** | **0.970** |
| — cross-check, method B | 1.032 | 1.003 | 1.015 | 0.952 |
| — years above the year average | 10/16 | 10/16 | 9/16 | 4/16 |

**Which quarter is weakest, counted year by year** (S02): Q4 is the weakest quarter in 8 of 17 years in market services, 9 of 17 in industry, 8 of 17 in the public sector and 10 of 16 in the total economy — the modal weakest quarter in every aggregate. **Which is strongest:** Q1 in 8/17 (market services), 9/17 (industry) and 7/16 (total); Q2 in 7/17 for the public sector.

**Stable across samples** (S03): excluding COVID years and restricting to 2015+ moves the indices by at most 0.04 and never changes which quarter is weakest.

## 5. Interpretation, with the confounds stated

1. **Q4 (October–December) is the reliably thin quarter.** It is the lowest index in all four aggregates, under both methods, in all three samples, and the modal weakest quarter year by year. Two mechanisms are plausible — the Christmas/holiday recruitment pause and annual budget exhaustion — but the data here only shows the pattern, not the cause.
2. **Q1 (January–March) is most often the strongest single quarter**, clearly in industry & construction (index 1.072) and in the total economy. This is consistent with budget years opening in January, and it is the aggregate most relevant to Styria's industrial employers (KNAPP, Magna, Anton Paar, ams OSRAM are NACE B-F type employers).
3. **Do not read the G-N Q3 peak as demand for data jobs.** NACE G-N includes section I (accommodation and food service), which in Austria is heavily seasonal with a summer peak, and section G (retail). The Q3 index of 1.038 is the only interval that excludes 1.00, but it cannot be attributed to ICT (J), finance (K) or professional services (M), because Austria does not report those sections separately in this dataset. The honest statement is: *market services as a whole are slightly busier in Q3, and at least part of that is tourism.*
4. **The calendar is a second-order effect; the cycle is first-order** (S06):

| Sector | Best-vs-worst **quarter** | Best-vs-worst **year** | Cycle ÷ season |
|---|---|---|---|
| G-N market services | 6.4 % | 309 % (2009: 33,680 → 2022: 137,704) | 49× |
| B-F industry & construction | 12.0 % | 567 % | 47× |
| O-S public sector | 13.8 % | 256 % | 19× |
| B-S total economy | 5.4 % | 255 % | 48× |

   Austrian market-services vacancies ran at ~33,700 per quarter in 2009, peaked at ~137,700 in 2022 and were back to ~82,200 in 2025 — a 40 % fall from the peak in three years. Against that, a 6 % seasonal wobble is noise. The same direction appears in this project's own official series: the AMS "Data Scientist" class fell 28 % against 2020 nationally while Styria rose 34 % (JB01). **Where and in which year you look dominates when in the year you look.**
5. **This analysis has no occupation and no regional grain.** It is Austrian, all-sector, quarterly. It is used the same way the AMS JobBarometer is used in this repository: for direction and context, never merged with the posting-level tables.

## 6. What this means for planning

* **Do not schedule applications around the calendar.** The measurable seasonal advantage is a few percent — smaller than the difference between two job boards, and far smaller than the effect of being ready with SQL/Python evidence when a suitable advertisement appears.
* **If a rhythm is wanted anyway:** treat **October–December as the build-and-study block** (thinnest quarter everywhere, holidays inside it) and be **application-ready by early January**, which is the most frequent annual peak in industry and in the total economy, and the quarter that matters most for Styria's industrial employers.
* **Keep the pipeline continuous regardless.** Half of the open advertisements in the snapshot were under 14 days old, and on the fastest board the median open advertisement was 5 days old. Response speed beats month selection.
* **Summer is not dead.** Q3 is above average in market services in 12 of 17 years and is never the modal weakest quarter. Pausing the search over July and August is not supported by the data, even after discounting the tourism component.
* **Watch the cycle, not the season.** The decision-relevant question is whether Austrian vacancies are recovering from the 2022–2025 decline. Re-running `collect_eurostat_jvs.py` each quarter answers that in one command and is permitted.

## 7. Limitations

1. Quarterly, not monthly: "apply in September rather than October" is not supported; only quarter-level statements are.
2. Stock, not flow: the survey counts vacancies open in the reference period, so a short-lived posting wave can be under-represented relative to slow-filling vacancies.
3. No occupation detail: sector aggregates are proxies, and the aggregate containing ICT also contains tourism and retail (§5.3).
4. No regional detail: Styria is not separable; the Styrian pattern could differ, particularly because its industrial employers sit in the B-F aggregate, whose Q1 peak is the strongest seasonal effect measured here.
5. Survey, not census: the Offene-Stellen-Erhebung is a firm survey with its own sampling error, not published with the series used here; the confidence intervals in S01 reflect year-to-year variation only.
6. 17 years cover two shocks (2009 aftermath, 2020–2021). The sensitivity runs show the pattern survives their removal, but the estimates are not independent of the cycle.
7. Nothing here measures hiring, competition per advertisement, or how quickly applications are reviewed in any quarter.

## 8. Reproduction

```bash
python src/acquisition/collect_eurostat_jvs.py   # public API, no key, re-runnable by anyone
python src/analysis/seasonality.py               # writes S01-S06, F13, outputs/seasonality.json
```
