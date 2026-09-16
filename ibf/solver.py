"""TCBF and WPBF heuristics of Yehia, Ashour, Abed and Elshaer (2024).

Both heuristics (EIJEST 47:92-100) extend Burke's best-fit (BFA) with a
modified packing-stage selection. This implementation keeps BFA's proven
machinery (preprocessing, lowest-gap search, exact-then-widest selection,
leftmost placement — the paper's own BFA(LM) column matches burke_bf's
leftmost results on 33/34 instances) and adds the paper's two ideas:

- TCBF (tower prevention): when the chosen rectangle would become the new
  skyline maximum, defer it if it could stand rotated on the taller
  neighbour without exceeding the current maximum height, and try the next
  best-fitting rectangle instead (paper step 2.5). No post-packing stage.
- WPBF (fitting-factor inversion): when the chosen rectangle would leave a
  remainder of the gap that fits none of the remaining rectangles, place
  instead the as-is fitting rectangle with the smallest fitting factor
  (width over gap width, ties by greatest height), then run Burke's
  tower-removal post-packing stage.

Reproduction note: as published, these numbers are NOT reproducible — every
faithful reading of the two mechanisms measurably degrades results relative
to plain BFA (see the negative-result discussion in docs/paper-en.md,
Section 4.3). The paper's prose for the
selection rule (step 2.2) is self-contradictory and its BFA(LM) baseline
deviates from the canonical BF on N13 (986 vs 964-968 elsewhere), so the
differences are attributed to undocumented implementation details.

Re-examination (2026-08, after reproducing the whole family): a reading
matrix over the two selection rules (Burke's exact-then-widest vs the
paper's literal {C,R'} highest-area) x the two deferral thresholds
(rotated-on-taller-neighbour below the current maximum vs below the
candidate's own top) x the two WPBF inversion candidate pools (as-is fits
vs including rotated fits) was run on all 34 instances. No variant
reproduces the paper's columns (TCBF best 9/34 exact, WPBF best 8/34), the
literal {C,R'}-area selection is catastrophic (3-5/34), and every variant
is on average WORSE than the shared BFA baseline (TCBF +2.20%, WPBF
+1.61% mean height increase, wins far outnumbered by losses). The paper's
own tables are likewise mixed (average deviation: BFA 7.33%, TCBF 7.62%,
WPBF 6.93%), and its "3% improvement" claim refers to other literature
heuristics, not to its own baseline. Conclusion: the published numbers
require undocumented implementation details; the stated mechanisms are not
supported as improvements.
"""

from __future__ import annotations

from math import inf

from burke_bf.model import Instance, Placement, Policy, Solution
from burke_bf.solver import (
    _lowest_gap,
    _neighbour_heights,
    _postprocess_towers,
    _preprocess,
    _raise_unfillable_gap,
    validate_solution,
)


def _best_fitting(
    rectangles, gap_width: int, excluded: frozenset[int] = frozenset()
):
    """Burke's exact-then-widest selection over non-excluded rectangles.

    Returns (index, rectangle, placed_width, placed_height) with index into
    the original list. Mirrors burke_bf's early-termination rule.
    """

    best = None
    best_fill = 0
    for index, rectangle in enumerate(rectangles):
        if index in excluded:
            continue
        if rectangle.width < best_fill:
            break
        if rectangle.width <= gap_width:
            width, height = rectangle.width, rectangle.height
        elif rectangle.height <= gap_width:
            width, height = rectangle.height, rectangle.width
        else:
            continue
        if width == gap_width:
            return index, rectangle, width, height
        if width > best_fill:
            best = (index, rectangle, width, height)
            best_fill = width
    return best


def _pack(
    instance: Instance, *, prevent_towers: bool, invert_on_waste: bool
) -> tuple[list[Placement], list[int]]:
    remaining = _preprocess(instance.items)
    skyline = [0] * instance.strip_width
    placements: list[Placement] = []

    while remaining:
        gap = _lowest_gap(skyline)
        excluded: set[int] = set()
        while True:
            candidate = _best_fitting(remaining, gap.width, frozenset(excluded))
            if candidate is None:
                if excluded:
                    # Every candidate towers; accept the preferred one.
                    candidate = _best_fitting(remaining, gap.width)
                    break
                _raise_unfillable_gap(skyline, gap)
                gap = _lowest_gap(skyline)
                continue

            index, rectangle, width, height = candidate
            top = gap.y + height
            if not prevent_towers or top <= max(skyline):
                break

            # Defer only when the rectangle could stand rotated on the taller
            # neighbour without exceeding the current maximum (step 2.5);
            # rotating an as-is placement never helps since width >= height.
            neighbours = [
                value
                for value in _neighbour_heights(skyline, gap)
                if value != inf
            ]
            rotated_height = (
                rectangle.height if height == rectangle.width else rectangle.width
            )
            if (
                neighbours
                and max(neighbours) + rotated_height < max(skyline)
                and len(excluded) + 1 < len(remaining)
            ):
                excluded.add(index)
                continue
            break

        if invert_on_waste and len(remaining) > 1:
            rest = gap.width - width
            if rest > 0 and not any(
                other.width <= rest or other.height <= rest
                for other_index, other in enumerate(remaining)
                if other_index != index
            ):
                inverted = min(
                    (
                        (other_index, other, other.width, other.height)
                        for other_index, other in enumerate(remaining)
                        if other.width <= gap.width
                    ),
                    key=lambda candidate: (candidate[2], -candidate[3]),
                    default=None,
                )
                if inverted is not None:
                    candidate = inverted
                    index, rectangle, width, height = candidate

        placements.append(
            Placement(
                item_id=rectangle.item.item_id,
                x=gap.x,
                y=gap.y,
                width=width,
                height=height,
                original_width=rectangle.item.width,
                original_height=rectangle.item.height,
            )
        )
        skyline[gap.x : gap.x + width] = [gap.y + height] * width
        del remaining[index]

    return placements, skyline


def solve_tcbf(instance: Instance) -> Solution:
    """Pack with TCBF: tower prevention instead of a post-packing stage."""

    placements, skyline = _pack(
        instance, prevent_towers=True, invert_on_waste=False
    )
    solution = Solution(
        instance_name=instance.name,
        policy=Policy.LEFTMOST,
        height=max(skyline),
        initial_height=max(skyline),
        placements=tuple(placements),
        skyline=tuple(skyline),
        tower_moves=0,
    )
    validate_solution(instance, solution)
    return solution


def solve_wpbf(instance: Instance) -> Solution:
    """Pack with WPBF: fitting-factor inversion plus Burke's tower removal."""

    placements, skyline = _pack(
        instance, prevent_towers=False, invert_on_waste=True
    )
    initial_height = max(skyline)
    placements, skyline, tower_moves = _postprocess_towers(
        placements, skyline, Policy.LEFTMOST
    )
    solution = Solution(
        instance_name=instance.name,
        policy=Policy.LEFTMOST,
        height=max(skyline),
        initial_height=initial_height,
        placements=tuple(placements),
        skyline=tuple(skyline),
        tower_moves=tower_moves,
    )
    validate_solution(instance, solution)
    return solution
