# Seasonality: when in the year is Austrian labour demand strongest?

**Purpose.** To plan study/build periods against application periods. **Added 2026-09-16 (DECISION_LOG D-015).** Tables `outputs/tables/S01`–`S06`, figure `BQ03_seasonality` (§4; the legacy F13 figure was retired on 2026-09-30), machine-readable `outputs/seasonality.json`, script `src/analysis/seasonality.py`, collector `src/acquisition/collect_eurostat_jvs.py`.

**Bottom line in three sentences.** The fourth quarter (October–December) is the weakest quarter for open vacancies in every Austrian sector aggregate, in both estimation methods and in every sub-sample — this is the one robust seasonal fact. The amplitude is small: <!--m:season_spread_pct_min-->5<!--/m-->–<!--m:season_spread_pct_max-->14<!--/m--> % between the best and the worst quarter, against <!--m:cycle_spread_pct_min-->255<!--/m-->–<!--m:cycle_spread_pct_max-->567<!--/m--> % between the best and worst *year*, so which year you are searching in matters roughly <!--m:cycle_ratio_min-->19<!--/m-->–<!--m:cycle_ratio_max-->49<!--/m--> times more than which quarter. Nothing in this analysis is specific to data roles or to Styria, and the apparent Q3 peak in market services is confounded with tourism, so it must not be read as demand for data jobs.

---

## 1. Why this could not be answered from this project's own postings

The project's posting layer is a **one-day snapshot** (<!--m:_meta.demand_vintage-->2026-10-18<!--/m-->). A snapshot observes an advertisement only if it is still open on that day, so the distribution of first-publish dates is *posting volume × probability of still being open* — a survival curve, not a calendar. The data show this directly (S05):

| First published within | Core postings | Share of <!--m:core_n-->699<!--/m--> |
|---|---|---|
| 7 days | <!--m:snapshot_age_n_within_7d-->180<!--/m--> | <!--m:snapshot_age_share_within_7d-->26 %<!--/m--> |
| 14 days | <!--m:snapshot_age_n_within_14d-->281<!--/m--> | <!--m:snapshot_age_share_within_14d-->40 %<!--/m--> |
| 30 days | <!--m:snapshot_age_n_within_30d-->405<!--/m--> | <!--m:snapshot_age_share_within_30d-->58 %<!--/m--> |
| 90 days | <!--m:snapshot_age_n_within_90d-->625<!--/m--> | <!--m:snapshot_age_share_within_90d-->89 %<!--/m--> |
| 180 days | <!--m:snapshot_age_n_within_180d-->665<!--/m--> | <!--m:snapshot_age_share_within_180d-->95 %<!--/m--> |

<!--m:first_published_n__collection_month-->310<!--/m--> of the <!--m:core_n-->699<!--/m--> core postings (<!--m:snapshot_first_published_in_collection_month_share-->44 %<!--/m-->) were first published in the collection month itself, 167 in August, <!--m:first_published_n__month_before_previous-->66<!--/m--> in July, then a long thin tail. That monotone decay is survival, not seasonality: it would look the same whichever month the collection had happened. Separating the two would require either repeated collections over a year or the duration distribution of advertisements, and the project has neither. **No seasonal claim is made from the posting snapshot.**

One thing the snapshot *does* support, which is useful for the same planning question: **the visible market turns over fast.** <!--m:snapshot_age_share_within_14d-->40 %<!--/m--> of the open core advertisements were less than 14 days old, and median age at collection was <!--m:posting_age_median_days__karriere-->32<!--/m--> days on karriere.at, <!--m:posting_age_median_days__linkedin-->14<!--/m--> on LinkedIn, <!--m:posting_age_median_days__jobsat-->30<!--/m--> on jobs.at, <!--m:posting_age_median_days__willhaben-->33<!--/m--> on willhaben and <!--m:posting_age_median_days__eures-->38<!--/m--> on the AMS/EURES feed (the last two carry long-running and evergreen ads). Reacting within days is worth more than choosing a month.

## 2. The source that can answer it

