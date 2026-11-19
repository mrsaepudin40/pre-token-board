---
name: pre-token-board
description: Rank pre-token DeFi protocols by implied launch value from a DefiLlama snapshot, with a costed six-step farm plan for each one. No API key needed.
summary: Rank pre-token protocols by what their launch would be worth, from a snapshot, with a farm plan for each one.
version: 1.0.0
tags: [defi, crypto, pre-token, token-radar, defillama, airdrop, protocol-ranking, crypto-research]
keywords: [pre-token, implied value, DefiLlama, TVL, farm plan, airdrop, protocol ranking]
use_cases: [Rank pre-token DeFi protocols by implied launch value, Find the most promising protocols to farm before their token launch, Explain why one protocol outranks another]
---

# Pre-Token Board

Rank pre-token DeFi protocols by implied launch value, from a
snapshot of the protocol universe, with a costed six-step farm plan
for each one. One transparent model, radar-2, applied the same way
to every protocol. Every number is recomputable from the snapshot.

Use this skill when the user asks to rank pre-token or token-less
DeFi protocols by likely launch value, find which protocols without
a token are worth farming for a possible airdrop or launch, build or
refresh a token radar board from a DefiLlama snapshot, or explain
why one protocol outranks another.

Do NOT use it to predict a price, a launch date, or whether a
protocol will ever issue a token. The implied value is a model
estimate from the snapshot's own figures, not a forecast and not
financial advice.

## Requirements

Python 3, a terminal, and read and write access to the working
files. No network calls, no API key, nothing to install. The
scorer is `scripts/score.py`, standard library only, self-contained.

## Workflow

### 1. Get a snapshot

Ask for a snapshot file, or help the user build one. A snapshot is
one JSON object with `as_of` (`YYYY-MM-DD`), `source`, `floor_usd`
(a positive integer), `protocols`, and `watchlist` (slugs). Each
protocol carries exactly ten fields: `slug`, `name`, `category`,
`chains`, `tvl_usd`, `change_7d`, `mcap_usd`, `listed_at`,
`gecko_id`, `symbol`. See `reference/model.md` for the schema and
the DefiLlama field mapping.

Refuse a snapshot that is not JSON, has no `as_of` date, no
`floor_usd`, no `protocols` array, or no `watchlist`. Refuse a
protocol entry that lacks a slug, a name, or a TVL. Never invent a
protocol, a TVL, or a market cap the source did not return. If the
user has no snapshot, offer `examples/sample-snapshot.json` as a
test first, and say clearly that it is invented sample data, not
real market data.

### 2. Run the scorer

Run the scorer from the skill folder. It writes `board.json` and
prints the top 10 rows.

```bash
python3 scripts/score.py --input snapshot.json --output board.json
python3 scripts/score.py --input snapshot.json --output board.json --top 20
```

The scorer reads only the snapshot file given on the command line.
It makes no network calls and reads no other file. If it exits
with an error, report the error exactly and do not hand-write a
board to replace it.

### 3. Present the board

Report the snapshot `as_of` date and source first, then the board
size and the top rows: rank, name, category, TVL, implied value,
and the category multiple. State the model version, radar-2.

Check the board before presenting it: every watchlist slug is
present, ranks run 1 to n with no gaps, rows are sorted by implied
value descending, and every row has 6 farm steps, or 7 for the
top 40 rows. If any check fails, say so and do not present the
board as valid.

### 4. Explain a row

When the user asks why one protocol outranks another, show that
row's own inputs from `board.json`: TVL, category multiple,
growth percent and multiplier, age and maturity multiplier, and
the worked multiplication. The worked example for Steakhouse
Financial is in `reference/model.md`. Never explain a rank with a
reason the row's own numbers do not support.

Call out thin categories: when a category's multiple rests on
fewer than 5 live comps, say the small-sample cap of 0.35 applied
and one outlier cannot decide the board.

### 5. Give the farm plan

Give the row's `farm_steps` as written. Do not add steps, change
the capital tier, or change the gas figures. The capital tier
comes from the protocol's TVL and the gas from its first chain,
both fixed in `reference/model.md`.

Warn the user in plain words: farming uses real capital at risk
of loss, the plan never pays to claim, and the implied value is
a model, not a promise that a token will ever exist.

## Files

- `SKILL.md` — this workflow.
- `scripts/score.py` — the complete radar-2 model in dependency-free
  Python 3. Run it as shown above. It takes `--input`, `--output`,
  and an optional `--top` display limit.
- `reference/model.md` — the snapshot schema, the radar-2 formulas
  and constants, the farm plan rules, and a hand-computed worked
  example.
- `examples/sample-snapshot.json` — an invented 8-protocol snapshot
  for testing. Its board is in `examples/sample-board.json`.

## Provenance

Built from a DefiLlama snapshot. On the 2026-11-14 snapshot the
scorer produces a board of 178 rows, led by Steakhouse Financial
at $657,799,657 implied, and every row recomputes from its own
record.
