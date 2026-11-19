# pre-token-board

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3](https://img.shields.io/badge/python-3-blue)](scripts/score.py)
[![API key: not required](https://img.shields.io/badge/API%20key-not%20required-brightgreen)](reference/model.md)

Rank pre-token DeFi protocols by implied launch value, from a
snapshot of the protocol universe, with a costed six-step farm plan
for each one. One transparent model, radar-2, applied the same way
to every protocol. Every number is recomputable from the snapshot.

## What it does

Feed it a snapshot (a JSON file in the format in
`reference/model.md`) and it returns a ranked board of pre-token
protocols. Each protocol's implied value is its TVL priced the way
the market prices its live-token peers: a category multiple measured
from the snapshot itself (median market-cap/TVL, shrunk toward the
global median when a category is thin, clamped to 0.05–1.00),
adjusted by a weekly-growth factor and a maturity factor that
rewards protocols which have run for years with no token. No
protocol name is special-cased; every constant is printed in the
reference notes, and one row is worked by hand so you can check
the arithmetic yourself.

Every row also carries a six-step farm plan derived from the
protocol's own record: the right action for its category, the
capital tier its TVL implies ($50–$250), the gas its main chain
actually costs, a weekly qualifying action, and how long to hold.
Watchlist protocols are guaranteed a place on the board; every
other rankable pre-token protocol joins them, so the board is a
floor, never a ceiling.

## Run it

```bash
python3 scripts/score.py --input snapshot.json --output board.json
python3 scripts/score.py --input snapshot.json --output board.json --top 20
```

Python 3, standard library only. No network calls, no API key,
nothing to install. `examples/sample-snapshot.json` is an invented
8-protocol snapshot for testing; its board is in
`examples/sample-board.json`. Sample data is clearly labelled and
is not real market data.

## Files

- `SKILL.md` — the agent skill: the full workflow for ranking a
  snapshot, presenting the board, explaining a row, and giving the
  farm plan.
- `scripts/score.py` — the complete radar-2 model in
  dependency-free Python 3.
- `reference/model.md` — the snapshot schema, the radar-2 formulas
  and constants, the farm plan rules, and a hand-computed worked
  example.
- `examples/` — a sample snapshot and the exact board the script
  produces from it.

## Honest limits

Implied value is a model estimate from the snapshot's own figures.
It is not a price prediction, not a launch date, and not a promise
that a protocol will ever issue a token. Always state the snapshot
date and source. Farming uses real capital at risk of loss.