| | |
|---|---|
| Series | Eurostat **`jvs_q_nace2`**, Job Vacancy Statistics by NACE Rev. 2 activity, quarterly |
| Behind it | Statistik Austria **Offene-Stellen-Erhebung**, compiled under Regulation (EU) 2019/2152 |
| Definition of a vacancy | *"Eine neu geschaffene, nicht besetzte oder demnächst frei werdende bezahlte Stelle, zu deren Besetzung aktive Schritte unternommen werden"* (Statistik Austria, fetched 2026-09-16) — a paid post under **active recruitment**, which is close to "an advertisement is open" |
| Geography / grain | Austria only (no NUTS-2, so **Styria is not separable**); quarter; NACE aggregates only |
| Sectors available for Austria | B-F industry & construction · G-N market services · O-S public sector, education, health · B-N business economy · B-S total economy. **No occupation detail**, so no "data roles" |
| Coverage | <!--m:eurostat_year_first-->2009<!--/m-->-Q1 … <!--m:eurostat_year_last-->2025<!--/m-->-Q4 = <!--m:season_n_years_max-->17<!--/m--> complete years, 336 observations, non-seasonally-adjusted (seasonal adjustment would erase the signal) |
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
| **G-N market services** (ICT, finance, professional, trade, transport, hospitality) | <!--m:season_index__g_n__q1-->1.007<!--/m--> | <!--m:season_index__g_n__q2-->0.979<!--/m--> | **<!--m:season_index__g_n__q3-->1.038<!--/m-->** (CI <!--m:season_ci_low__g_n__q3-->1.005<!--/m-->–<!--m:season_ci_high__g_n__q3-->1.070<!--/m-->) | **<!--m:season_index__g_n__q4-->0.976<!--/m-->** |
| — cross-check, method B | <!--m:season_index_b__g_n__q1-->1.016<!--/m--> | <!--m:season_index_b__g_n__q2-->0.990<!--/m--> | <!--m:season_index_b__g_n__q3-->1.031<!--/m--> | <!--m:season_index_b__g_n__q4-->0.959<!--/m--> |
| — years above the year average | <!--m:season_years_above_avg__g_n__q1-->10<!--/m-->/<!--m:season_n_years__g_n-->17<!--/m--> | <!--m:season_years_above_avg__g_n__q2-->8<!--/m-->/<!--m:season_n_years__g_n-->17<!--/m--> | <!--m:season_years_above_avg__g_n__q3-->12<!--/m-->/<!--m:season_n_years__g_n-->17<!--/m--> | <!--m:season_years_above_avg__g_n__q4-->5<!--/m-->/<!--m:season_n_years__g_n-->17<!--/m--> |
| **B-F industry & construction** | **<!--m:season_index__b_f__q1-->1.072<!--/m-->** (CI <!--m:season_ci_low__b_f__q1-->0.993<!--/m-->–<!--m:season_ci_high__b_f__q1-->1.151<!--/m-->) | <!--m:season_index__b_f__q2-->0.993<!--/m--> | <!--m:season_index__b_f__q3-->0.978<!--/m--> | **<!--m:season_index__b_f__q4-->0.957<!--/m-->** |
| — cross-check, method B | <!--m:season_index_b__b_f__q1-->1.084<!--/m--> | <!--m:season_index_b__b_f__q2-->0.997<!--/m--> | <!--m:season_index_b__b_f__q3-->0.970<!--/m--> | <!--m:season_index_b__b_f__q4-->0.930<!--/m--> |
| — years above the year average | <!--m:season_years_above_avg__b_f__q1-->10<!--/m-->/<!--m:season_n_years__b_f-->17<!--/m--> | <!--m:season_years_above_avg__b_f__q2-->8<!--/m-->/<!--m:season_n_years__b_f-->17<!--/m--> | <!--m:season_years_above_avg__b_f__q3-->4<!--/m-->/<!--m:season_n_years__b_f-->17<!--/m--> | <!--m:season_years_above_avg__b_f__q4-->6<!--/m-->/<!--m:season_n_years__b_f-->17<!--/m--> |
| **O-S public sector, education, health** | <!--m:season_index__o_s__q1-->0.989<!--/m--> | **<!--m:season_index__o_s__q2-->1.058<!--/m-->** (CI <!--m:season_ci_low__o_s__q2-->1.004<!--/m-->–<!--m:season_ci_high__o_s__q2-->1.112<!--/m-->) | <!--m:season_index__o_s__q3-->1.023<!--/m--> | **<!--m:season_index__o_s__q4-->0.930<!--/m-->** |
| — cross-check, method B | <!--m:season_index_b__o_s__q1-->1.000<!--/m--> | <!--m:season_index_b__o_s__q2-->1.058<!--/m--> | <!--m:season_index_b__o_s__q3-->1.016<!--/m--> | <!--m:season_index_b__o_s__q4-->0.915<!--/m--> |
| — years above the year average | <!--m:season_years_above_avg__o_s__q1-->7<!--/m-->/<!--m:season_n_years__o_s-->17<!--/m--> | <!--m:season_years_above_avg__o_s__q2-->12<!--/m-->/<!--m:season_n_years__o_s-->17<!--/m--> | <!--m:season_years_above_avg__o_s__q3-->10<!--/m-->/<!--m:season_n_years__o_s-->17<!--/m--> | <!--m:season_years_above_avg__o_s__q4-->5<!--/m-->/<!--m:season_n_years__o_s-->17<!--/m--> |
| **B-S total economy** | <!--m:season_index__b_s__q1-->1.014<!--/m--> | <!--m:season_index__b_s__q2-->0.995<!--/m--> | **<!--m:season_index__b_s__q3-->1.022<!--/m-->** | **<!--m:season_index__b_s__q4-->0.970<!--/m-->** |
| — cross-check, method B | <!--m:season_index_b__b_s__q1-->1.032<!--/m--> | <!--m:season_index_b__b_s__q2-->1.003<!--/m--> | <!--m:season_index_b__b_s__q3-->1.015<!--/m--> | <!--m:season_index_b__b_s__q4-->0.952<!--/m--> |
| — years above the year average | <!--m:season_years_above_avg__b_s__q1-->10<!--/m-->/<!--m:season_n_years__b_s-->16<!--/m--> | <!--m:season_years_above_avg__b_s__q2-->10<!--/m-->/<!--m:season_n_years__b_s-->16<!--/m--> | <!--m:season_years_above_avg__b_s__q3-->9<!--/m-->/<!--m:season_n_years__b_s-->16<!--/m--> | <!--m:season_years_above_avg__b_s__q4-->4<!--/m-->/<!--m:season_n_years__b_s-->16<!--/m--> |

