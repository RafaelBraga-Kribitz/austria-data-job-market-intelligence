# Dashboards: Power BI project and its HTML twin

Five pages over the repository's public outputs, built twice from one page spec:

| Artefact | What it is | How it is built |
|---|---|---|
| [`JobMarket.pbip`](JobMarket.pbip) with `JobMarket.SemanticModel/` and `JobMarket.Report/` | Power BI Project in text form: TMDL semantic model, PBIR report (enhanced report format), custom theme | `python src/reporting/dashboard_pbip.py` (authoring tool; see "Editing" below) |
| [`html/index.html`](html/index.html) | One static, self-contained HTML file with the same five pages: inline data, hand-built charts, no network, no backend | `python run_all.py dashboard` or `python src/reporting/dashboard_html.py` |

Both read the same files: `outputs/tables/*.csv`, `outputs/market_summary.json` and `outputs/supply_summary.json`. Neither adds data, a table or a conclusion. Every number on a page is read from those files when the model refreshes or the HTML is built; the reading notes are composed from the same numbers, so a new snapshot re-renders them. The page set, titles and German subtitles live in one place, [`src/reporting/dashboard_spec.py`](../src/reporting/dashboard_spec.py). The decision behind this layout is recorded in [DECISION_LOG.md](../DECISION_LOG.md) (entry P-01).

To view the HTML twin, download the file or clone the repository and open `dashboards/html/index.html` in a browser. GitHub shows the file as source, not as a page.

## Pages

| # | Page | German subtitle | Visuals | Reads |
|---|---|---|---|---|
| 1 | Market overview | Wo in Österreich offene Data-Stellen ausgeschrieben sind: Kerninserate nach Rollenfamilie und Bundesland an einem einzigen Stichtag. | KPI cards; core ads by role family; core ads by primary state (Steiermark highlighted) | T02, T03a, market_summary.json |
| 2 | Skills & stacks | Welche Skills die Inserate nennen, wie sich die Steiermark vom Rest Österreichs unterscheidet und welche Dreier-Kombinationen gemeinsam vorkommen. | share of ads per skill with Wilson 95 % interval; Styria vs rest of Austria; most frequent three-skill stacks | T05, T05 by Styria, T06b |
| 3 | Advertised pay floors | Beworbene Mindestgehälter nach Rollenfamilie, Seniorität und Bundesland: kollektivvertragliche Untergrenzen in Inseraten, keine tatsächlich bezahlten Gehälter. | evidence cards; median advertised floor with interquartile range by family, seniority word and state | T09, T09b |
| 4 | Demand vs supply | Was die Inserate verlangen, was öffentliche GitHub-Portfolios zeigen und wie stabil die Reihung der Rollenfamilien unter vier Gewichtungen bleibt. | capability demand vs project evidence; decision-matrix score; rank under four weightings | DS10, D01, D02 |
| 5 | Data quality & coverage | Wie aus Rohzeilen die Analysebasis entsteht, welche Quellen sie tragen und wie genau die Titelklassifikation laut Handprüfung ist. | population funnel; core ads and posting age by source; title precision before and after the audit | market_summary.json, T01, T13b, Q04, Q03c |

Every page carries a provenance footer (source tables, epistemic tag, snapshot dates) and a reading note next to its numbers. The caveats the repository attaches to a number travel with it:

- **Indicative, small n.** Cells below the project's own rule of 30 (docs/limitations.md item 9) are drawn but flagged (`n < 30`, a hatched mark in the HTML). Every Styria-only figure is tentative: Styria has <!--m:styria_core_primary_state-->62<!--/m--> core ads by primary state and <!--m:styria_core_flag-->68<!--/m--> counting every listed site.
- **Text-derived denominators.** Skill shares are shares of the <!--m:core_n_text_basis-->699<!--/m--> core ads with a description that *mention* an item, never a requirement.
- **Legal floors, not pay.** <!--m:salary_with_salary_figure_n-->527<!--/m--> ads state a figure, mostly the collective-agreement minimum the law requires; a floor is not a salary (D05, BQ45).
- **No robust family.** No family meets the decision framework's robustness rule, because every Styrian family count is below 30. The D01/D02 scores were computed with the author's own profile (D-026).
- **Two universes.** Demand (<!--m:core_n-->699<!--/m--> ads, <!--m:_meta.demand_vintage-->2026-10-18<!--/m-->) and supply (<!--m:supply_p_data_n-->1,818<!--/m--> GitHub accounts, <!--m:_meta.supply_vintage_span-->2026-09-17/18<!--/m-->) have different denominators; read orders of magnitude.

## Semantic model (TMDL)

