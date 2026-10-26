"""Step 6: figures -> outputs/figures/*.png  (only charts that answer a question; each has title, n, source, period)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "viz"))
# The Braga design system v2.1 (bk-viz): engine applies bk.apply("light") and names every colour as a role.
from engine import (  # noqa: E402
    BASE, HILITE, INK, INK_2, LABEL, NEUTRALS, POLE_A, POLE_B, bk, on_fill, ordinal_colors, seq_cmap,
)

TAB = ROOT / "outputs" / "tables"
FIG = ROOT / "outputs" / "figures"
S = json.load(open(ROOT / "outputs" / "market_summary.json", encoding="utf-8"))
PERIOD = f"postings collected {S['collected_at_range']['min'][:10]}; core ads posted {S['posted_date_range']['min']} to {S['posted_date_range']['max']}"
SRC = "Sources: EURES/AMS, karriere.at, LinkedIn, willhaben, jobs.at (deduplicated)"
TITLE_FP = bk.font("display", "bold", "body")   # chart title; type sizes never below the 12px floor (LABEL)

def set_title(ax, text):
    """Chart title in the display face, wrapped to the figure so it is never clipped."""
    width_px = ax.figure.get_size_inches()[0] * bk.PX_PER_IN * 0.72
    ax.set_title(bk.wrap_to_px(text, TITLE_FP, width_px), loc="left", fontproperties=TITLE_FP)



def foot(ax, n, extra=""):
    # Anchored below the whole figure (not at a fixed axes fraction) so rotated tick labels
    # can never overlap it; bbox_inches="tight" at save time includes it in the PNG.
    # (Fix made in the public repository on 2026-09-17, ported back 2026-09-30.)
    ax.figure.text(0.01, -0.02, f"n = {n}. {SRC}. {PERIOD}. {extra}", fontsize=LABEL, color=INK_2, ha="left", va="top", wrap=True)


def barh(df, cat, val, title, fname, n, xlabel, top=25, extra="", ci=None):
    d = df.head(top).iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 0.28 * len(d) + 1.6))
    ax.barh(d[cat].astype(str), d[val], color=BASE)
    if ci and ci[0] in d:
        ax.errorbar(d[val], d[cat].astype(str), xerr=[d[val] - d[ci[0]], d[ci[1]] - d[val]], fmt="none", ecolor=INK_2, capsize=2, lw=0.8)
    ax.set_xlabel(xlabel); set_title(ax, title)
    for i, v in enumerate(d[val]):
        ax.text(v, i, f" {v:.0%}" if xlabel.startswith("Share") else f" {int(v)}", va="center", fontsize=LABEL, color=INK)
    foot(ax, n, extra)
    fig.tight_layout(); fig.savefig(FIG / fname, bbox_inches="tight"); plt.close(fig)


def main():
    FIG.mkdir(parents=True, exist_ok=True)
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
    ax.bar(x - w / 2, fam2["Austria share"], w, label=f"Austria (n={int(fam2['count'].sum())})", color=BASE)
    ax.bar(x + w / 2, fam2["Styria share"], w, label=f"Styria (n={int(fam2['styria_count'].sum())})", color=HILITE)
    ax.set_xticks(x); ax.set_xticklabels(fam2.role_family, rotation=30, ha="right"); ax.set_ylabel("Share of postings in scope"); ax.legend()
    set_title(ax, "Role-family mix: Styria vs Austria"); foot(ax, c["core_canonical"], "Small Styrian n: interpret differences cautiously.")
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
    for i, (col, color) in enumerate([("Rest of Austria", BASE), ("Styria", HILITE)]):
        if col in piv:
            ax.barh(y + (i - 0.5) * w, piv[col], w, label=f"{col} (n={ns.get(col, 0)})", color=color)
    ax.set_yticks(y); ax.set_yticklabels(piv.index); ax.set_xlabel("Share of postings with description"); ax.legend()
    set_title(ax, "Technology demand: Styria vs rest of Austria (top-20 skills)"); foot(ax, sum(ns.values()))
    fig.tight_layout(); fig.savefig(FIG / "F05_skills_styria_vs_rest.png", bbox_inches="tight"); plt.close(fig)
    # F06 German requirement by family
    g = pd.read_csv(TAB / "T07_german_requirement_by_role_family.csv")
    piv = g.pivot_table(index="role_family", columns="german_requirement", values="share").fillna(0)
    order = [x for x in ["required", "required_implied", "german_or_english", "preferred", "mentioned", "explicitly_not_required", "not_mentioned"] if x in piv]
    piv = piv[order]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    # requirement strength is ordinal: the sequential scale, strongest wording darkest
    piv.plot(kind="barh", stacked=True, ax=ax, color=ordinal_colors(len(piv.columns)), width=0.7)
    ax.set_xlabel("Share of postings with description"); set_title(ax, "German-language requirement by role family")
    ax.legend(fontsize=LABEL, loc="lower left", bbox_to_anchor=(1.01, 0.0)); foot(ax, int(g.n.sum() // max(len(piv.columns), 1)), "Classification from context around language mentions; see docs/methodology.md.")
    fig.tight_layout(); fig.savefig(FIG / "F06_german_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F07 salary by family (min annual)
    sal = pd.read_csv(TAB / "T09b_salary_by_role_family.csv").sort_values("min_median")
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(sal.role_family, sal.min_median, color=BASE)
    ax.errorbar(sal.min_median, sal.role_family, xerr=[sal.min_median - sal.min_p25, sal.min_p75 - sal.min_median], fmt="none", ecolor=INK_2, capsize=3)
    for i, r in enumerate(sal.itertuples()):
        ax.text(r.min_median, i, f"  {r.min_median:,.0f} € (n={int(r.n)})", va="center", fontsize=LABEL, color=INK)
    ax.set_xlabel("Advertised MINIMUM annual gross salary, EUR (median, IQR); monthly ×14"); set_title(ax, "Advertised minimum salary by role family")
    foot(ax, int(sal.n.sum()), "Advertised minimums (mostly collective-agreement floors), not offers or survey medians.")
    fig.tight_layout(); fig.savefig(FIG / "F07_salary_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F08 remote by family
    r = pd.read_csv(TAB / "T10_remote_by_family.csv")
    piv = r.pivot_table(index="role_family", columns="remote_type", values="share").fillna(0)
    order = [x for x in ["remote", "hybrid", "hybrid_or_flexible", "on_site", "unknown"] if x in piv]
    # fully remote is the one highlight; the other parts of the whole are the IBCS structure greys
    work_color = {"remote": HILITE, "hybrid": NEUTRALS[0], "hybrid_or_flexible": NEUTRALS[1], "on_site": NEUTRALS[2], "unknown": NEUTRALS[3]}
    fig, ax = plt.subplots(figsize=(8, 4)); piv[order].plot(kind="barh", stacked=True, ax=ax, color=[work_color[k] for k in order], width=0.7)
    ax.set_xlabel("Share of postings with description"); set_title(ax, "Work model mentioned in postings, by role family"); ax.legend(fontsize=LABEL, loc="lower left", bbox_to_anchor=(1.01, 0.0))
    foot(ax, int(r.groupby("role_family").n.first().sum()), "'unknown' = no remote/home-office statement in the ad.")
    fig.tight_layout(); fig.savefig(FIG / "F08_remote_by_family.png", bbox_inches="tight"); plt.close(fig)
    # F09 seniority
    se = pd.read_csv(TAB / "T08_seniority_overall.csv")
    barh(se, "seniority", "count", "Seniority signal in titles (core postings)", "F09_seniority.png", int(se.n.iloc[0]), "Unique postings", extra="'unspecified' = no seniority word in the title.")
    # F10 employers Styria
    es = pd.read_csv(TAB / "T04a_employers_styria.csv").head(25)
    barh(es, "example_company", "styria", "Employers with most core data-role postings in Styria", "F10_employers_styria.png", c["styria_core"], "Postings listing a Styrian site (any-site basis)")
    # F11 JobBarometer yearly (if available)
    p = TAB / "JB01_yearly_counts_long.csv"
    if p.exists():
        L = pd.read_csv(p)
        sel = L[L.beruf.str.contains("Data Scientist|Datenbank|Data-Warehouse|Statistik|Wirtschaftsinformatik|Business-Intelligence|Datenanaly", regex=True, na=False)]
        for bl, name in [("AT", "Austria"), ("AT22", "Styria")]:
            sub = sel[sel.bl == bl].pivot_table(index="year", columns="beruf", values="ads")
            if sub.empty:
                continue
            # occupations are unordered: categorical slots in order, a sixth and later series is cat-other
            fig, ax = plt.subplots(figsize=(10, 4)); sub.plot(ax=ax, marker="o", color=bk.palette("categorical", len(sub.columns)))
            ax.set_ylabel("Online job ads per year (AMS count)"); set_title(ax, f"AMS JobBarometer: yearly online ads for data occupations, {name}"); ax.legend(fontsize=LABEL, loc="upper left", bbox_to_anchor=(1.01, 1.0))
            ax.annotate("Source: AMS JobBarometer (jobbarometer.ams.at), 'Inserate aus dem Internet'. AMS occupation classes, not job titles. '<20' censored.", xy=(0, -0.30), xycoords="axes fraction", fontsize=LABEL, color=INK_2)
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
    cmap = seq_cmap()
    fig, ax = plt.subplots(figsize=(12, 10.5)); im = ax.imshow(M.values, cmap=cmap)   # cells sized for 12px labels; ax.grid(False)
    ax.set_xticks(range(len(top))); ax.set_xticklabels(top, rotation=60, ha="right", fontsize=LABEL); ax.set_yticks(range(len(top))); ax.set_yticklabels(top, fontsize=LABEL)
    for i in range(len(top)):
        for j in range(len(top)):
            ax.text(j, i, f"{M.values[i, j]:.0%}", ha="center", va="center", fontsize=LABEL, color=on_fill(cmap(im.norm(M.values[i, j]))))
    set_title(ax, "Skill co-occurrence: share of postings mentioning both (diagonal = single skill)")
    ax.annotate(f"n = {int(sk.n.iloc[0])} core postings with description. {SRC}.", xy=(0, -0.38), xycoords="axes fraction", fontsize=LABEL, color=INK_2)
    fig.tight_layout(); fig.savefig(FIG / "F12_cooccurrence.png", bbox_inches="tight"); plt.close(fig)
    # F14 intern vs junior skill divergence (top |pp|)
    p17 = TAB / "T17_skill_divergence_intern_vs_junior.csv"
    if p17.exists():
        d17 = pd.read_csv(p17)
        d17 = d17[d17.junior_minus_intern_pp.notna()].copy()
        d17["abs_pp"] = d17.junior_minus_intern_pp.abs()
        d17 = d17.sort_values("abs_pp", ascending=False).head(16).iloc[::-1]
        if len(d17):
            fig, ax = plt.subplots(figsize=(8, 0.32 * len(d17) + 1.8))
            # two poles of one comparison, from the ultramarine <-> ochre scale
            colors = [POLE_B if v > 0 else POLE_A for v in d17.junior_minus_intern_pp]
            ax.barh(d17.skill.astype(str), d17.junior_minus_intern_pp, color=colors)
            ax.axvline(0, color=INK, lw=0.6)
            ax.set_xlabel("Junior share − intern share (percentage points)")
            set_title(ax, "What changes from intern/Werkstudent to junior titles")
            n_i = int(d17.intern_n.iloc[0]) if "intern_n" in d17 else 0
            n_j = int(d17.junior_n.iloc[0]) if "junior_n" in d17 else 0
            foot(ax, n_i + n_j, f"Intern n={n_i}, junior n={n_j}; cells with n<30 are tentative (T17). Ochre = more common in junior ads.")
            fig.tight_layout(); fig.savefig(FIG / "F14_intern_vs_junior_skills.png", bbox_inches="tight"); plt.close(fig)
    print("figures:", sorted(p.name for p in FIG.glob("*.png")))


if __name__ == "__main__":
    main()
