"""Paper assets: reproduction-fidelity table (T2), per-instance appendix
table (T8) and figures F1-F4 as plain-SVG (standard library only).

    python3 -m cch.paper_assets

writes docs/paper-t2-fidelity.csv, docs/paper-t8-per-instance.csv and
docs/figures/f{1,2,3,4}-*.svg. T2 is compiled from the verified reproduction
records hardcoded below (each row cites its evidence); T8 and the
figures are computed from docs/stage*-*.csv.
"""

from __future__ import annotations

import csv
from math import sqrt
from statistics import mean, stdev
from xml.etree import ElementTree

from burke_bf import load_instance

from .experiment import _instance_paths, _lower_bound

# ---------------------------------------------------------------- tables

T2_ROWS = [
    # paper, venue, benchmark scope, outcome, evidence
    ("BF (Burke, Kendall & Whitwell 2004)", "Oper. Res. 52(4):655-671",
     "C7P1-P3 vs Tables 3/5",
     "all exact after the SN-clarification fix (commit de59705)",
     "TWBF 复现状态 / burke_bf"),
    ("BBF (Asik & Ozcan 2009)", "Ann. Oper. Res. 172:405-427",
     "M1 + N1-N13 + C1-C7 (35 instances)",
     "20 exact, 8 better (1-3), 7 worse (1-2); M1 walkthrough step-exact",
     "BBF 复现状态"),
    ("TCBF/WPBF (Yehia et al. 2024)", "EIJEST 47:92-100",
     "N1-N13 + C1-C7 (34 instances)",
     "negative result: base BFA(LM) 33/34 exact, mechanisms 9/34 and 7/34; "
     "max-area harm re-confirmed at component level (stage-1 t=-11.9)",
     "IBF 复现状态"),
    ("TWBF (Verstichel et al. 2013)", "ITOR 20(5):711-730",
     "N1-N13 + C1-C7 (34 instances)",
     "24 exact, 4 better (1-4), 6 worse (1-2)",
     "TWBF 复现状态"),
    ("SH (Wei et al. 2011)", "EJOR 215(2):337-346",
     "C1-C7 + N1-N13 vs Table 2",
     "semantics double-verified (3000 random tests vs naive reference); "
     "IDBS 16/21 optimal @60s, 17/21 @300s (compute-limited, Python)",
     "SKY 复现状态"),
    ("ISH (Wei et al. 2017)", "Comput. Oper. Res. 80:113-127",
     "C1-C7 + N1-N13 vs Tables 5/6 best.gap",
     "29 exact + 1 rounding; 4 worse (+1.1 to +3.3)",
     "ISH 复现状态"),
    ("Level family (Ortmann et al. 2010)", "EJOR 203(2):306-315",
     "C1-C7 + T1-T7 + N1-N7 category gaps",
     "FFDH 17/21 categories exact (C5-C7 +8 to +13, unresolved); "
     "SC/SCR best-fitting; SASm weakest",
     "LVL 复现状态"),
    ("FH (Leung & Zhang 2011)", "ESWA 38(10):13032-13042",
     "C1-C7 + N1-N13 (34 instances)",
     "25 exact, 8 within +/-2 (incl. BKW13=960 exact)",
     "FH 复现状态"),
]


def write_t2(path: str) -> None:
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["paper", "venue", "benchmark_scope", "outcome", "evidence"])
        writer.writerows(T2_ROWS)


