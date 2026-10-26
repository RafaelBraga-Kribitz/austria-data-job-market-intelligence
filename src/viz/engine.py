"""Figure engine for the visual decision layer (DSX house style).

Every figure in `outputs/figures/BQ*` is built through this module so that the
whole layer shares one grammar:

* **House style.** The Braga design system v2.1 through `bk-viz` (`bk_theme`):
  `bk.apply("light")` runs at import time (BKribitz type, flat surface, hairline
  axes and grid); every colour below is a design-system role, never a hex value.
* **Takeaway titles.** `finalise()` wraps the DSX `finalise_figure` helper: the
  title is a sentence with a magnitude, never a chart name, and the source line
  is a mandatory keyword (a figure without provenance is a `TypeError`).
* **One highlight colour.** `HILITE` (the `hl` accent) marks the one entity that
  concerns *this* reader's decision (Graz/Styria, the target family, the reachable
  set), at most once per chart. It is never the only channel — the highlighted
  element is always also labelled. Labels are set in ink / ink-2, never in a hue.
* **Deterministic output.** SVG is written with the DSX recipe (fixed hashsalt,
  glyphs as paths, no render timestamp) and sealed with stdlib SHA-256 into
  `outputs/figures/FIGURE-MANIFEST.yaml`; PNG is written alongside for markdown.

Chart selection follows `references/chart-selection.md` of GSD-DSX: name the
relationship first, then take an admissible mark from the catalogue. The
relationship and mark of every figure are recorded in the manifest.
"""
from __future__ import annotations

import hashlib
import json
import sys
import textwrap
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.lines  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

# Flat-script layout (no packages), as everywhere else in src/.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dsx_plotstyle import save_deterministic  # noqa: E402

import bk_theme as bk  # noqa: E402  (bk-viz: the Braga design system v2.1)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "reporting"))
import vintages  # noqa: E402  (single definition of the data vintages)
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

bk.apply("light")

# ---- palette: design-system roles only (DECISIONS.md D-036, D-053) ----------------------------
HILITE = bk.c("hl")              # the one entity that bears on this reader's decision (one per chart)
HILITE_TINT = bk.c("hl-7")       # opaque fill under a HILITE outline (no alpha in the system)
BASE = bk.c("ink-2")             # the market / the reference set (structure grey)
MUTED = bk.c("mid")              # context, de-emphasised (a mark colour; `mid` is never text)
RANGE = bk.c("rule-c")           # an interquartile band or leader drawn behind the marks
INK = bk.c("ink")                # text, reference lines
INK_2 = bk.c("ink-2")            # secondary text, error bars
SURFACE = bk.c("surface")        # the page surface: the fill of an open marker
CAT = bk.palette("categorical")  # unordered series, used in slot order; a sixth is bk.c("cat-other")
CAT_OTHER = bk.c("cat-other")
NEUTRALS = bk.neutral_ramp(4)    # parts of a whole (IBCS greys), darkest first
# two poles of one comparison (e.g. junior vs intern), from the ultramarine <-> ochre scale
_TWO = bk.palette("two")
POLE_A, POLE_B = _TWO[2], _TWO[-3]
LABEL = bk.SIZE["mono-sm"]       # the 12px floor, for dense direct labels
TEXT = bk.SIZE["mono"]           # default label size


def ordinal_colors(n: int) -> list[str]:
    """`n` steps of the sequential ultramarine scale, darkest (strongest) first."""
    return bk.palette("seq", n + 1)[:n] if n < 9 else bk.palette("seq", n)


def seq_cmap(name: str = "bk_seq"):
    """The sequential scale as a colormap, light (low) to dark (high)."""
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(name, bk.palette("seq", reverse=True))


def on_fill(face: str) -> str:
    """Ink or surface, whichever reads on a filled mark (labels inside bars and cells)."""
    return bk._contrast_ink(face)


