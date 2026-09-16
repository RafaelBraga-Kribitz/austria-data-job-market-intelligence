"""Step 6: figures -> outputs/figures/*.png  (only charts that answer a question; each has title, n, source, period)."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
S = json.load(open(ROOT / "outputs" / "market_summary.json", encoding="utf-8"))
PERIOD = f"postings collected {S['collected_at_range']['min'][:10]}; posted {S['posted_date_range']['min']} to {S['posted_date_range']['max']}"
SRC = "Sources: EURES/AMS, karriere.at, LinkedIn, willhaben, jobs.at (deduplicated)"
plt.rcParams.update({"figure.dpi": 130, "font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def foot(ax, n, extra=""):
    ax.annotate(f"n = {n}. {SRC}. {PERIOD}. {extra}", xy=(0, -0.28), xycoords="axes fraction", fontsize=6.5, color="#555", wrap=True)


def barh(df, cat, val, title, fname, n, xlabel, top=25, extra="", ci=None):
    d = df.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.28 * len(d) + 1.6))
    ax.barh(d[cat].astype(str), d[val], color="#2b6cb0")
    if ci and ci[0] in d:
        ax.errorbar(d[val], d[cat].astype(str), xerr=[d[val] - d[ci[0]], d[ci[1]] - d[val]], fmt="none", ecolor="#999", capsize=2, lw=0.8)
    ax.set_xlabel(xlabel); ax.set_title(title, loc="left", fontsize=10, weight="bold")
    for i, v in enumerate(d[val]):
        ax.text(v, i, f" {v:.0%}" if xlabel.startswith("Share") else f" {int(v)}", va="center", fontsize=7)
    foot(ax, n, extra)
    fig.tight_layout(); fig.savefig(FIG / fname, bbox_inches="tight"); plt.close(fig)


def main():
    c = S["counts"]
    # F01 role families
    fam = pd.read_csv(TAB / "T02_role_family_counts.csv")
    barh(fam, "role_family", "count", "Core data-role postings by role family (Austria)", "F01_role_families.png", c["core_canonical"], "Unique postings", extra="Family = rule-based title normalization (config/role_taxonomy.json).")
    # F02 state distribution
    st = pd.read_csv(TAB / "T03a_state_counts.csv")
    barh(st, "state", "count", "Where are the core data-role postings? (by Bundesland)", "F02_states.png", c["core_canonical"], "Unique postings", extra="State from explicit location, NUTS-3 code or address in text.")
    # F03 Styria vs Austria family mix
    fam2 = fam.copy(); fam2["Austria share"] = fam2["count"] / fam2["count"].sum(); fam2["Styria share"] = fam2["styria_count"] / max(fam2["styria_count"].sum(), 1)
    fig, ax = plt.subplots(figsize=(8, 4.2)); x = np.arange(len(fam2)); w = 0.38
    ax.bar(x - w / 2, fam2["Austria share"], w, label=f"Austria (n={int(fam2['count'].sum())})", color="#2b6cb0")
    ax.bar(x + w / 2, fam2["Styria share"], w, label=f"Styria (n={int(fam2['styria_count'].sum())})", color="#dd6b20")
    ax.set_xticks(x); ax.set_xticklabels(fam2.role_family, rotation=30, ha="right"); ax.set_ylabel("Share of postings in scope"); ax.legend()
    ax.set_title("Role-family mix: Styria vs Austria", loc="left", fontsize=10, weight="bold"); foot(ax, c["core_canonical"], "Small Styrian n: interpret differences cautiously.")
    fig.tight_layout(); fig.savefig(FIG / "F03_styria_vs_austria_families.png", bbox_inches="tight"); plt.close(fig)
    # F04 tech skills
    sk = pd.read_csv(TAB / "T05_skills_all_tech.csv")
    barh(sk, "skill", "share", "Most requested technologies / methods (share of core postings with description)", "F04_tech_skills.png", int(sk.n.iloc[0]), "Share of postings", top=30, extra="Wilson 95% CI shown.", ci=("ci_low", "ci_high"))
    # F05 skills Styria vs rest
    sks = pd.read_csv(TAB / "T05_skills_all_tech_by_styria.csv")
    piv = sks.pivot_table(index="skill", columns="styria_flag", values="share").fillna(0)
    top = sk.skill.head(20).tolist(); piv = piv.loc[[t for t in top if t in piv.index]].iloc[::-1]
    ns = sks.groupby("styria_flag").n.first().to_dict()
    fig, ax = plt.subplots(figsize=(8, 6.5)); y = np.arange(len(piv)); w = 0.4
    for i, (col, color) in enumerate([("Rest of Austria", "#2b6cb0"), ("Styria", "#dd6b20")]):
        if col in piv:
            ax.barh(y + (i - 0.5) * w, piv[col], w, label=f"{col} (n={ns.get(col, 0)})", color=color)
    ax.set_yticks(y); ax.set_yticklabels(piv.index); ax.set_xlabel("Share of postings with description"); ax.legend()
    ax.set_title("Technology demand: Styria vs rest of Austria (top-20 skills)", loc="left", fontsize=10, weight="bold"); foot(ax, sum(ns.values()))
    fig.tight_layout(); fig.savefig(FIG / "F05_skills_styria_vs_rest.png", bbox_inches="tight"); plt.close(fig)
    # F06 German requirement by family
    g = pd.read_csv(TAB / "T07_german_requirement_by_role_family.csv")
    piv = g.pivot_table(index="role_family", columns="german_requirement", values="share").fillna(0)
    order = [x for x in ["required", "required_implied", "german_or_english", "preferred", "mentioned", "explicitly_not_required", "not_mentioned"] if x in piv]
    piv = piv[order]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    piv.plot(kind="barh", stacked=True, ax=ax, colormap="RdYlGn_r" if False else "viridis", width=0.7)
    ax.set_xlabel("Share of postings with description"); ax.set_title("German-language requirement by role family", loc="left", fontsize=10, weight="bold")
    ax.legend(fontsize=7, loc="lower right"); foot(ax, int(g.n.sum() // max(len(piv.columns), 1)), "Classification from context around language mentions; see docs/methodology.md.")
    fig.tight_layout(); fig.savefig(FIG / "F06_german_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F07 salary by family (min annual)
    sal = pd.read_csv(TAB / "T09b_salary_by_role_family.csv").sort_values("min_median")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(sal.role_family, sal.min_median, color="#2b6cb0")
    ax.errorbar(sal.min_median, sal.role_family, xerr=[sal.min_median - sal.min_p25, sal.min_p75 - sal.min_median], fmt="none", ecolor="#999", capsize=3)
    for i, r in enumerate(sal.itertuples()):
        ax.text(r.min_median, i, f"  {r.min_median:,.0f} € (n={int(r.n)})", va="center", fontsize=7)
    ax.set_xlabel("Advertised MINIMUM annual gross salary, EUR (median, IQR); monthly ×14"); ax.set_title("Advertised minimum salary by role family", loc="left", fontsize=10, weight="bold")
    foot(ax, int(sal.n.sum()), "Advertised minimums (mostly collective-agreement floors), not offers or survey medians.")
    fig.tight_layout(); fig.savefig(FIG / "F07_salary_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F08 remote by family
    r = pd.read_csv(TAB / "T10_remote_by_family.csv")
    piv = r.pivot_table(index="role_family", columns="remote_type", values="share").fillna(0)
    order = [x for x in ["remote", "hybrid", "hybrid_or_flexible", "on_site", "unknown"] if x in piv]
    fig, ax = plt.subplots(figsize=(8, 4)); piv[order].plot(kind="barh", stacked=True, ax=ax, colormap="viridis", width=0.7)
    ax.set_xlabel("Share of postings with description"); ax.set_title("Work model mentioned in postings, by role family", loc="left", fontsize=10, weight="bold"); ax.legend(fontsize=7, loc="lower right")
    foot(ax, int(r.groupby("role_family").n.first().sum()), "'unknown' = no remote/home-office statement in the ad.")
    fig.tight_layout(); fig.savefig(FIG / "F08_remote_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F09 seniority
    se = pd.read_csv(TAB / "T08_seniority_overall.csv")
    barh(se, "seniority", "count", "Seniority signal in titles (core postings)", "F09_seniority.png", int(se.n.iloc[0]), "Unique postings", extra="'unspecified' = no seniority word in the title.")
    # F10 employers Styria
    es = pd.read_csv(TAB / "T04a_employers_styria.csv").head(25)
    barh(es, "example_company", "styria", "Employers with most core data-role postings in Styria", "F10_employers_styria.png", c["styria_core"], "Unique postings in Styria")
    # F11 JobBarometer yearly (if available)
    p = TAB / "JB01_yearly_counts_long.csv"
    if p.exists():
        L = pd.read_csv(p)
        sel = L[L.beruf.str.contains("Data Scientist|Datenbank|Data-Warehouse|Statistik|Wirtschaftsinformatik|Business-Intelligence|Datenanaly", regex=True, na=False)]
        for bl, name in [("AT", "Austria"), ("AT22", "Styria")]:
            sub = sel[sel.bl == bl].pivot_table(index="year", columns="beruf", values="ads")
            if sub.empty:
                continue
            fig, ax = plt.subplots(figsize=(8, 4)); sub.plot(ax=ax, marker="o")
            ax.set_ylabel("Online job ads per year (AMS count)"); ax.set_title(f"AMS JobBarometer: yearly online ads for data occupations, {name}", loc="left", fontsize=10, weight="bold"); ax.legend(fontsize=7)
            ax.annotate("Source: AMS JobBarometer (jobbarometer.ams.at), 'Inserate aus dem Internet'. AMS occupation classes, not job titles. '<20' censored.", xy=(0, -0.22), xycoords="axes fraction", fontsize=6.5, color="#555")
            fig.tight_layout(); fig.savefig(FIG / f"F11_jobbarometer_{name.lower()}.png", bbox_inches="tight"); plt.close(fig)
    # F12 co-occurrence heatmap (top 15)
    co = pd.read_csv(TAB / "T06_cooccurrence_pairs.csv")
    top = sk.skill.head(15).tolist()
    M = pd.DataFrame(0.0, index=top, columns=top)
    for r_ in co.itertuples():
        if r_.skill_a in top and r_.skill_b in top:
            M.loc[r_.skill_a, r_.skill_b] = r_.share_of_postings; M.loc[r_.skill_b, r_.skill_a] = r_.share_of_postings
    for s_ in top:
        M.loc[s_, s_] = float(sk.set_index("skill").share.get(s_, 0))
    fig, ax = plt.subplots(figsize=(8, 7)); im = ax.imshow(M.values, cmap="Blues")
    ax.set_xticks(range(len(top))); ax.set_xticklabels(top, rotation=60, ha="right", fontsize=7); ax.set_yticks(range(len(top))); ax.set_yticklabels(top, fontsize=7)
    for i in range(len(top)):
        for j in range(len(top)):
            ax.text(j, i, f"{M.values[i, j]:.0%}", ha="center", va="center", fontsize=5.5, color="white" if M.values[i, j] > 0.3 else "black")
    ax.set_title("Skill co-occurrence: share of postings mentioning both (diagonal = single skill)", loc="left", fontsize=10, weight="bold")
    ax.annotate(f"n = {int(sk.n.iloc[0])} core postings with description. {SRC}.", xy=(0, -0.3), xycoords="axes fraction", fontsize=6.5, color="#555")
    fig.tight_layout(); fig.savefig(FIG / "F12_cooccurrence.png", bbox_inches="tight"); plt.close(fig)
    print("figures:", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