def write_t8(runs_dir: str, path: str) -> None:
    def load(name: str) -> dict[tuple[str, str, str, str], int]:
        table: dict[tuple[str, str, str, str], int] = {}
        with open(f"{runs_dir}/{name}", newline="") as handle:
            for row in csv.DictReader(handle):
                table[(row["instance"], row["ordering"], row["selection"],
                       row["placement"])] = int(row["height"])
        return table

    base = load("stage1-runs.csv")
    tower = load("stage2-tower-runs.csv")
    vn = load("stage2-vn-runs.csv")
    vt = load("stage2-vntower-runs.csv")

    with open(f"{runs_dir}/stage3-baselines.csv", newline="") as handle:
        baseline_rows = list(csv.DictReader(handle))
    algorithms = sorted({row["algorithm"] for row in baseline_rows})
    baseline = {(row["instance"], row["algorithm"]): row["height"]
                for row in baseline_rows}

    all_cells = [base, tower, vn, vt]
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["instance", "data_set", "n_items", "strip_width", "lower_bound",
             "reference_height"]
            + algorithms
            + ["cch_best_single", "cch_enum864"]
        )
        for data_set, instance_path in _instance_paths():
            instance = load_instance(instance_path)
            name = instance.name
            keys = [(o, s, p) for (i, o, s, p) in base if i == name]
            enum_best = min(
                min(table[(name, o, s, p)] for table in all_cells)
                for (o, s, p) in keys
            )
            best_single = tower[(name, "perimeter", "fitness-number", "SN")]
            writer.writerow(
                [name, data_set, len(instance.items), instance.strip_width,
                 _lower_bound(instance), instance.reference_height or ""]
                + [baseline.get((name, alg), "") for alg in algorithms]
                + [best_single, enum_best]
            )


# ---------------------------------------------------------------- figures

INK = "#222222"
ACCENT = "#b03a2e"
MUTED = "#888888"


def _svg(width: int, height: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" font-family="Helvetica, Arial, sans-serif" '
        f'font-size="11">{body}</svg>\n'
    )


def _text(x: float, y: float, content: str, size: int = 11,
          anchor: str = "start", fill: str = INK) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'text-anchor="{anchor}" fill="{fill}">{content}</text>'
    )


def figure_f1(path: str) -> None:
    """Skyline mechanics: lowest gap, neighbours, placement, raising."""

    cell = 26
    skyline = [2, 2, 5, 5, 3, 1, 1, 1, 4, 4]
    origin_x, origin_y = 60, 200
    top = 6

    def px(unit_x: float) -> float:
        return origin_x + unit_x * cell

    def py(unit_h: float) -> float:
        return origin_y - unit_h * cell

    parts = [
        # strip sides
        f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(0)}" y2="{py(top)}" stroke="{INK}"/>',
        f'<line x1="{px(10)}" y1="{py(0)}" x2="{px(10)}" y2="{py(top)}" stroke="{INK}"/>',
        f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(10)}" y2="{py(0)}" stroke="{INK}"/>',
        _text(px(5), origin_y + 18, "strip floor (width W)", 10, "middle"),
    ]
    # packed profile (filled region under the skyline; step polygon, not
    # diagonals: emit both endpoints of each unit segment)
    points = [f"{px(0):.1f},{py(0):.1f}"]
    for x, h in enumerate(skyline):
        points.append(f"{px(x):.1f},{py(h):.1f}")
        points.append(f"{px(x + 1):.1f},{py(h):.1f}")
    points.append(f"{px(10):.1f},{py(0):.1f}")
    parts.append(
        f'<polygon points="{" ".join(points)}" fill="#dde3ea" stroke="{INK}" '
        f'stroke-width="1.2"/>'
    )
    parts.append(_text(px(1.2), py(1.0), "packed items", 10, "start", MUTED))
    # lowest gap: units 5..8, the open space above the floor at height 1
    parts.append(
        f'<rect x="{px(5):.1f}" y="{py(2):.1f}" width="{3 * cell}" '
        f'height="{cell}" fill="none" stroke="{ACCENT}" stroke-width="2" '
        f'stroke-dasharray="4 3"/>'
    )
    parts.append(_text(px(6.5), py(2) + cell / 2 + 4, "lowest gap", 11, "middle", ACCENT))
    # neighbours: unit 4 (left, h=3) and units 8-9 (right, h=4)
    parts.append(_text(px(4.5), py(3) - 6, "left neighbour", 10, "middle", MUTED))
    parts.append(_text(px(9.0), py(4) - 6, "right neighbour", 10, "middle", MUTED))
    # candidate rectangle with drop arrow; label on two lines inside it
    parts.append(
        f'<rect x="{px(5):.1f}" y="{py(6):.1f}" width="{2 * cell}" '
        f'height="{2 * cell}" fill="#f5d6d0" stroke="{ACCENT}" '
        f'stroke-width="1.5"/>'
    )
    parts.append(_text(px(6.0), py(5) - 2, "selected", 9, "middle", ACCENT))
    parts.append(_text(px(6.0), py(5) + 10, "item", 9, "middle", ACCENT))
    parts.append(
        f'<line x1="{px(6)}" y1="{py(4.6)}" x2="{px(6)}" y2="{py(2.3)}" '
        f'stroke="{ACCENT}" stroke-width="1.5" marker-end="url(#arrow)"/>'
    )
    parts.append(
        '<defs><marker id="arrow" markerWidth="8" markerHeight="8" '
        'refX="4" refY="4" orient="auto">'
        f'<path d="M0,0 L8,4 L0,8 z" fill="{ACCENT}"/></marker></defs>'
    )
    # raising rule annotation
    parts.append(
        _text(px(0), py(6.6),
              "if no item fits the gap: raise it to the lower neighbour",
              10, "start", MUTED)
    )
    parts.append(_text(px(0), py(7.0), "D4 policy decides: left side vs right side", 10, "start", MUTED))
    with open(path, "w") as handle:
        handle.write(_svg(400, 250, "".join(parts)))


