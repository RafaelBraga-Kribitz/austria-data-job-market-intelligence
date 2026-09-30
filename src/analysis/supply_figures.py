"""Layer 2/3 figures SF01–SF16 (supply) and DSF01–DSF08 (demand × supply). Each figure states title, n, source and date.
Reads only the aggregated C*/DS*/O* tables, so it runs in the public repository too.

Naming (2026-09-30, audit L69/L112): the supply figures were called S01–S16 until 2026-09-30, which collided with the
seasonality tables S01–S06 (seasonality.py). They are now SF01–SF16 with unchanged numbers. SF03 and SF04 do not exist:
the original S03 (demand vs supply by family) and S04 (demand vs supply by technology) were retired when the DSF block
was introduced and live on as DSF01 and DSF02, so the series intentionally jumps from SF02 to SF05.
The legacy SF figures sit outside FIGURE-MANIFEST.yaml; the sealed visual layer is BQ01–BQ45.

Usage: python src/analysis/supply_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"; FIG = ROOT / "outputs" / "figures"
T = lambda n: pd.read_csv(TAB / f"{n}.csv")  # noqa: E731
META = json.loads((ROOT / "outputs" / "supply_summary.json").read_text(encoding="utf-8"))
DATE = META["collection_date"]; SRC = "GitHub REST API, Austrian-located accounts"
# demand vintage and core n from the Layer 1 summary (M81), not typed by hand
_MS = json.loads((ROOT / "outputs" / "market_summary.json").read_text(encoding="utf-8"))
DEMAND_DATE = str(_MS["collected_at_range"]["min"])[:10]; N_CORE = int(_MS["counts"]["core_canonical"])
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name, note):
    fig.text(0.01, 0.005, note, fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / f"{name}.png", dpi=130); plt.close(fig)


def barh_ci(df, label, share, lo, hi, title, name, note, top=None, color="#3b6ea5"):
    d = df.head(top) if top else df
    fig, ax = plt.subplots(figsize=(8, max(3, 0.32 * len(d) + 1.2)))
    y = np.arange(len(d))[::-1]
    ax.barh(y, d[share] * 100, color=color)
    if lo in d and hi in d:
        ax.errorbar(d[share] * 100, y, xerr=[(d[share] - d[lo]) * 100, (d[hi] - d[share]) * 100], fmt="none", ecolor="#222", lw=0.8, capsize=2)
    ax.set_yticks(y); ax.set_yticklabels(d[label]); ax.set_xlabel("% of population (Wilson 95 % CI)"); ax.set_title(title, loc="left", fontsize=10)
    save(fig, name, note)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    # SF01 families
    c04 = T("C04_role_family_distribution")
    barh_ci(c04, "family_label", "share", "ci_low", "ci_high", f"Observed candidate supply by role family (bio-declared, n = {int(c04.n.iloc[0])})", "SF01_supply_role_families", f"{SRC}; bios mapped with the Layer 1 taxonomy; {DATE}")
    # SF02 titles
    c03 = T("C03_normalized_title_distribution")
    barh_ci(c03, "normalized_title", "share", "ci_low", "ci_high", f"Normalized titles in bios (n = {int(c03.n.iloc[0])})", "SF02_supply_titles", f"{SRC}; {DATE}")
    # DSF01 demand vs supply families (was S03, retired into the DSF block)
    ds01 = T("DS01_demand_supply_role_families")
    fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(len(ds01)); w = 0.38
    ax.bar(x - w / 2, ds01.demand_share * 100, w, label=f"employer demand (share of {int(ds01.demand_n.iloc[0])} core postings)", color="#c0504d")
    ax.bar(x + w / 2, ds01.supply_share * 100, w, label=f"observed supply (share of {int(ds01.supply_n.iloc[0])} bio-declared candidates)", color="#3b6ea5")
    ax.errorbar(x + w / 2, ds01.supply_share * 100, yerr=[(ds01.supply_share - ds01.supply_ci_low) * 100, (ds01.supply_ci_high - ds01.supply_share) * 100], fmt="none", ecolor="#222", lw=0.8, capsize=2)
    ax.set_xticks(x); ax.set_xticklabels(ds01.label, rotation=25, ha="right"); ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Demand vs observed supply by role family", loc="left", fontsize=10)
    save(fig, "DSF01_demand_vs_supply_families", f"Layer 1 postings {DEMAND_DATE} (T02) × Layer 2 GitHub bios {DATE} (C04); different universes, compare ranking and order of magnitude")
    # DSF02 technologies (was S04, retired into the DSF block)
    ds04 = T("DS04_demand_supply_technologies").head(25)
    fig, ax = plt.subplots(figsize=(8.5, 8)); y = np.arange(len(ds04))[::-1]; h = 0.27
    ax.barh(y + h, ds04.demand_share * 100, h, label="demand: share of ads mentioning", color="#c0504d")
    ax.barh(y, ds04.supply_share * 100, h, label="supply: candidates with any evidence", color="#3b6ea5")
    ax.barh(y - h, ds04.project_share * 100, h, label="supply: candidates with substantive-project evidence", color="#7fb069")
    ax.set_yticks(y); ax.set_yticklabels(ds04.category); ax.set_xlabel("%"); ax.legend(fontsize=8, loc="lower right"); ax.set_title("Demand vs observed supply by technology (top 25 by demand)", loc="left", fontsize=10)
    save(fig, "DSF02_demand_vs_supply_technologies", f"T05 (n = {int(ds04.demand_n.iloc[0])}) × C10 (n = {int(ds04.supply_n.iloc[0])}); {DATE}")
    # DSF03 capabilities
    ds10 = T("DS10_demand_supply_capability_evidence").sort_values("demand_share", ascending=False).head(30)
    fig, ax = plt.subplots(figsize=(8.5, 9)); y = np.arange(len(ds10))[::-1]
    ax.barh(y + h, ds10.demand_share * 100, h, color="#c0504d", label="demand share (any member skill)")
    ax.barh(y, ds10.supply_any_share * 100, h, color="#3b6ea5", label="supply: any evidence")
    ax.barh(y - h, ds10.supply_project_share * 100, h, color="#7fb069", label="supply: project-demonstrated")
    ax.set_yticks(y); ax.set_yticklabels(ds10.category); ax.set_xlabel("%"); ax.legend(fontsize=8, loc="lower right"); ax.set_title("Demand × supply × evidence by capability", loc="left", fontsize=10)
    save(fig, "DSF03_demand_vs_supply_capabilities", f"demand: {ds10.demand_method.iloc[0]}; supply: P_data n = {int(ds10.supply_n.iloc[0])}; {DATE}")
    # DSF04 quadrant scatter (skills)
    ds03 = T("DS03_demand_supply_skills"); d = ds03[ds03.demand_count >= 8].dropna(subset=["supply_share"])
    fig, ax = plt.subplots(figsize=(8, 6.5))
    ax.scatter(d.demand_share * 100, d.supply_share * 100, s=18, color="#3b6ea5")
    for _, r in d.iterrows():
        if r.demand_share >= 0.08 or r.supply_share >= 0.25:
            ax.annotate(r.category, (r.demand_share * 100, r.supply_share * 100), fontsize=7, xytext=(2, 2), textcoords="offset points")
    ax.axvline(d.threshold_demand.iloc[0] * 100, color="#999", lw=0.8, ls="--"); ax.axhline(d.threshold_supply.iloc[0] * 100, color="#999", lw=0.8, ls="--")
    ax.set_xlabel("demand: % of core ads mentioning"); ax.set_ylabel("supply: % of data-signal candidates with any evidence"); ax.set_title("Demand × supply quadrants (skills with ≥ 8 ads)", loc="left", fontsize=10)
    save(fig, "DSF04_quadrants_skills", f"dashed = medians of the joined set; {DATE}")
    # DSF05 geography
    ds05 = T("DS05_demand_supply_geography")
    fig, ax = plt.subplots(figsize=(8, 4)); x = np.arange(len(ds05))
    ax.bar(x - w / 2, ds05.demand_share * 100, w, color="#c0504d", label="demand share of postings"); ax.bar(x + w / 2, ds05.supply_share * 100, w, color="#3b6ea5", label="supply share of data-signal candidates (frames differ!)")
    ax.set_xticks(x); ax.set_xticklabels(ds05.category, rotation=25, ha="right"); ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Demand vs observed supply by Bundesland", loc="left", fontsize=10)
    save(fig, "DSF05_demand_vs_supply_geography", "supply frames: Styria complete, others keyword+base-rate samples → supply shares are not comparable across states (DS05)")
    # DSF06 language
    ds06 = T("DS06_demand_supply_language")
    fig, ax = plt.subplots(figsize=(7, 3.8)); x = np.arange(len(ds06))
    ax.bar(x - w / 2, ds06.supply_bio_en_share * 100, w, color="#3b6ea5", label="supply: English-written bios (of classified bios)")
    ax.bar(x + w / 2, ds06.supply_readme_en_only_share * 100, w, color="#7fb069", label="supply: English-only READMEs (of candidates with READMEs)")
    ax.axhline(ds06.demand_english_share.iloc[0] * 100, color="#c0504d", ls="--", label="demand: English-written ads, Austria (T07c)")
    ax.axhline(ds06.demand_german_req_share.iloc[0] * 100, color="#c0504d", ls=":", label="demand: German required/level-stated, Austria (T07)")
    ax.set_xticks(x); ax.set_xticklabels(ds06.region); ax.set_ylabel("%"); ax.legend(fontsize=7, loc="lower right"); ax.set_title("Language: what ads require vs the language candidates write in", loc="left", fontsize=10)
    save(fig, "DSF06_demand_vs_supply_language", "supply side = presentation language, not proficiency (DS06)")
    # DSF07 seniority
    ds07 = T("DS07_demand_supply_seniority")
    fig, ax = plt.subplots(figsize=(7, 3.8)); x = np.arange(len(ds07))
    ax.bar(x - w / 2, ds07.demand_share * 100, w, color="#c0504d", label="demand: seniority word in ad title"); ax.bar(x + w / 2, ds07.supply_share * 100, w, color="#3b6ea5", label="supply: seniority word in bio")
    ax.errorbar(x + w / 2, ds07.supply_share * 100, yerr=[(ds07.supply_share - ds07.supply_ci_low) * 100, (ds07.supply_ci_high - ds07.supply_share) * 100], fmt="none", ecolor="#222", lw=0.8, capsize=2)
    ax.set_xticks(x); ax.set_xticklabels(ds07.category, rotation=15, ha="right"); ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Seniority wording: ads vs bios", loc="left", fontsize=10)
    save(fig, "DSF07_demand_vs_supply_seniority", f"T08 (n = {int(ds07.demand_n.iloc[0])}) × C06 (n = {int(ds07.supply_n.iloc[0])}); {DATE}")
    # DSF08 education
    ds08 = T("DS08_demand_supply_education"); d = ds08[ds08.dimension == "education_level"].head(5)
    fig, ax = plt.subplots(figsize=(7, 3.8)); x = np.arange(len(d))
    ax.bar(x - w / 2, d.demand_share * 100, w, color="#c0504d", label="demand: level named in ad"); ax.bar(x + w / 2, d.supply_share * 100, w, color="#3b6ea5", label="supply: level wording in bio/READMEs")
    ax.set_xticks(x); ax.set_xticklabels(d.category); ax.set_ylabel("%"); ax.legend(fontsize=8); ax.set_title("Education wording: ads vs candidates", loc="left", fontsize=10)
    save(fig, "DSF08_demand_vs_supply_education", "absence of wording ≠ absence of degree on either side (DS08)")
    # SF05 project types, SF06 formats, SF07 project counts, SF08 README, SF09 GitHub evidence, SF10 portfolio evidence
    c18 = T("C18_project_topics"); d = c18[(c18.population == "projects")].sort_values("count", ascending=False).head(25)
    barh_ci(d.assign(lab=d.group + ": " + d.theme), "lab", "share", "ci_low", "ci_high", f"Project topics (share of {int(d.n.iloc[0])} projects)", "SF05_project_topics", f"{SRC}; {DATE}", color="#7fb069")
    c17 = T("C17_project_formats"); d = c17[c17.population == "projects"].sort_values("count", ascending=False)
    barh_ci(d, "format", "share", "ci_low", "ci_high", f"Project packaging formats (share of {int(d.n.iloc[0])} projects)", "SF06_project_formats", f"{SRC}; {DATE}", color="#7fb069")
    c16 = T("C16_project_count_distribution"); d = c16[(c16.population == "P_data") & (c16.variable == "n_projects")]
    fig, ax = plt.subplots(figsize=(6, 3.5)); ax.bar(d.bucket, d.share * 100, color="#3b6ea5"); ax.set_ylabel("% of data-signal candidates"); ax.set_title(f"Projects per candidate (n = {int(d.n.iloc[0])})", loc="left", fontsize=10)
    save(fig, "SF07_project_count_distribution", f"project definition in schemas/supply_schema.md; {DATE}")
    c19 = T("C19_readme_patterns"); d = c19[c19.population == "documented projects"].sort_values("share", ascending=False)
    barh_ci(d, "feature", "share", "ci_low", "ci_high", f"README features (share of {int(d.n.iloc[0])} documented projects)", "SF08_readme_features", f"{SRC}; {DATE}", color="#8e7cc3")
    c14 = T("C14_github_evidence"); d = c14[c14.population == "P_data"]
    barh_ci(d, "signal", "share", "ci_low", "ci_high", f"GitHub evidence signals (share of {int(d.n.iloc[0])} data-signal candidates)", "SF09_github_evidence", f"{SRC}; {DATE}")
    c15 = T("C15_portfolio_evidence"); d = c15[c15.population == "P_data"].sort_values("share", ascending=False)
    barh_ci(d, "evidence", "share", "ci_low", "ci_high", f"Portfolio / cross-platform evidence (share of {int(d.n.iloc[0])} data-signal candidates)", "SF10_portfolio_evidence", f"{SRC}; {DATE}")
    # SF11 technology network (co-occurrence). networkx is a pinned requirement: a missing install fails loudly
    # instead of silently saving a bar chart under the network's name (L113).
    c12 = T("C12_technology_cooccurrence").head(40)
    try:
        import networkx as nx
    except ImportError as exc:
        raise SystemExit("supply_figures.py: networkx is required for SF11_technology_network (pip install -r requirements.txt)") from exc
    G = nx.Graph()
    for _, r in c12.iterrows():
        G.add_edge(r.skill_a, r.skill_b, weight=r.both)
    pos = nx.spring_layout(G, seed=2, k=0.9)
    fig, ax = plt.subplots(figsize=(8, 6.5))
    nx.draw_networkx_edges(G, pos, width=[G[u][v]["weight"] / c12.both.max() * 4 for u, v in G.edges()], alpha=0.4, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=[300 + 20 * G.degree(n) for n in G.nodes()], node_color="#3b6ea5", alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, ax=ax); ax.axis("off"); ax.set_title("Candidate technology co-occurrence (top 40 pairs)", loc="left", fontsize=10)
    save(fig, "SF11_technology_network", f"edge width = candidates with both; {DATE}")
    # SF12 Styria
    ds13 = T("DS13_styria_graz_demand_supply")
    fig, ax = plt.subplots(figsize=(8, 4.5)); ax.axis("off")
    tbl = ax.table(cellText=[[str(a), str(b)] for a, b in zip(ds13.measure, ds13.value)], colLabels=["measure", "value"], loc="center", cellLoc="left", colWidths=[0.75, 0.25]); tbl.auto_set_font_size(False); tbl.set_fontsize(7.5); tbl.scale(1, 1.25)
    ax.set_title("Styria / Graz: demand (one-day stock) vs GitHub supply (location-resolved; frame-B subset)", loc="left", fontsize=10)
    save(fig, "SF12_styria_demand_supply", f"T02/T03a/T07e × location-resolved accounts and the frame-B complete-Styria subset (DS13); {DATE}")
    # SF13 marketing × data
    c24 = T("C24_marketing_data_intersection").iloc[0]; ds12 = T("DS12_marketing_x_data_intersection")
    fig, ax = plt.subplots(figsize=(8, 3.6)); ax.axis("off")
    lines = [f"Demand: marketing-analytics postings {int(ds12.iloc[0]['marketing_analytics_postings'])} of {int(ds12.iloc[0]['n']) if 'n' in ds12 else N_CORE} (Styria {int(ds12.iloc[0]['marketing_analytics_styria'])}, ads listing a Styrian site); 'marketing' wording in {ds12.iloc[0]['marketing_wording_share_T05']:.0%} of core ads; A/B testing {ds12.iloc[0]['ab_testing_share']:.1%}",
             f"Supply: {int(c24['marketing/customer/e-commerce projects'])} marketing/customer/e-commerce projects ({c24['share_of_projects']:.1%} of projects) by {int(c24['candidates_with_such_project'])} candidates ({c24['share_of_P_data']:.1%} of P_data)",
             f"  with experimentation/causal method: {int(c24['with_experimentation_or_causal'])}; with SQL+Python: {int(c24['with_sql_and_python'])}; with Power BI/Tableau: {int(c24['with_power_bi_or_tableau'])}",
             f"  bio-declared marketing-analytics family: {int(ds12.iloc[1]['T1_marketing_analytics_family'])}; bios naming marketing: {int(ds12.iloc[1]['T1_bios_naming_marketing'])}; Styrian candidates with such projects: {int(c24['styria'])}"]
    ax.text(0, 0.9, "\n".join(lines), va="top", fontsize=8.5, family="monospace"); ax.set_title("Marketing × data intersection", loc="left", fontsize=10)
    save(fig, "SF13_marketing_x_data", f"T02/T05 × C24/DS12; {DATE}")
    # SF14 transitions
    c22b = T("C22b_prior_domains"); d = c22b[c22b.population == "P_T1"].sort_values("count", ascending=False)
    barh_ci(d, "prior_domain", "share", "ci_low", "ci_high", f"Prior/other domains named in data-role bios (n = {int(d.n.iloc[0])})", "SF14_transition_domains", "weak signal: a named domain may be current, not former (C22)", color="#e08e45")
    # SF15 official supply: graduates
    o01 = T("O01_graduates_by_field_level_at"); d = o01[(o01.level == "Master") & (o01.field_code.isin(["F06", "F0613", "F0612", "F054", "F0542", "F041", "F0414", "F0311", "F071"]))]
    fig, ax = plt.subplots(figsize=(8, 4)); y = np.arange(len(d))[::-1]; ax.barh(y, d.graduates_latest, color="#555"); ax.set_yticks(y); ax.set_yticklabels(d.field); ax.set_xlabel(f"master's graduates, Austria, {int(d.latest_year.iloc[0])}")
    ax.set_title("Yearly flow of master's graduates by field (official supply context)", loc="left", fontsize=10)
    save(fig, "SF15_graduates_by_field", "Eurostat educ_uoe_grad02 (AT), ISCED-F 2013 detailed fields")
    # SF16 SO survey (newest survey year written by official_supply.py)
    so_files = sorted(TAB.glob("O04_so[0-9][0-9][0-9][0-9]_at_devtype.csv"))
    so_tag = so_files[-1].name.split("_")[1] if so_files else "so2025"
    o04 = T(f"O04_{so_tag}_at_devtype").head(15)
    barh_ci(o04.assign(lab=o04.item + o04.is_data_role.map({True: " ★", False: ""})), "lab", "share", "ci_low", "ci_high", f"Stack Overflow {so_tag[2:]}, Austrian respondents by role (n = {int(o04.n.iloc[0])}; ★ = data role)", f"SF16_{so_tag}_roles", "self-selected developer survey; ODbL", color="#555")
    print("figures written:", len(list(FIG.glob("SF*.png"))) + len(list(FIG.glob("DSF*.png"))))


if __name__ == "__main__":
    main()