# ---- data vintages ---------------------------------------------------------------------------
# Read from the run's own metadata so that captions follow a re-collection; the literals are the
# 2026-09 vintages and only apply when a metadata file is absent (e.g. a public clone without
# data/processed/).
def _read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _demand_vintage(default: str = "2026-09-16") -> str:
    return vintages.demand_vintage(ROOT, default)   # FALLBACK default only when outputs/market_summary.json is absent


def _supply_vintage(default: str = "2026-09-17/18") -> str:
    return vintages.supply_vintage_label(ROOT, default)   # collection day / next day; FALLBACK default only when supply_summary.json is absent


def _year_span(table_name: str, default: str) -> str:
    try:
        with open(TABLES / table_name, encoding="utf-8") as handle:
            header = handle.readline().rstrip().split(",")
            col = header.index("year")
            years = {int(line.split(",")[col]) for line in handle if line.strip()}
        return f"{min(years)}-{max(years)}"
    except (OSError, ValueError, IndexError):
        return default


DEMAND_VINTAGE = _demand_vintage()
SUPPLY_VINTAGE = _supply_vintage()
DEMAND_SOURCE = (f"Austrian data-role postings, snapshot {DEMAND_VINTAGE} "
                 "(EURES/AMS, karriere.at, LinkedIn, willhaben, jobs.at, deduplicated)")
SUPPLY_SOURCE = f"Public GitHub accounts with an Austrian location signal, {SUPPLY_VINTAGE}"
AMS_SOURCE = (f"AMS JobBarometer yearly ad counts {_year_span('JB01_yearly_counts_long.csv', '2020-2025')}, "
              "occupation class 'Data Scientist (m/w)'")
EUROSTAT_SOURCE = (f"Eurostat Job Vacancy Statistics, Austria, quarterly "
                   f"{_year_span('S02_quarter_ratios_by_year.csv', '2009-2025')}")
SNAPSHOT = f"demand {DEMAND_VINTAGE} / supply {SUPPLY_VINTAGE}"


# ---- headline Layer 1 counts with their geographic basis (OQ-19) ----------------------------------
# Two regional bases exist and must never be mixed in one sentence without a label:
#   primary state  - one state per ad (the `state` field; T03a_state_counts.csv): Styria 54, Vienna 343
#   any listed site - every ad that lists at least one site in the region (the is_styria / is_vienna /
#                     is_graz_area flags; market_summary.json styria_core / vienna_core / graz_area_core):
#                     Styria 58, Vienna 350. T02 styria_count, T03c, T04a `styria`, T07e and every
#                     *_by_styria table use this basis. The Graz commuting area is flag-only (52).
PRIMARY_BASIS = "by primary state"
ANY_SITE_BASIS = "listing at least one site in the region"


def market_counts() -> dict:
    """Headline counts from market_summary.json and T03a, keyed by basis (see the note above)."""
    summary = _read_json(ROOT / "outputs" / "market_summary.json")
    if summary is None:
        raise FileNotFoundError("outputs/market_summary.json is missing - run src/analysis/run_analysis.py first")
    c = summary["counts"]
    primary = {}
    with open(TABLES / "T03a_state_counts.csv", encoding="utf-8") as handle:
        header = handle.readline().rstrip().split(",")
        i_state, i_count = header.index("state"), header.index("count")
        for line in handle:
            cells = line.rstrip().split(",")
            if len(cells) > max(i_state, i_count):
                primary[cells[i_state]] = int(cells[i_count])
    return {
        "raw_rows": int(c["raw_rows_all_sources"]),
        "canonical": int(c["canonical_groups_all"]),
        "core": int(c["core_canonical"]),
        "core_with_description": int(c["core_with_description"]),
        "styria_primary": primary.get("Steiermark", int(c.get("styria_core_primary_state", 0))),
        "styria_any_site": int(c["styria_core"]),
        "vienna_primary": primary.get("Wien", int(c.get("vienna_core_primary_state", 0))),
        "vienna_any_site": int(c["vienna_core"]),
        "graz_area_any_site": int(c["graz_area_core"]),
        # Graz-area ads whose primary state is Styria; only present in market_summary.json from 2026-09-30 on
        "graz_area_primary_styria": (int(c["graz_area_core_primary_styria"])
                                     if c.get("graz_area_core_primary_styria") is not None else None),
    }