def _load_gaps(runs_dir: str, name: str) -> dict[tuple[str, str, str, str], float]:
    table: dict[tuple[str, str, str, str], float] = {}
    with open(f"{runs_dir}/{name}", newline="") as handle:
        for row in csv.DictReader(handle):
            table[(row["instance"], row["ordering"], row["selection"],
                   row["placement"])] = float(row["gap_pct"])
    return table


def figure_f2(runs_dir: str, path: str) -> None:
    """Forest plot of marginal main effects (mean gap pct +/- 95% CI)."""

    gap = _load_gaps(runs_dir, "stage1-runs.csv")
    instances = sorted({key[0] for key in gap})
    axes = (
        ("ordering", 1, ["width", "maxside", "perimeter", "diagonal", "area", "height"]),
        ("selection", 2, ["widest-fit", "first-fit", "tre", "fitness-number", "nre", "max-area"]),
        ("placement", 3, ["TN", "MinD", "MaxD", "LM", "RM", "SN"]),
    )
    lo, hi = 9.0, 20.0

    def sx(value: float) -> float:
        return 170 + (value - lo) / (hi - lo) * 400

    parts: list[str] = []
    y = 30
    panel_titles = {"ordering": "D2 ordering", "selection": "D3 selection", "placement": "D4 placement"}
    for axis, index, levels in axes:
        parts.append(_text(20, y - 8, panel_titles[axis], 12))
        for level in levels:
            per_instance = []
            for instance in instances:
                values = [v for key, v in gap.items()
                          if key[0] == instance and key[index] == level]
                per_instance.append(mean(values))
            centre = mean(per_instance)
            ci = 1.96 * stdev(per_instance) / sqrt(len(per_instance))
            colour = ACCENT if level in ("height", "max-area", "widest-fit", "TN") else INK
            parts.append(_text(160, y + 4, level, 10, "end", colour))
            parts.append(
                f'<line x1="{sx(centre - ci):.1f}" y1="{y}" x2="{sx(centre + ci):.1f}" '
                f'y2="{y}" stroke="{colour}" stroke-width="1.5"/>'
            )
            parts.append(
                f'<circle cx="{sx(centre):.1f}" cy="{y}" r="4" fill="{colour}"/>'
            )
            parts.append(_text(sx(centre + ci) + 8, y + 4, f"{centre:.2f}", 9, "start", MUTED))
            y += 22
        y += 14
    for tick in range(int(lo), int(hi) + 1, 2):
        parts.append(
            f'<line x1="{sx(tick):.1f}" y1="20" x2="{sx(tick):.1f}" y2="{y - 6}" '
            f'stroke="#dddddd" stroke-dasharray="2 3"/>'
        )
        parts.append(_text(sx(tick), y + 6, str(tick), 9, "middle", MUTED))
    parts.append(_text(sx((lo + hi) / 2), y + 22, "mean gap to lower bound (%)", 10, "middle"))
    with open(path, "w") as handle:
        handle.write(_svg(730, y + 34, "".join(parts)))


