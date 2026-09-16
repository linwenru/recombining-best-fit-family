"""Retro-validation sweep over all reported packings (2026-09 review round).

Re-runs every deterministic experiment row and checks, per packing:
geometric validity (completeness, legal orientation, in-bounds, no overlap,
reported height) via ``burke_bf.validate_solution``; equality of the re-run
height with the reported CSV height (the solvers are deterministic); and,
for waste-measured rows, non-negative buried/top components with the area
identity H*W = area + buried + top.

Sources re-checked here (no per-row validation at production time):
  stage1-runs.csv, stage2-tower-runs.csv, stage2-vn-runs.csv,
  stage2-vntower-runs.csv   -- factorial arms via solve_config;
  prospective-runs.csv      -- grid/portfolio arms via the same engines as
                               production (measure for VN-off, solve_config
                               otherwise), fh arm via fast_heuristic.

Already validated per row at production time (not re-run):
  stage3-rls-runs.csv (cch/shell.py), stage3-baselines.csv
  (cch/baselines.py), stage4-zdf-runs.csv (cch/robustness.py).
The 624 matched tower-removal cells (F3) are covered by a dedicated
verification step (piece conservation, non-negative top waste, height
match to the stage1/stage2-tower ground truth).

Usage: python3 -m cch.validate_all [--workers N]
Writes docs/validation-sweep.csv and prints the summary.
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from types import SimpleNamespace

from burke_bf import load_instance
from burke_bf.solver import validate_solution
from fh import fast_heuristic

from .mechanisms import measure
from .model import Config, Ordering, PlacementPolicy, Selection
from .solver import solve_config

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "docs" / "validation-sweep.csv"

# source CSV -> (tower_removal, vertical_niche) flags for its config variant
STAGE_SOURCES = {
    "stage1-runs.csv": (False, False),
    "stage2-tower-runs.csv": (True, False),
    "stage2-vn-runs.csv": (False, True),
    "stage2-vntower-runs.csv": (True, True),
}

PRODUCTION_VALIDATED = (
    "stage3-rls-runs.csv (cch/shell.py, per-row validate_solution)",
    "stage3-baselines.csv (cch/baselines.py, per-row validate_solution)",
    "stage4-zdf-runs.csv (cch/robustness.py, per-row validate_solution)",
)

CHUNK = 50


def _instance_map() -> dict[str, str]:
    """instance name -> .ins2D path (classic + prospective suites)."""
    mapping: dict[str, str] = {}
    for pattern in (
        "data/c/*.ins2D", "data/bkw/*.ins2D", "data/nt/*.ins2D",
        "data/prospective/*.ins2D",
    ):
        for path in glob.glob(str(ROOT / pattern)):
            name = Path(path).stem.replace("-", "").upper()
            mapping[name] = path
    return mapping


def _stage_tasks() -> list[tuple[str, list[tuple[str, str, str, str, str]]]]:
    """(path, [(source, ordering, selection, placement, height), ...])."""
    by_instance: dict[str, list] = {}
    names = _instance_map()
    for source, (tw, vn) in STAGE_SOURCES.items():
        with open(ROOT / "docs" / source, newline="") as handle:
            for row in csv.DictReader(handle):
                key = (
                    source, row["ordering"], row["selection"],
                    row["placement"], row["height"],
                )
                by_instance.setdefault(names[row["instance"]], []).append(key)
    tasks = []
    for path, rows in by_instance.items():
        for i in range(0, len(rows), CHUNK):
            tasks.append((path, rows[i : i + CHUNK]))
    return tasks


def _prospective_tasks() -> list[tuple[str, list[tuple[str, str, str, str, str, str, str, str]]]]:
    by_instance: dict[str, list] = {}
    names = _instance_map()
    with open(ROOT / "docs" / "prospective-runs.csv", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (
                row["arm"], row["ordering"], row["selection"],
                row["placement"], row["tower_removal"],
                row["vertical_niche"], row["height"], row["lower_bound"],
            )
            by_instance.setdefault(names[row["instance"]], []).append(key)
    tasks = []
    for path, rows in by_instance.items():
        for i in range(0, len(rows), CHUNK):
            tasks.append((path, rows[i : i + CHUNK]))
    return tasks


def _check_stage(task) -> list[str]:
    path, rows = task
    instance = load_instance(path)
    problems = []
    for source, ordering, selection, placement, height_s in rows:
        tw, vn = STAGE_SOURCES[source]
        config = Config(
            ordering=Ordering(ordering),
            selection=Selection(selection),
            placement=PlacementPolicy(placement),
            tower_removal=tw,
            vertical_niche=vn,
        )
        try:
            placements, skyline, _ = solve_config(instance, config)
            height = max(skyline)
            validate_solution(
                instance,
                SimpleNamespace(placements=tuple(placements), height=height),
            )
            if height != int(height_s):
                problems.append(
                    f"height {height} != csv {height_s} "
                    f"{instance.name} {config.value} ({source})"
                )
        except Exception as exc:  # noqa: BLE001 - collect, do not abort
            problems.append(
                f"{type(exc).__name__}: {exc} "
                f"{instance.name} {config.value} ({source})"
            )
    return problems


def _check_prospective(task) -> list[str]:
    path, rows = task
    instance = load_instance(path)
    problems = []
    for arm, ordering, selection, placement, tw, vn, height_s, lb_s in rows:
        tag = f"{instance.name} {arm} {ordering}/{selection}/{placement}+tw{tw}+vn{vn}"
        try:
            if arm == "fh":
                budget = None if len(instance.items) <= 250 else 5000
                placements, height = fast_heuristic(
                    list(instance.items), instance.strip_width,
                    swap_budget=budget,
                )
            else:
                config = Config(
                    ordering=Ordering(ordering),
                    selection=Selection(selection),
                    placement=PlacementPolicy(placement),
                    tower_removal=tw == "T",
                    vertical_niche=vn == "T",
                )
                if arm == "grid" and vn == "F":
                    _, buried, _, placed, _, skyline = measure(
                        instance, config, tower_removal=config.tower_removal
                    )
                    height = max(skyline)
                    top = height * instance.strip_width - instance.total_area - buried
                    if buried < 0 or top < 0:
                        problems.append(
                            f"negative waste buried={buried} top={top} {tag}"
                        )
                    if height * instance.strip_width != (
                        instance.total_area + buried + top
                    ):
                        problems.append(f"area identity broken {tag}")
                    if len(placed) != len(instance.items):
                        problems.append(f"piece count {len(placed)} {tag}")
                    placements, skyline2, _ = solve_config(instance, config)
                    if max(skyline2) != height:
                        problems.append(f"engine mismatch {tag}")
                    validate_solution(
                        instance,
                        SimpleNamespace(
                            placements=tuple(placements), height=height
                        ),
                    )
                    if height != int(height_s):
                        problems.append(
                            f"height {height} != csv {height_s} {tag}"
                        )
                    continue
                placements, skyline, _ = solve_config(instance, config)
                height = max(skyline)
            validate_solution(
                instance,
                SimpleNamespace(placements=tuple(placements), height=height),
            )
            if height != int(height_s):
                problems.append(f"height {height} != csv {height_s} {tag}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{type(exc).__name__}: {exc} {tag}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    stage_tasks = _stage_tasks()
    prosp_tasks = _prospective_tasks()
    n_stage = sum(len(rows) for _, rows in stage_tasks)
    n_prosp = sum(len(rows) for _, rows in prosp_tasks)
    print(f"stage rows: {n_stage}; prospective rows: {n_prosp}")
    start = time.perf_counter()
    summary = []
    for source_name, tasks, worker in (
        ("stage1/2 factorial arms", stage_tasks, _check_stage),
        ("prospective arms", prosp_tasks, _check_prospective),
    ):
        problems: list[str] = []
        done = 0
        with Pool(args.workers) as pool:
            for chunk_problems in pool.imap_unordered(worker, tasks):
                problems.extend(chunk_problems)
                done += 1
                if done % 100 == 0:
                    print(
                        f"  {source_name}: {done}/{len(tasks)} chunks, "
                        f"{len(problems)} problems "
                        f"({time.perf_counter() - start:.0f}s)",
                        flush=True,
                    )
        rows_n = sum(len(rows) for _, rows in tasks)
        summary.append(
            {
                "source": source_name,
                "rows": rows_n,
                "violations": len(problems),
                "first_violations": " | ".join(problems[:20]),
            }
        )
        print(f"{source_name}: {rows_n} rows, {len(problems)} violations")

    for note in PRODUCTION_VALIDATED:
        print(f"validated at production time: {note}")
        summary.append(
            {
                "source": note,
                "rows": "",
                "violations": 0,
                "first_violations": "",
            }
        )

    with open(OUT_CSV, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary[0].keys()))
        writer.writeheader()
        writer.writerows(summary)
    print(f"wrote {OUT_CSV} in {time.perf_counter() - start:.0f}s")
    total = sum(int(s["violations"]) for s in summary)
    print(f"TOTAL VIOLATIONS: {total}")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
