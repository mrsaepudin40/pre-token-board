# Token Radar radar-2 — model notes

Provenance: built from a DefiLlama snapshot. On the 2026-11-14
snapshot it scored 178 pre-token rows, led by Steakhouse Financial
at $657,799,657 implied. `scripts/score.py` reproduces that board
exactly, row for row.

## Snapshot schema

One JSON object. No other input is scored.

```json
{
  "as_of": "2026-11-14",
  "source": "DefiLlama https://api.llama.fi/protocols, fetched 2026-11-14T01:18:33.201Z",
  "floor_usd": 50000000,
  "protocols": [
    {
      "slug": "steakhouse-financial",
      "name": "Steakhouse Financial",
      "category": "Risk Curators",
      "chains": ["Base", "Ethereum"],
      "tvl_usd": 2753981495,
      "change_7d": -2.1935,
      "mcap_usd": null,
      "listed_at": "2025-05-20",
      "gecko_id": null,
      "symbol": null
    }
  ],
  "watchlist": ["steakhouse-financial"]
}
```

Each protocol carries exactly those ten fields. `as_of` is `YYYY-MM-DD`.
`floor_usd` is a positive integer. `watchlist` is a list of slugs.

Build a snapshot from DefiLlama by fetching the protocols list and
mapping each entry: `slug`, `name`, `category`, `chains`, `tvl` to
`tvl_usd`, `change_7d`, `mcap` to `mcap_usd` (null when the protocol
has no token), `listedAt` to `listed_at` as `YYYY-MM-DD` (null when
unknown), `gecko_id`, `symbol` (null when the protocol has no token).
Keep the fetch date as `as_of` and record the fetch time in `source`.
Never invent a protocol, a TVL, or a market cap that the source did
not return.

## Pre-token test

A protocol is pre-token when `mcap_usd`, `gecko_id` and `symbol` are
all null. Live-token protocols are never ranked; they are only the
market comps that price the board.

A pre-token protocol is rankable when it is not an exchange name
(Binance, Coinbase, Bybit, Kraken, Bitget, OKX, Bitfinex, Gemini),
its name does not end in a version (`V2`, `v3`, `1.2`), its name does
not contain wrapped, staked or staking, and its category is not
Bridge, Canonical Bridge, Liquid Staking, Liquid Restaking,
Restaked BTC or CEX.

## radar-2 formulas

All constants are fixed. Do not tune them per snapshot.

| Constant | Value |
| --- | --- |
| growth_weight | 0.5 |
| growth clamp | -60 to 120 percent |
| maturity floor / range / days | 0.6 / 0.4 / 1095 |
| unknown age | 365 days |
| shrink weight | 20 |
| small-sample cap | 0.35 when fewer than 5 live comps |
| multiple floor / cap | 0.05 / 1.0 |

Category multiple: for each category, take the median mcap/TVL of
the snapshot's own live protocols in that category (mcap present,
TVL above zero). Shrink it toward the global median (the median
mcap/TVL across all live protocols) with weight 20, then clamp it
to 0.05–1.0, and cap it at 0.35 when the category has fewer than
5 live comps. A category with no live comps falls back to the
global median. A protocol with no category uses the global median.

```
growth_pct   = clamp(change_7d, -60, 120), missing change_7d counts as 0
growth_mult  = 1 + (growth_pct / 100) * 0.5
age_days     = days from listed_at to as_of, at least 0, null when listed_at is missing
maturity     = 0.6 + min(age_days or 365, 1095) / 1095 * 0.4
implied      = max(1, round(tvl_usd * category_multiple * growth_mult * maturity))
```

There is no chain-breadth factor and no concave growth factor in
radar-2. Growth is linear with weight 0.5. Do not add factors the
model does not define.

Board: every watchlist slug present in the snapshot is ranked, then
every other rankable pre-token protocol with TVL below `floor_usd`,
sorted by TVL descending. Rank by implied value descending, ties
by slug ascending. Ranks run 1 to n with no gaps.

## Worked example (Steakhouse Financial, 2026-11-14)

TVL $2,753,981,495. Category Risk Curators, multiple 0.3025.
Growth -2.1935 percent, so growth multiplier 0.989.
Listed 2025-05-20, age 543 days, so maturity 0.7984.

```
2,753,981,495 * 0.3025 * 0.989 * 0.7984 = 657,799,657
```

That is the board's row 1 on that snapshot. Every other row recomputes the
same way from its own record.

## Farm plan

Six steps per row, derived from the protocol's own record only:

1. Fresh wallet, seed phrase offline.
2. The category action: supply for Lending/CDP, provide liquidity
   for Dexs/Yield, bridge for Bridge, stake for Staking/Restaking,
   margin for Perpetuals/Derivatives, fund a market for Prediction,
   deposit into a vault for Curators/Allocators, mint or deposit
   the stable asset for Stablecoins, mint the yield asset for RWA,
   buy cover for Insurance, deposit USDC otherwise.
3. One qualifying action a week.
4. Hold: 60 days when age is under 180, 45 days when under 365,
   30 days otherwise (30 when age is unknown).
5. Before withdrawing, claim only from the link the protocol's own
   points page publishes. Never pay to claim.
6. Log the wallet, dates and transactions.

Capital tier by TVL: $250 at $5B or more, $150 at $1B or more,
$100 at $100M or more, $50 below that. Gas per transaction by
first chain: Ethereum $15 first / $10 action / $5 weekly,
Solana $0.10, Binance $1 / $0.50 / $0.20, Arbitrum, Optimism,
Base, Polygon, zkSync Era, Blast, Linea, Scroll, Mantle,
Avalanche, Fantom and Gnosis $2 / $1 / $0.50, any other chain
$3 / $2 / $1. The top 40 rows carry one extra step: implied
value is a model, not a promise.

## Output

`board.json` holds `{"rows": [...]}`. Each row carries rank, slug,
name, category, chains, tvl_usd, change_7d, mcap_usd, listed_at,
gecko_id, symbol, token_status `pre-token`, age_days,
implied_value_usd, a `model` object with category_multiple,
growth_pct, growth_multiplier, maturity_multiplier and age_days,
and `farm_steps` as strings. Live-token protocols are not rows.

## Honesty rules

Implied value is a model estimate from the snapshot's own figures.
It is not a price prediction, not a launch date, and not a promise
that a protocol will ever issue a token. Always state the snapshot
`as_of` date and source. When a category rests on few live comps,
say so: one outlier cannot decide the board, and the small-sample
cap is what keeps the top honest. Farming uses real capital at
risk of loss. Never present a farm plan as a guarantee of an
airdrop.