def figure_f3(runs_dir: str, path: str) -> None:
    """Vertical niche as a diversity generator: means vs enumeration frontier."""

    base = _load_gaps(runs_dir, "stage1-runs.csv")
    vn = _load_gaps(runs_dir, "stage2-vn-runs.csv")
    instances = sorted({key[0] for key in base})
    sels = ["widest-fit", "first-fit", "tre", "nre", "fitness-number", "max-area"]
    ords = ["width", "height", "area", "perimeter", "maxside", "diagonal"]
    pols = ["LM", "RM", "TN", "SN", "MinD", "MaxD"]
    all_cells = [(o, s, p) for o in ords for s in sels for p in pols]

    lo, hi = 9.0, 20.0

    def sx(value: float) -> float:
        return 150 + (value - lo) / (hi - lo) * 240

    parts = [_text(20, 18, "(a) per-selection marginal mean: base -> +vn", 12)]
    y = 40
    for sel in sels:
        mb = mean(v for key, v in base.items() if key[2] == sel)
        mv = mean(v for key, v in vn.items() if key[2] == sel)
        worse = mv > mb
        colour = ACCENT if worse else "#1e8449"
        parts.append(_text(146, y + 4, sel, 10, "end"))
        parts.append(
            f'<line x1="{sx(mb):.1f}" y1="{y}" x2="{sx(mv):.1f}" '
            f'y2="{y}" stroke="{colour}" stroke-width="1.5"/>'
        )
        parts.append(f'<circle cx="{sx(mb):.1f}" cy="{y}" r="4" fill="{INK}"/>')
        # shape redundancy: red down-triangle = worse, green up-triangle = better
        if worse:
            tri = (f'{sx(mv) - 6:.1f},{y - 4:.1f} {sx(mv) + 6:.1f},{y - 4:.1f} '
                   f'{sx(mv):.1f},{y + 5:.1f}')
        else:
            tri = (f'{sx(mv) - 6:.1f},{y + 4:.1f} {sx(mv) + 6:.1f},{y + 4:.1f} '
                   f'{sx(mv):.1f},{y - 5:.1f}')
        parts.append(f'<polygon points="{tri}" fill="{colour}"/>')
        parts.append(_text(sx(max(mb, mv)) + 8, y + 4,
                           f"{mb:.2f} -> {mv:.2f}", 9, "start", colour))
        y += 24
    # legend: black dot = base; red down-triangle = +vn worse; green up = better
    lx = sx(lo)
    parts.append(f'<circle cx="{lx + 5}" cy="{y + 6}" r="4" fill="{INK}"/>')
    parts.append(_text(lx + 14, y + 10, "= base;", 9, "start", MUTED))
    parts.append(f'<polygon points="{lx + 60},{y + 2} {lx + 72},{y + 2} {lx + 66},{y + 11}" '
                 f'fill="{ACCENT}"/>')
    parts.append(_text(lx + 78, y + 10, "= +vn worse;", 9, "start", MUTED))
    parts.append(f'<polygon points="{lx + 160},{y + 11} {lx + 172},{y + 11} {lx + 166},{y + 2}" '
                 f'fill="#1e8449"/>')
    parts.append(_text(lx + 178, y + 10, "= +vn better", 9, "start", MUTED))
    for tick in (10, 12, 14, 16, 18, 20):
        parts.append(
            f'<line x1="{sx(tick):.1f}" y1="26" x2="{sx(tick):.1f}" y2="{y - 4}" '
            f'stroke="#dddddd" stroke-dasharray="2 3"/>'
        )
        parts.append(_text(sx(tick), y + 22, str(tick), 9, "middle", MUTED))

    # panel (b): enumeration frontier
    bx = 500
    enum_rows = [
        ("enum base (216)", mean(min(base[(i,) + c] for c in all_cells) for i in instances)),
        ("enum vn (216)", mean(min(vn[(i,) + c] for c in all_cells) for i in instances)),
        ("enum union (432)", mean(min(min(base[(i,) + c], vn[(i,) + c]) for c in all_cells)
                                  for i in instances)),
    ]
    parts.append(_text(bx - 40, 18, "(b) enumeration frontier", 12))
    maxv = 4.5
    yy = 40
    for label, value in enum_rows:
        width = value / maxv * 130
        parts.append(_text(bx - 44, yy + 11, label, 10, "end"))
        parts.append(
            f'<rect x="{bx - 40}" y="{yy}" width="{width:.1f}" height="16" '
            f'fill="#dde3ea" stroke="{INK}"/>'
        )
        parts.append(_text(bx - 40 + width + 6, yy + 12, f"{value:.2f}", 10, "start", ACCENT))
        yy += 26
    with open(path, "w") as handle:
        handle.write(_svg(710, max(y + 34, yy + 20), "".join(parts)))