**Which quarter is weakest, counted year by year** (S02): Q4 is the weakest quarter in <!--m:season_trough_years__g_n__q4-->8<!--/m--> of <!--m:season_n_years__g_n-->17<!--/m--> years in market services, <!--m:season_trough_years__b_f__q4-->9<!--/m--> of <!--m:season_n_years__b_f-->17<!--/m--> in industry, <!--m:season_trough_years__o_s__q4-->8<!--/m--> of <!--m:season_n_years__o_s-->17<!--/m--> in the public sector and <!--m:season_trough_years__b_s__q4-->10<!--/m--> of <!--m:season_n_years__b_s-->16<!--/m--> in the total economy — the modal weakest quarter in every aggregate. **Which is strongest:** Q1 in <!--m:season_peak_years__g_n__q1-->8<!--/m-->/<!--m:season_n_years__g_n-->17<!--/m--> (market services), <!--m:season_peak_years__b_f__q1-->9<!--/m-->/<!--m:season_n_years__b_f-->17<!--/m--> (industry) and <!--m:season_peak_years__b_s__q1-->7<!--/m-->/<!--m:season_n_years__b_s-->16<!--/m--> (total); Q2 in <!--m:season_peak_years__o_s__q2-->7<!--/m-->/<!--m:season_n_years__o_s-->17<!--/m--> for the public sector.

**Stable across samples** (S03): excluding COVID years and restricting to 2015+ moves the indices by at most 0.04 and never changes which quarter is weakest.


<!-- BQ03_seasonality:start (figure generated by src/analysis/make_visual_layer.py - do not edit by hand) -->
**Q. Should I time my applications by season, or does the cycle swamp the calendar?**

Q4 runs 2%-7% below an average quarter in every sector and Q1 is usually the strongest, but between-year swings are 19-49× the seasonal swing - use Oct-Dec to build and be ready in January, do not wait for a month.

[![BQ03_seasonality](../outputs/figures/BQ03_seasonality.png)](../outputs/figures/BQ03_seasonality.png)

<sub>**Figure BQ03** · deviation from target shown as `error_bars` (interval-range) · built from `S01_seasonal_index.csv`, `S06_season_vs_cycle.csv` · units: index (1.00 = average quarter). **Read with:** Eurostat's Austrian vacancy series has no occupation or regional breakdown; market services (G-N) includes retail, accommodation and food service, so its Q3 peak is not data-job demand.</sub>
<!-- BQ03_seasonality:end -->

## 5. Interpretation, with the confounds stated

1. **Q4 (October–December) is the reliably thin quarter.** It is the lowest index in all four aggregates, under both methods, in all three samples, and the modal weakest quarter year by year. Two mechanisms are plausible — the Christmas/holiday recruitment pause and annual budget exhaustion — but the data here only shows the pattern, not the cause.
2. **Q1 (January–March) is most often the strongest single quarter**, clearly in industry & construction (index <!--m:season_index__b_f__q1-->1.072<!--/m-->) and in the total economy. This is consistent with budget years opening in January, and it is the aggregate most relevant to Styria's industrial employers (KNAPP, Magna, Anton Paar, ams OSRAM are NACE B-F type employers).
3. **Do not read the G-N Q3 peak as demand for data jobs.** NACE G-N includes section I (accommodation and food service), which in Austria is heavily seasonal with a summer peak, and section G (retail). The Q3 index of <!--m:season_index__g_n__q3-->1.038<!--/m--> is the only interval that excludes 1.00, but it cannot be attributed to ICT (J), finance (K) or professional services (M), because Austria does not report those sections separately in this dataset. The honest statement is: *market services as a whole are slightly busier in Q3, and at least part of that is tourism.*
4. **The calendar is a second-order effect; the cycle is first-order** (S06):