def styria_basis_note(counts: dict | None = None) -> str:
    """One clause that reconciles the two Styria totals, for captions and caveats."""
    c = counts or market_counts()
    extra = c["styria_any_site"] - c["styria_primary"]
    return (f"Styria = {c['styria_primary']} ads {PRIMARY_BASIS}, {c['styria_any_site']} listing at least one "
            f"Styrian site (+{extra} multi-site ads whose primary state is elsewhere)")


@dataclass
class Spec:
    """The declaration a figure is judged against (DSX visuals[] row)."""

    chart_id: str
    question: str            # the business question, in the reader's own terms
    answer: str              # the one-sentence answer, numbers included
    relationship: str        # DSX relationship vocabulary
    mark: str                # DSX chart-catalogue mark
    data_signature: str      # DSX data-input-type
    tables: list[str]        # source tables in outputs/tables/
    units: str
    anchors: list[tuple[str, str, str]] = field(default_factory=list)
    caveat: str = ""
    svg_sha256: str = ""

    @property
    def png(self) -> str:
        return f"{self.chart_id}.png"

    @property
    def svg(self) -> str:
        return f"{self.chart_id}.svg"


def wrap(text: str, width: int = 74) -> str:
    return "\n".join(textwrap.wrap(text, width=width))


def new_figure(height: float = 5.0, width: float = 9.5) -> tuple[Figure, Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def finalise(
    fig: Figure,
    *,
    title: str,
    source: str,
    units: str,
    n: str,
    note: str = "",
) -> Figure:
    """Takeaway title + mandatory source, with the layout reserved first.

    Both texts are wrapped to the figure's own width (measured in the BKribitz
    faces) and the axes rectangle is computed from the resulting line counts, so a
    long takeaway sentence or a long provenance line pushes the plot down instead
    of being clipped by it. The source note carries provenance, n and units
    together, because a chart that is screenshotted out of this repository has to
    defend itself alone. The footer opens with an ink hairline (D-044).
    """
    width_in, height_in = fig.get_size_inches()
    margin = 0.01
    span_px = (1.0 - 2 * margin) * width_in * bk.PX_PER_IN
    title_fp = bk.font("display", "bold", "project")
    source_fp = bk.font("mono", "regular", "mono-sm")
    title_text = bk.wrap_to_px(title, title_fp, span_px)
    source_text = bk.wrap_to_px(
        f"Source: {source}. {n}. Units: {units}." + (f" {note}" if note else ""),
        source_fp, span_px,
    )
    # Axis titles are prose, set in the display face (numbers and tick labels stay mono, D-053);
    # a long y-axis title in the wider mono face would run past the axes into the title band.
    for ax in fig.axes:
        for lab in (ax.xaxis.label, ax.yaxis.label):
            lab.set_fontproperties(bk.font("display", "regular", lab.get_fontsize()))
    pad = 0.12                                       # inches of air at the top and bottom edge
    title = fig.text(margin, 1.0 - pad / height_in, title_text, ha="left", va="top", color=INK,
                     linespacing=bk.LINE_HEIGHT["snug"], fontproperties=title_fp)
    source = fig.text(margin, pad / height_in, source_text, ha="left", va="bottom", color=INK_2,
                      linespacing=1.3, fontproperties=source_fp)
    # measure the set text, then reserve exactly that much: no estimate of line heights
    renderer = fig.canvas.get_renderer()
    title_h = title.get_window_extent(renderer).height / fig.dpi
    source_h = source.get_window_extent(renderer).height / fig.dpi
    top = 1.0 - (pad + title_h + 0.16) / height_in
    rule_y = (pad + source_h + 0.07) / height_in
    bottom = rule_y + 0.10 / height_in
    fig.tight_layout(rect=(0.0, bottom, 1.0, top))
    # an axis title longer than its axis is broken at the middle space, then the layout is redone
    wrapped = False
    for ax in fig.axes:
        box = ax.get_window_extent(renderer)
        for label, limit, along in ((ax.xaxis.label, box.width, "width"), (ax.yaxis.label, box.height, "height")):
            text = label.get_text()
            if not text or "\n" in text or " " not in text:
                continue
            if getattr(label.get_window_extent(renderer), along) > limit:
                mid = len(text) // 2
                cut = min((i for i, ch in enumerate(text) if ch == " "), key=lambda i: abs(i - mid))
                label.set_text(text[:cut] + "\n" + text[cut + 1:])
                wrapped = True
    if wrapped:
        fig.tight_layout(rect=(0.0, bottom, 1.0, top))
    fig.add_artist(matplotlib.lines.Line2D([margin, 1.0 - margin], [rule_y, rule_y],
                                           transform=fig.transFigure, color=INK,
                                           linewidth=bk.HAIRLINE_PT, clip_on=False))
    return fig


def spread_labels(
    positions: list[float],
    *,
    min_gap: float,
    lo: float | None = None,
    hi: float | None = None,
) -> list[float]:
    """Push overlapping label positions apart along one axis, inside [lo, hi].

    A forward pass opens each label to at least `min_gap` above its predecessor, a
    backward pass pulls the overflow back under `hi`, and both stay in rank order -
    so a label never crosses another and never leaves the axes. Labels keep their
    own position wherever the crowding allows, which is what keeps the leader lines
    short in the sparse parts of the plot.
    """
    if not positions:
        return []
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    placed = {}
    previous = None
    for i in order:
        value = positions[i]
        if lo is not None:
            value = max(value, lo)
        if previous is not None:
            value = max(value, previous + min_gap)
        placed[i] = value
        previous = value
    if hi is not None and previous is not None and previous > hi:
        previous = None
        for i in reversed(order):
            value = min(placed[i], hi if previous is None else previous - min_gap)
            if lo is not None:
                value = max(value, lo)
            placed[i] = value
            previous = value
    return [placed[i] for i in range(len(positions))]


def label_bars(ax: Axes, values, labels, *, horizontal: bool = True, pad: float = 0.01, color=None) -> None:
    """Direct value labels — they replace a legend and survive a screenshot."""
    span = (max(values) - min(0, min(values))) or 1
    for i, (v, text) in enumerate(zip(values, labels)):
        offset = span * pad
        if horizontal:
            ax.text(v + (offset if v >= 0 else -offset), i, text, va="center",
                    ha="left" if v >= 0 else "right", fontsize=LABEL, color=color or INK)
        else:
            ax.text(i, v + offset, text, ha="center", va="bottom", fontsize=LABEL, color=color or INK)


def seal(path: Path) -> str:
    """stdlib SHA-256 of the written bytes, in `dsx seal` form."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def save(fig: Figure, spec: Spec) -> Spec:
    """Write the deterministic SVG plus a PNG for markdown, and seal the SVG.

    The SVG keeps the GA-3 recipe (glyphs as paths), so it carries BKribitz
    wherever it is opened; the PNG is written at the theme's 2x density.
    """
    FIGURES.mkdir(parents=True, exist_ok=True)
    svg_path = save_deterministic(fig, FIGURES / spec.svg, metadata={"Date": None})
    fig.savefig(FIGURES / spec.png, format="png", metadata={"Software": None})
    plt.close(fig)
    spec.svg_sha256 = seal(svg_path)
    return spec


def pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def eur_k(x: float) -> str:
    return f"€{x / 1000:.1f}k"