def figure_f4(runs_dir: str, path: str) -> None:
    """Champion-configuration distribution (per-instance best, stage-1 216)."""

    gap = _load_gaps(runs_dir, "stage1-runs.csv")
    instances = sorted({key[0] for key in gap})
    ords = ["width", "height", "area", "perimeter", "maxside", "diagonal"]
    sels = ["widest-fit", "first-fit", "tre", "nre", "fitness-number", "max-area"]
    pols = ["LM", "RM", "TN", "SN", "MinD", "MaxD"]
    all_cells = [(o, s, p) for o in ords for s in sels for p in pols]

    from collections import Counter

    champions: Counter[tuple[str, str, str]] = Counter()
    for instance in instances:
        best = min((gap[(instance,) + c], c) for c in all_cells)
        champions[best[1]] += 1
    top = champions.most_common(10)

    hatch = (
        '<defs><pattern id="fnhatch" width="7" height="7" '
        'patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'
        f'<rect width="7" height="7" fill="#f5d6d0"/>'
        f'<line x1="0" y1="0" x2="0" y2="7" stroke="{ACCENT}" stroke-width="1.6"/>'
        '</pattern></defs>'
    )
    parts = [hatch,
             _text(20, 18, "per-instance best configuration (104 instances, 41 distinct champions)", 12)]
    y = 40
    for combo, count in top:
        label = "/".join(combo)
        width = count * 26
        has_fn = "fitness-number" in combo
        fill = "url(#fnhatch)" if has_fn else "#dde3ea"
        stroke = ACCENT if has_fn else INK
        parts.append(_text(240, y + 11, label, 10, "end"))
        parts.append(
            f'<rect x="246" y="{y}" width="{width}" height="15" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="0.9"/>'
        )
        parts.append(_text(246 + width + 6, y + 11, str(count), 10, "start"))
        y += 24
    parts.append(
        f'<rect x="246" y="{y}" width="16" height="12" fill="url(#fnhatch)" '
        f'stroke="{ACCENT}" stroke-width="0.9"/>'
    )
    parts.append(_text(268, y + 10, "= contains the fitness-number rule (complementarity)",
                       9, "start", MUTED))
    with open(path, "w") as handle:
        handle.write(_svg(670, y + 22, "".join(parts)))