| Sector | Best-vs-worst **quarter** | Best-vs-worst **year** | Cycle ÷ season |
|---|---|---|---|
| G-N market services | <!--m:season_spread_pct__g_n-->6.4<!--/m--> % | <!--m:cycle_spread_pct__g_n:int0-->309<!--/m--> % (<!--m:eurostat_year_mean_min_year__g_n-->2009<!--/m-->: <!--m:eurostat_year_mean_min__g_n-->33,680<!--/m--> → <!--m:eurostat_year_mean_max_year__g_n-->2022<!--/m-->: <!--m:eurostat_year_mean_max__g_n-->137,704<!--/m-->) | <!--m:cycle_ratio__g_n:int0-->49<!--/m-->× |
| B-F industry & construction | <!--m:season_spread_pct__b_f-->12.0<!--/m--> % | <!--m:cycle_spread_pct__b_f:int0-->567<!--/m--> % | <!--m:cycle_ratio__b_f:int0-->47<!--/m-->× |
| O-S public sector | <!--m:season_spread_pct__o_s-->13.8<!--/m--> % | <!--m:cycle_spread_pct__o_s:int0-->256<!--/m--> % | <!--m:cycle_ratio__o_s:int0-->19<!--/m-->× |
| B-S total economy | <!--m:season_spread_pct__b_s-->5.4<!--/m--> % | <!--m:cycle_spread_pct__b_s:int0-->255<!--/m--> % | <!--m:cycle_ratio__b_s:int0-->48<!--/m-->× |

   Austrian market-services vacancies ran at ~<!--m:eurostat_year_mean_min__g_n:int100-->33,700<!--/m--> per quarter in <!--m:eurostat_year_mean_min_year__g_n-->2009<!--/m-->, peaked at ~<!--m:eurostat_year_mean_max__g_n:int100-->137,700<!--/m--> in <!--m:eurostat_year_mean_max_year__g_n-->2022<!--/m--> and were back to ~<!--m:eurostat_year_mean_latest__g_n:int100-->82,200<!--/m--> in <!--m:eurostat_year_last-->2025<!--/m--> — a <!--m:eurostat_change_from_peak__g_n:apct0-->40 %<!--/m--> fall from the peak in three years. Against that, a <!--m:season_spread_pct__g_n:int0-->6<!--/m--> % seasonal wobble is noise. The same direction appears in this project's own official series: the AMS "Data Scientist" class fell <!--m:jb_data_scientist_change__austria:apct0-->28 %<!--/m--> against 2020 nationally while Styria rose <!--m:jb_data_scientist_change__styria:apct0-->34 %<!--/m--> (JB01). **Where and in which year you look dominates when in the year you look.**
5. **This analysis has no occupation and no regional grain.** It is Austrian, all-sector, quarterly. It is used the same way the AMS JobBarometer is used in this repository: for direction and context, never merged with the posting-level tables.

## 6. What this means for planning

* **Do not schedule applications around the calendar.** The measurable seasonal advantage is a few percent — smaller than the difference between two job boards, and far smaller than the effect of being ready with SQL/Python evidence when a suitable advertisement appears.
* **If a rhythm is wanted anyway:** treat **October–December as the build-and-study block** (thinnest quarter everywhere, holidays inside it) and be **application-ready by early January**, which is the most frequent annual peak in industry and in the total economy, and the quarter that matters most for Styria's industrial employers.
* **Keep the pipeline continuous regardless.** <!--m:snapshot_age_share_within_14d-->40 %<!--/m--> of the open advertisements in the snapshot were under 14 days old, and on the fastest board the median open advertisement was <!--m:posting_age_median_days__karriere-->32<!--/m--> days old. Response speed beats month selection.
* **Summer is not dead.** Q3 is above average in market services in <!--m:season_years_above_avg__g_n__q3-->12<!--/m--> of <!--m:season_n_years__g_n-->17<!--/m--> years and is never the modal weakest quarter. Pausing the search over July and August is not supported by the data, even after discounting the tourism component.
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
python src/analysis/seasonality.py               # writes S01-S06, outputs/seasonality.json (BQ03 is the figure)
```
