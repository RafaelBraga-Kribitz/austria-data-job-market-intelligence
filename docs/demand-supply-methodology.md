# Demand × supply methodology (Layer 3)

**Version:** Demand × Supply v1 · demand = Layer 1 snapshot 2026-09-16 (720 core postings, 719 with description) · supply = Layer 2 GitHub collection 2026-09-17 · decisions D-016, D-019, D-020. Code: `src/analysis/demand_supply.py`. Tables `outputs/tables/DS01–DS13`; JSON `outputs/demand_supply_*.json`. Findings: `CAREER_SUPPLY_DEMAND_MAP.md`.

## 1. What is joined on what

| Dimension | Demand side (Layer 1) | Supply side (Layer 2) | Table |
|---|---|---|---|
| Role family | `T02` core postings by family | P_T1 bio families (same taxonomy) | DS01 |
| Normalized title | `T02b` | P_T1 normalized titles | DS02 |
| Skill (Layer 1 canonical) | `T05` share of 719 ads mentioning | P_data: any evidence; substantive-project evidence | DS03 / DS04 (tools only) |
| Capability group | union over member skills per posting (private file) | P_data: any / mentioned / used / project-demonstrated | DS09 / DS10 |
| Bundesland | `T03a` | P_data / P_T1 by state (frame-aware) | DS05, DS05b |
| Language | `T07` German requirement, `T07c` posting language, `T07e` scenarios | presentation language of bios/READMEs | DS06, DS06b |
| Seniority | `T08` title words | bio words (student/junior/unlabelled/senior/lead) | DS07 |
| Education, certification | `T11a/b/d/e` | wording in bios/READMEs | DS08 |
| Positioning clusters | `T05` mention shares of a cluster's defining skills | k-means clusters over P_data (C23) | DS11 |
| Marketing × data | `T02` marketing_analytics, `T05` domain words | C22d bios, C24 projects | DS12 |
| Styria / Graz | `T02` Styrian counts, `T07e` | frame B (complete) | DS13 |

## 2. Metrics on every row (where meaningful)

* `demand_share = demand_count / demand_n` — share of core postings that *mention* the item (never "require").
* `supply_share = supply_count / supply_n` — share of the named supply population with the item; Wilson 95 % interval.
* `project_share` — share of P_data with substantive-project evidence for the item (the conservative reading of "can they show it?").
* `difference_pp = 100 × (supply_share − demand_share)`; `relative_representation = supply_share / demand_share`.
* `evidence_gap_pp = 100 × (demand_share − project_share)` — how much more often employers mention a capability than candidates demonstrate it in a documented, non-educational project.
* `candidate_density = supply_count / demand_count` — observed candidates per open posting (Styria: complete frame; Vienna and others: lower bounds).
* `quadrant` — A high/high, B high demand/lower supply, C lower demand/high supply, D lower/lower, thresholds = medians of the joined set (stated in the table). Labels describe structure; they are not "good" or "bad".

## 3. Denominator discipline

The two sides are different universes: a posting is a document written by an employer on one day; a candidate row is a public account that happened to be findable. Therefore: (1) shares are placed side by side, never subtracted into a score; (2) comparisons are of rankings and orders of magnitude; (3) every row carries both n's; (4) frames are named where they bias a comparison (DS05: Styrian supply complete, Vienna sampled); (5) survey and Eurostat rows stay in their own tables (`O*`) and are cited, not merged; (6) LinkedIn manual counts (if any) are indices and are never added to GitHub counts.

## 4. Capability layer

`config/capability_map.json` maps Layer 1 skills and Layer 2 project themes/formats to ~50 capabilities in groups (tool, technical, analytical, business, domain, engineering, decision, ai, credential). Demand share per capability is the share of core postings mentioning *any* member skill, computed from the private posting file (exact union); the public repository, which lacks that file, falls back to the maximum member-skill share and records the method in the table. Supply per capability counts candidates with any member skill at each evidence strength or any member theme/format in their projects.

## 5. Interpretation labels (DS10)

* *core market capability* — demand ≥ median and supply ≥ median.
* *demanded, rarely project-demonstrated* — demand ≥ median and project-demonstrated share < ½ of demand share → **demonstration opportunity candidate** (validate that the demand is meaningful before acting: check the absolute demand count and the family profile in T14).
* *commonly evidenced, less demanded* — supply ≥ median, demand < median → not differentiating on its own.
* *demanded, less commonly evidenced* — high demand, lower supply; check whether the tool is simply invisible on GitHub (Power BI, SAP, Excel) before reading it as a supply gap.
* *smaller on both sides*.

## 6. What Layer 3 cannot say

It does not measure hiring, competition per vacancy, or the size of the invisible (non-GitHub) supply; a low supply share can mean "rare skill" or "skill that leaves no public trace". It does not measure proficiency (language or technical). It does not attribute causality. Styrian counts on the demand side are a one-day stock (58) against a yearly flow roughly five times larger (AMS JobBarometer 300 in 2025); densities are therefore only comparable *between* families or regions computed the same way, not as absolute "candidates per job" claims.