def figure_f5(path: str) -> None:
    """The waste decomposition: H.W = item area + buried waste + top waste."""

    cell = 34
    skyline = [2, 2, 4, 4, 3, 3, 5, 5, 3, 3]
    height = 6
    origin_x, origin_y = 70, 240

    def px(unit_x: float) -> float:
        return origin_x + unit_x * cell

    def py(unit_h: float) -> float:
        return origin_y - unit_h * cell

    parts = [
        f'<rect x="{px(0)}" y="{py(height)}" width="{10 * cell}" '
        f'height="{height * cell}" fill="none" stroke="{INK}" stroke-width="1.4"/>',
    ]
    # top waste: between the skyline and the reported height
    points = [f"{px(0):.1f},{py(height):.1f}", f"{px(0):.1f},{py(skyline[0]):.1f}"]
    for x, h in enumerate(skyline):
        points.append(f"{px(x):.1f},{py(h):.1f}")
        points.append(f"{px(x + 1):.1f},{py(h):.1f}")
    points.append(f"{px(10):.1f},{py(height):.1f}")
    parts.append(
        f'<polygon points="{" ".join(points)}" fill="#f5d6d0" stroke="none"/>'
    )
    parts.append(_text(px(7.6), py(5.5), "top waste", 11, "middle", ACCENT))
    # packed items under the skyline
    points = [f"{px(0):.1f},{py(0):.1f}"]
    for x, h in enumerate(skyline):
        points.append(f"{px(x):.1f},{py(h):.1f}")
        points.append(f"{px(x + 1):.1f},{py(h):.1f}")
    points.append(f"{px(10):.1f},{py(0):.1f}")
    parts.append(
        f'<polygon points="{" ".join(points)}" fill="#dde3ea" stroke="{INK}" '
        f'stroke-width="1.2"/>'
    )
    parts.append(_text(px(1.0), py(1.0), "packed items", 10, "start", MUTED))
    # buried waste: a pocket raised over at x in [4,6), from y=1 up to y=3
    parts.append(
        f'<rect x="{px(4):.1f}" y="{py(3):.1f}" width="{2 * cell}" '
        f'height="{2 * cell}" fill="{ACCENT}" fill-opacity="0.55" '
        f'stroke="{ACCENT}" stroke-dasharray="3 2"/>'
    )
    parts.append(_text(px(5.0), py(2.15) + 4, "buried", 10, "middle", "#ffffff"))
    parts.append(_text(px(5.0), py(1.3) + 4, "waste", 10, "middle", "#ffffff"))
    parts.append(
        _text(px(0), py(6.45),
              "H x W  =  item area  +  buried waste (raised over)  +  top waste",
              11, "start")
    )
    parts.append(_text(px(5), origin_y + 18, "strip width W", 10, "middle"))
    with open(path, "w") as handle:
        handle.write(_svg(470, 300, "".join(parts)))


def figure_f6(runs_dir: str, path: str) -> None:
    """Greedy portfolio curve: size k vs mean gap, with the enum frontier."""

    points_data = []
    with open(f"{runs_dir}/stage4-portfolio.csv", newline="") as handle:
        for row in csv.DictReader(handle):
            points_data.append((int(row["k"]), float(row["mean_gap_pct"])))
    frontier = 3.42
    lo, hi = 3.0, 7.5

    def sx(k: float) -> float:
        return 70 + (k - 1) / 11 * 430

    def sy(value: float) -> float:
        return 230 - (value - lo) / (hi - lo) * 200

    parts = [_text(20, 18, "greedy portfolio: size vs mean gap (104 instances)", 12)]
    for tick in (3, 4, 5, 6, 7):
        parts.append(
            f'<line x1="{sx(1):.1f}" y1="{sy(tick):.1f}" x2="{sx(12):.1f}" '
            f'y2="{sy(tick):.1f}" stroke="#dddddd" stroke-dasharray="2 3"/>'
        )
        parts.append(_text(sx(1) - 8, sy(tick) + 4, str(tick), 9, "end", MUTED))
    parts.append(
        f'<line x1="{sx(1):.1f}" y1="{sy(frontier):.1f}" x2="{sx(12):.1f}" '
        f'y2="{sy(frontier):.1f}" stroke="{ACCENT}" stroke-dasharray="6 4"/>'
    )
    parts.append(_text(sx(12), sy(frontier) - 6, "full enum (864) = 3.42", 9, "end", ACCENT))
    polyline = " ".join(f"{sx(k):.1f},{sy(v):.1f}" for k, v in points_data)
    parts.append(f'<polyline points="{polyline}" fill="none" stroke="{INK}" stroke-width="1.6"/>')
    for k, v in points_data:
        parts.append(f'<circle cx="{sx(k):.1f}" cy="{sy(v):.1f}" r="4" fill="{INK}"/>')
        parts.append(_text(sx(k), sy(v) - 8, f"{v:.2f}", 9, "middle"))
    for k in (1, 2, 4, 6, 8, 10, 12):
        parts.append(_text(sx(k), 250, str(k), 9, "middle", MUTED))
    parts.append(_text(sx(6.5), 268, "portfolio size k", 10, "middle"))
    parts.append(_text(34, 130, "mean gap %", 10, "middle", MUTED))
    with open(path, "w") as handle:
        handle.write(_svg(560, 285, "".join(parts)))


