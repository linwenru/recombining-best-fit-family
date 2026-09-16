"""Robustness experiment on the ZDF benchmark set (Leung & Zhang 2011 /
Zhang et al. 2013, downloaded from 2DPackLib into data/zdf/).

Design: full stage-1 factorial (216 configs, +/- tower removal) on the five
small instances ZDF1-5 (n <= 900, W = 100), and a reduced 72-cell design
(4 orderings x 3 selections x 3 placements x tower on/off) on the mid-size
ZDF6-9 (n <= 5032, W = 3000). ZDF10-16 (n up to 75032) exceed what the
array-skyline engine can do in pure Python and are documented as skipped.

    python3 -m cch.robustness [--limit N]

writes docs/stage4-zdf-runs.csv (resumable).
"""

from __future__ import annotations

import argparse
import csv
import glob
import sys
import time
from itertools import product
from math import ceil
from types import SimpleNamespace
from typing import Iterable

from burke_bf import load_instance
from burke_bf.solver import validate_solution

from .model import Config, Ordering, PlacementPolicy, Selection
from .solver import solve_config

FULL_INSTANCES = [f"data/zdf/zdf{i}.ins2D" for i in range(1, 6)]
REDUCED_INSTANCES = [f"data/zdf/zdf{i}.ins2D" for i in range(6, 10)]

REDUCED_ORDERINGS = (
    Ordering.WIDTH,
    Ordering.PERIMETER,
    Ordering.AREA,
    Ordering.HEIGHT,
)
REDUCED_SELECTIONS = (
    Selection.WIDEST_FIT,
    Selection.FIRST_FIT,
    Selection.FITNESS_NUMBER,
)
REDUCED_PLACEMENTS = (
    PlacementPolicy.LM,
    PlacementPolicy.TN,
    PlacementPolicy.SN,
)


def _lower_bound(instance) -> int:
    tallest = max(item.height for item in instance.items)
    return max(ceil(instance.total_area / instance.strip_width), tallest)


def _design(path: str) -> list[Config]:
    if path in FULL_INSTANCES:
        return [
            Config(
                ordering=ordering,
                selection=selection,
                placement=placement,
                tower_removal=tower,
            )
            for ordering, selection, placement, tower in product(
                Ordering, Selection, PlacementPolicy, (False, True)
            )
        ]
    return [
        Config(
            ordering=ordering,
            selection=selection,
            placement=placement,
            tower_removal=tower,
        )
        for ordering, selection, placement, tower in product(
            REDUCED_ORDERINGS,
            REDUCED_SELECTIONS,
            REDUCED_PLACEMENTS,
            (False, True),
        )
    ]


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out-dir", default="docs")
    args = parser.parse_args(list(argv) if argv is not None else None)

    rows_path = f"{args.out_dir}/stage4-zdf-runs.csv"
    done: set[tuple[str, str, str, str, str]] = set()
    try:
        with open(rows_path, newline="") as handle:
            done = {
                (row["instance"], row["ordering"], row["selection"],
                 row["placement"], row["tower"])
                for row in csv.DictReader(handle)
            }
    except FileNotFoundError:
        pass

    paths = FULL_INSTANCES + REDUCED_INSTANCES
    if args.limit is not None:
        paths = paths[: args.limit]

    with open(rows_path, "a", newline="") as handle:
        writer = csv.writer(handle)
        if not done:
            writer.writerow(
                ["instance", "n_items", "ordering", "selection", "placement",
                 "tower", "height", "lower_bound", "gap_pct"]
            )
        for path in paths:
            instance = load_instance(path)
            lower_bound = _lower_bound(instance)
            configs = _design(path)
            start = time.perf_counter()
            skipped = 0
            for config in configs:
                key = (
                    instance.name,
                    config.ordering.value,
                    config.selection.value,
                    config.placement.value,
                    str(config.tower_removal),
                )
                if key in done:
                    skipped += 1
                    continue
                placements, skyline, _ = solve_config(instance, config)
                height = max(skyline)
                validate_solution(
                    instance,
                    SimpleNamespace(placements=tuple(placements), height=height),
                )
                writer.writerow(
                    [
                        instance.name,
                        len(instance.items),
                        config.ordering.value,
                        config.selection.value,
                        config.placement.value,
                        config.tower_removal,
                        height,
                        lower_bound,
                        f"{100.0 * (height - lower_bound) / lower_bound:.4f}",
                    ]
                )
            handle.flush()
            print(
                f"{instance.name}: {len(configs) - skipped} cells"
                f" ({time.perf_counter() - start:.1f}s, {skipped} cached)",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