- **One parameter.** `ExportsPath` (in `expressions.tmdl`) is the path to the repository's `outputs\` folder, ending with a backslash. Every table reads through it (`Csv.Document(File.Contents(ExportsPath & "tables\...csv"))`, typed with the en-US culture, or `Json.Document` for the two JSON files). Change that one value to re-point the model.
- **Tables.** Dimensions `Role Family` (T02, labels from DS01), `State` (T03a), `Skill` (T05), `Seniority` (T09b); facts and lookups for skills by region, stacks, pay floors, salary evidence, decision matrix, weighting ranks (D02 unpivoted), capability evidence (DS10), sources (T01 with T13b), title precision (Q03c), duplicates (Q04), the population funnel and the snapshot dates (market_summary.json, supply_summary.json); `Measures` holds every measure.
- **Relationships.** Five, single direction, many-to-one to a dimension: pay floors, decision matrix and weighting ranks to `Role Family`; skills by region to `Skill`; pay floors by state to `State`.
- **Measures.** 72, in display folders `1 Market` to `5 Quality`, each with a `///` description (what Copilot and Q&A read) that names its source field and, where it should equal a quoted number, the README marker key it must match. Ratios use `DIVIDE`; medians are shown per cell only (a median does not add up), so a total row stays blank instead of showing a wrong number. Display cuts (top 15 skills, top 12 regional skills, top 10 stacks, top 14 capabilities) are measures that return blank outside the cut; the tables keep every row.
- **Columns.** Explicit data types, `summarizeBy: none` on keys, order and rank columns, `sortByColumn` where the order matters, technical columns hidden.

## Open in Power BI Desktop (human step)

The project was written and checked as text; it has **not** been opened, refreshed or screenshotted in Power BI Desktop. Checklist:

1. Use a current Power BI Desktop (the PBIR report format is the default in current releases). On an older release, enable *File → Options → Preview features → Power BI Project (.pbip) save option*, *Store semantic model using TMDL format* and *Store reports using enhanced metadata format (PBIR)*, then restart.
2. Open `dashboards/JobMarket.pbip`.
3. *Transform data → Edit parameters*: set `ExportsPath` to your clone's `outputs\` folder, for example `C:\src\austria-data-job-market-intelligence\outputs\` (with the trailing backslash).
4. *Refresh*. If Desktop asks about privacy levels, both sources are local files: set them to the same level.
5. Check the cards against the outputs: page 1 core ads = `market_summary.json` `counts.core_canonical` (<!--m:core_n-->699<!--/m-->), Vienna by primary state <!--m:vienna_core_primary_state-->315<!--/m-->, Styria by primary state <!--m:styria_core_primary_state-->62<!--/m-->; page 3 ads stating a figure <!--m:salary_with_salary_figure_n-->527<!--/m-->; page 5 strict precision <!--m:title_precision_strict_after-->83 %<!--/m-->. The HTML twin shows the same values.
6. Check that the custom theme *Braga Light* is applied (View → Themes). The report registers only this custom theme and no base theme; if Desktop asks for one, pick any and re-apply *Braga Light*.
7. Take one screenshot per page and look for clipped labels before publishing them.
8. Save. Desktop then owns the files: review the diff before committing, and do not run `dashboard_pbip.py` over Desktop edits.

`.pbi/localSettings.json` and `.pbi/cache.abf` are local Desktop state and are git-ignored.

## Editing

- **Page set or wording:** edit `src/reporting/dashboard_spec.py`, then run both generators.
- **Model or report layout:** edit `src/reporting/dashboard_pbip.py` and run it, or edit in Desktop and commit the saved text files.
- **HTML only:** `src/reporting/dashboard_html.py`.

## Checks

```bash
python -m pytest tests/test_dashboards.py -q            # model<->report integrity, spec, alt text, HTML values, determinism
python src/reporting/dashboard_pbip.py --check           # committed project == generator output
python src/reporting/dashboard_html.py --check           # committed HTML == a fresh build from outputs/
python src/reporting/validate_pbip.py --schemas <dir>    # JSON schema validation, offline (needs jsonschema)
```

`tests/test_dashboards.py` checks that every field a visual references exists in the TMDL, every DAX reference resolves, every relationship endpoint exists, no measure shares a name with a column, every measure has a description and a format string (text measures excepted), every partition reads an existing output and every CSV column it types exists in that file's header, the pages match the spec, each page has its German subtitle and a provenance footer, every visual has alt text and a unique tab order with the page title first, and the theme is registered. For the HTML it checks determinism, the KPI values against the source files, the embedded data and the absence of any network reference.

`validate_pbip.py` validates every PBIR/PBIP JSON file against the schema version it declares (report 3.1.0, page 2.0.0, visualContainer 2.5.0, pagesMetadata 1.0.0, versionMetadata 1.0.0, definitionProperties 2.0.0 / 1.0.0, pbipProperties 1.0.0, platformProperties 2.0.0). `<dir>` is a local copy of Microsoft's json-schemas repository (the folder that contains `fabric/`); without it, or without `jsonschema` installed, the script skips with a notice, so CI stays offline.

## Design

Braga design system v2.1 (bk-viz tokens): flat opaque surfaces (`#E4E6EA` page, `#DCDEE2` cards), ink text, hairline grid in the rule colour, one highlighted entity per chart in the ultramarine accent, structure grey for the rest, categorical slots in order for the theme's data colours, square corners, nothing below 12 px. The HTML follows the system's dark mode through `prefers-color-scheme`. Chart text is English; each page has one German subtitle.

## Publication

The project and the HTML contain aggregates that are already public in `outputs/` (CC BY 4.0) and nothing else: no posting text, no links to ads, no employer names, no personal data. `src/publish/export_public.py` copies `dashboards/` into the public tree and its scans cover it like every other file.