def write_t8_appendix(runs_dir: str, path: str) -> None:
    """Curated per-instance appendix table with the portfolio-of-12 column."""

    portfolio = [
        ("perimeter", "fitness-number", "SN", "True", "False"),
        ("area", "widest-fit", "MaxD", "True", "False"),
        ("area", "fitness-number", "LM", "True", "False"),
        ("perimeter", "tre", "TN", "True", "True"),
        ("diagonal", "fitness-number", "LM", "True", "True"),
        ("maxside", "fitness-number", "MinD", "True", "True"),
        ("maxside", "widest-fit", "MinD", "True", "True"),
        ("perimeter", "nre", "MinD", "True", "True"),
        ("perimeter", "tre", "RM", "True", "False"),
        ("perimeter", "first-fit", "TN", "True", "False"),
        ("area", "nre", "MinD", "True", "True"),
        ("perimeter", "nre", "LM", "True", "False"),
    ]
    tables = {}
    for name, tw, vn in (("stage1-runs.csv", "False", "False"),
                         ("stage2-tower-runs.csv", "True", "False"),
                         ("stage2-vn-runs.csv", "False", "True"),
                         ("stage2-vntower-runs.csv", "True", "True")):
        with open(f"{runs_dir}/{name}", newline="") as handle:
            for row in csv.DictReader(handle):
                tables[(row["instance"], row["ordering"], row["selection"],
                        row["placement"], tw, vn)] = int(row["height"])

    wanted = ["bf-LM", "bbf-best288", "twbf-best18", "fh"]
    with open(f"{runs_dir}/paper-t8-per-instance.csv", newline="") as handle:
        base_rows = list(csv.DictReader(handle))
    with open(path, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["instance", "n_items", "lower_bound"] + wanted
            + ["cch_best_single", "cch_portfolio12", "cch_enum864"]
        )
        for row in base_rows:
            name = row["instance"]
            pf = min(
                tables[(name,) + config]
                for config in portfolio
                if (name,) + config in tables
            )
            writer.writerow(
                [name, row["n_items"], row["lower_bound"]]
                + [row[alg] for alg in wanted]
                + [row["cch_best_single"], pf, row["cch_enum864"]]
            )


def main() -> int:
    import os

    os.makedirs("docs/figures", exist_ok=True)
    write_t2("docs/paper-t2-fidelity.csv")
    write_t8("docs", "docs/paper-t8-per-instance.csv")
    write_t8_appendix("docs", "docs/paper-t8-appendix.csv")
    figure_f1("docs/figures/f1-skyline.svg")
    figure_f2("docs", "docs/figures/f2-main-effects.svg")
    figure_f3("docs", "docs/figures/f3-vn-diversity.svg")
    figure_f4("docs", "docs/figures/f4-champions.svg")
    figure_f5("docs/figures/f5-waste-decomposition.svg")
    figure_f6("docs", "docs/figures/f6-portfolio.svg")
    for path in (
        "docs/paper-t2-fidelity.csv",
        "docs/paper-t8-per-instance.csv",
        "docs/paper-t8-appendix.csv",
        "docs/figures/f1-skyline.svg",
        "docs/figures/f2-main-effects.svg",
        "docs/figures/f3-vn-diversity.svg",
        "docs/figures/f4-champions.svg",
        "docs/figures/f5-waste-decomposition.svg",
        "docs/figures/f6-portfolio.svg",
    ):
        # Well-formedness check (raises on malformed XML).
        if path.endswith(".svg"):
            ElementTree.parse(path)
        print("wrote", path, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
