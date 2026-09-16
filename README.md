# Recombining the Best-Fit Family

Code and data for a unified component analysis of best-fit and related
constructive heuristics for two-dimensional strip packing. Citation
information will be added once the associated publication is available.

Archived at <https://doi.org/10.5281/zenodo.22792108>.

## What this repository contains

- Unified, zero-dependency Python reimplementations of fifteen best-fit and
  related constructive heuristics for two-dimensional strip packing — one
  package per source paper:
  - `burke_bf/` — BF (Burke, Kendall & Whitwell 2004)
  - `bbf/` — BBF (Aşık & Özcan 2009)
  - `twbf/` — TWBF (Verstichel et al. 2013)
  - `sky/` — the skyline heuristic with tabu/IDBS (Wei et al. 2011)
  - `ish/` — ISH (Wei et al. 2017)
  - `lvl/` — the level family (Ortmann et al. 2010; FFDH, BFDH, SAS, SASm,
    BFS, SC/SCR)
  - `fh/` — FH (Leung & Zhang 2011)
  - `ibf/` — TCBF/WPBF (Yehia et al. 2024)
- `cch/` — the configurable constructive engine: every family member as one
  point in a shared component space (orderings × selections × placements ×
  flags), plus all experiment and analysis runners:
  - `experiment.py` — the stage-1/2 factorial experiments
  - `shell.py` / `rls_multiseed.py` — the random-local-search shell runs
  - `baselines.py` — the unified-protocol baseline measurements
  - `mechanisms.py` — the buried/top waste decomposition
  - `portfolio_robustness.py` — greedy portfolio selection, random-portfolio
    control, leave-one-family-out
  - `prospective.py` — the prospective validation arm on newly generated
    distributions
  - `validate_all.py` — the full geometric validation sweep
  - `paper_assets.py` — table and figure generators
- `data/` — the benchmark instances (2DPackLib format; see
  `data/format_description.txt`) and the 120-instance prospective suite
  (`data/prospective/`)
- `docs/` — all per-cell raw results (CSV) behind every reported number,
  and the pre-registered prospective protocol
  (`docs/prospective-validation-plan.md`)

## Requirements

Python 3.10+, standard library only.

## Reproducing

```sh
# stage-1 factorial experiment (resumable, streams CSV)
python3 -m cch.experiment

# prospective arm
python3 -m cch.prospective generate
python3 -m cch.prospective select-novn --tr-locked
python3 -m cch.prospective select-novn
python3 -m cch.prospective run --workers 6
python3 -m cch.prospective aggregate

# full geometric validation sweep over all reported packings
python3 -m cch.validate_all --workers 6
```

Every reported packing passes a geometric validator (completeness, legal
orientation, in-bounds, no overlap, reported height); see
`docs/validation-sweep.csv`.

## Data credit

Benchmark instances are from 2DPackLib (University of Bologna),
<https://site.unibo.it/operations-research/en/research/2dpacklib>, and
remain the property of their original publishers.

## License

MIT (see `LICENSE`). Third-party benchmark instance files are covered by
their original terms (see "Data credit").
