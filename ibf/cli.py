"""Command-line runner for the TCBF/WPBF reproduction experiment.

Compares computed heights against the paper's Tables 1-2 (Yehia et al.
2024), which list BFA(LM), TCBF and WPBF heights per instance. BKW01-13
correspond to the paper's N1-N13; the path/nice/babu rows of Table 2 are
skipped because those datasets are not in this repository.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

from burke_bf import Policy, load_instance, solve_policy
from burke_bf.render import render_svg
from burke_bf.model import Solution

from .solver import solve_tcbf, solve_wpbf

# Paper Tables 1-2: instance -> (BFA(LM), TCBF, WPBF).
PAPER_TABLES = {
    "C1P1": (21, 22, 21),
    "C1P2": (22, 21, 22),
    "C1P3": (24, 24, 24),
    "C2P1": (17, 18, 17),
    "C2P2": (16, 16, 16),
    "C2P3": (18, 17, 18),
    "C3P1": (32, 32, 32),
    "C3P2": (34, 34, 34),
    "C3P3": (33, 35, 33),
    "C4P1": (63, 63, 63),
    "C4P2": (64, 67, 64),
    "C4P3": (62, 62, 62),
    "C5P1": (94, 95, 95),
    "C5P2": (93, 96, 93),
    "C5P3": (94, 94, 99),
    "C6P1": (124, 124, 124),
    "C6P2": (124, 123, 124),
    "C6P3": (124, 124, 124),
    "C7P1": (246, 245, 245),
    "C7P2": (246, 245, 246),
    "C7P3": (245, 245, 247),
    "BKW01": (48, 45, 45),
    "BKW02": (55, 55, 55),
    "BKW03": (54, 55, 54),
    "BKW04": (86, 83, 89),
    "BKW05": (105, 104, 106),
    "BKW06": (102, 102, 103),
    "BKW07": (110, 113, 110),
    "BKW08": (85, 84, 84),
    "BKW09": (163, 163, 163),
    "BKW10": (153, 153, 152),
    "BKW11": (153, 154, 152),
    "BKW12": (347, 364, 305),
    "BKW13": (986, 964, 966),
}


def _solution_record(solution: Solution) -> dict[str, object]:
    return {
        "height": solution.height,
        "initial_height": solution.initial_height,
        "tower_moves": solution.tower_moves,
        "placements": [
            {
                "item_id": placement.item_id,
                "x": placement.x,
                "y": placement.y,
                "width": placement.width,
                "height": placement.height,
                "rotated": placement.rotated,
            }
            for placement in solution.placements
        ],
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Yehia et al.'s TCBF and WPBF heuristics."
    )
    parser.add_argument(
        "inputs", nargs="*", type=Path, help="2DPackLib .ins2D files"
    )
    parser.add_argument(
        "--json", type=Path, help="write complete placements as JSON"
    )
    parser.add_argument(
        "--svg-dir",
        type=Path,
        help="write SVGs of the TCBF and WPBF packings for every instance",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    paths = sorted(args.inputs)
    if not paths:
        raise SystemExit("no input instances found")

    experiment: dict[str, object] = {
        "algorithm": "Yehia et al. TCBF and WPBF",
        "instances": {},
    }
    print(
        "instance  n    bfaLM  TCBF  WPBF  pTCBF  pWPBF  mT    mW   time_s"
    )
    print("-" * 66)
    matches_t = matches_w = compared = 0
    for path in paths:
        instance = load_instance(path)
        started = perf_counter()
        tcbf = solve_tcbf(instance)
        wpbf = solve_wpbf(instance)
        bfa_lm = solve_policy(instance, Policy.LEFTMOST)
        elapsed = perf_counter() - started
        paper = PAPER_TABLES.get(instance.name)
        match_t = match_w = ""
        if paper is not None:
            compared += 1
            match_t = "yes" if tcbf.height == paper[1] else "NO"
            match_w = "yes" if wpbf.height == paper[2] else "NO"
            matches_t += tcbf.height == paper[1]
            matches_w += wpbf.height == paper[2]
        print(
            f"{instance.name:<8} {len(instance.items):>4}  "
            f"{bfa_lm.height:>5}  {tcbf.height:>4}  {wpbf.height:>4}  "
            f"{str(paper[1]) if paper is not None else '-':>5}  "
            f"{str(paper[2]) if paper is not None else '-':>5}  "
            f"{match_t:>4} {match_w:>4}  {elapsed:>7.2f}"
        )

        experiment["instances"][instance.name] = {
            "items": len(instance.items),
            "strip_width": instance.strip_width,
            "reference_height": instance.reference_height,
            "paper_tables": paper,
            "bfa_lm_height": bfa_lm.height,
            "elapsed_s": elapsed,
            "tcbf": _solution_record(tcbf),
            "wpbf": _solution_record(wpbf),
        }

        if args.svg_dir is not None:
            args.svg_dir.mkdir(parents=True, exist_ok=True)
            stem = instance.name.lower()
            (args.svg_dir / f"{stem}-tcbf.svg").write_text(
                render_svg(instance, tcbf), encoding="utf-8"
            )
            (args.svg_dir / f"{stem}-wpbf.svg").write_text(
                render_svg(instance, wpbf), encoding="utf-8"
            )

    print("-" * 66)
    print(
        f"matched paper on TCBF {matches_t}/{compared}, "
        f"WPBF {matches_w}/{compared} instances"
    )

    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(experiment, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
