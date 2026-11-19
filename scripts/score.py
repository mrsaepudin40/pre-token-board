#!/usr/bin/env python3
"""Pre-Token Board model scorer, self-contained, standard library only.

Reads one snapshot JSON, ranks its pre-token protocols by implied value,
writes board.json. No network calls, no credentials, no other files read.

Usage:
    python3 score.py --input snapshot.json --output board.json
    python3 score.py --input snapshot.json --output board.json --top 10
"""
import argparse
import json
import math
import re
import sys
from datetime import date

MODEL_VERSION = "pre-token-board"
GROWTH_WEIGHT = 0.5
SHRINK_WEIGHT = 20
SMALL_N = 5
SMALL_N_CAP = 0.35
MULTIPLE_FLOOR = 0.05
MULTIPLE_CAP = 1.0
UNKNOWN_AGE_DAYS = 365
EXCLUDED = {"Bridge", "Canonical Bridge", "Liquid Staking",
            "Liquid Restaking", "Restaked BTC", "CEX"}
EXCHANGES = ["Binance", "Coinbase", "Bybit", "Kraken", "Bitget",
             "OKX", "Bitfinex", "Gemini"]
VERSIONED = re.compile(r"\s(V\d+(\.\d+)?|v\d+(\.\d+)?|\d+\.\d+)$")
WRAPPED = re.compile(r"\b(wrapped|staked|staking)\b", re.I)
L2 = {"Arbitrum", "Optimism", "Base", "Polygon", "zkSync Era", "Blast",
      "Linea", "Scroll", "Mantle", "Avalanche", "Fantom", "Gnosis"}


def round4(n):
    return math.floor(n * 10000 + 0.5) / 10000


def round_int(n):
    return math.floor(n + 0.5)


def median(values):
    s = sorted(values)
    mid = len(s) // 2
    if len(s) % 2 == 1:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2


def parse_snapshot(text):
    try:
        raw = json.loads(text)
    except json.JSONDecodeError:
        raise ValueError("snapshot.json is not JSON")
    if not isinstance(raw, dict):
        raise ValueError("snapshot.json is not a JSON object")
    if not isinstance(raw.get("as_of"), str) or not re.match(
            r"^\d{4}-\d{2}-\d{2}$", raw["as_of"]):
        raise ValueError("snapshot.json has no as_of date")
    if not isinstance(raw.get("source"), str):
        raise ValueError("snapshot.json has no source")
    if not isinstance(raw.get("floor_usd"), int) or raw["floor_usd"] <= 0:
        raise ValueError("snapshot.json has no floor_usd")
    if not isinstance(raw.get("protocols"), list):
        raise ValueError("snapshot.json has no protocols array")
    if not isinstance(raw.get("watchlist"), list) or any(
            not isinstance(s, str) for s in raw["watchlist"]):
        raise ValueError("snapshot.json has no watchlist of slugs")
    protocols = []
    for i, v in enumerate(raw["protocols"]):
        if not isinstance(v, dict):
            raise ValueError(f"snapshot.json's protocol {i} is not an object")
        if not isinstance(v.get("slug"), str) or not isinstance(
                v.get("name"), str) or not isinstance(
                v.get("tvl_usd"), (int, float)):
            raise ValueError(
                f"snapshot.json's protocol {i} lacks a slug, a name or a TVL")
        protocols.append({
            "slug": v["slug"], "name": v["name"],
            "category": v["category"] if isinstance(
                v.get("category"), str) else None,
            "chains": [c for c in v.get("chains", [])
                       if isinstance(c, str)],
            "tvl_usd": v["tvl_usd"],
            "change_7d": v["change_7d"] if isinstance(
                v.get("change_7d"), (int, float)) else None,
            "mcap_usd": v["mcap_usd"] if isinstance(
                v.get("mcap_usd"), (int, float)) else None,
            "listed_at": v["listed_at"] if isinstance(
                v.get("listed_at"), str) else None,
            "gecko_id": v["gecko_id"] if isinstance(
                v.get("gecko_id"), str) else None,
            "symbol": v["symbol"] if isinstance(
                v.get("symbol"), str) else None,
        })
    return {"as_of": raw["as_of"], "source": raw["source"],
            "floor_usd": raw["floor_usd"], "protocols": protocols,
            "watchlist": raw["watchlist"]}


def age_days(as_of, listed_at):
    if listed_at is None:
        return None
    try:
        a = date.fromisoformat(as_of)
        b = date.fromisoformat(listed_at)
    except ValueError:
        return None
    return max(0, (a - b).days)


def category_multiples(snapshot):
    live = [p for p in snapshot["protocols"]
            if p["mcap_usd"] is not None and p["tvl_usd"] > 0]
    raw_global = median([p["mcap_usd"] / p["tvl_usd"] for p in live])
    global_med = round4(raw_global)
    by_cat = {}
    for p in live:
        by_cat.setdefault(p["category"] or "", []).append(
            p["mcap_usd"] / p["tvl_usd"])
    multiples = {}
    for cat in sorted({p["category"] for p in snapshot["protocols"]
                       if p["category"] is not None}):
        values = by_cat.get(cat, [])
        if not values:
            multiples[cat] = global_med
        else:
            med = median(values)
            shrunk = (len(values) * med + SHRINK_WEIGHT * raw_global) / (
                len(values) + SHRINK_WEIGHT)
            cap = SMALL_N_CAP if len(values) < SMALL_N else MULTIPLE_CAP
            multiples[cat] = round4(min(cap, max(MULTIPLE_FLOOR, shrunk)))
    return multiples, global_med


def implied_value(p, as_of, multiple):
    age = age_days(as_of, p["listed_at"])
    growth = min(120, max(-60, p["change_7d"] if p["change_7d"] is not None else 0))
    growth_mult = 1 + (growth / 100) * GROWTH_WEIGHT
    age_model = age if age is not None else UNKNOWN_AGE_DAYS
    maturity = 0.6 + (min(max(age_model, 0), 1095) / 1095) * 0.4
    implied = max(1, round_int(
        p["tvl_usd"] * multiple * growth_mult * maturity))
    return implied, growth, growth_mult, maturity, age


def is_pre_token(p):
    return p["mcap_usd"] is None and p["gecko_id"] is None \
        and p["symbol"] is None


def is_rankable(p):
    if not is_pre_token(p):
        return False
    if p["category"] in EXCLUDED:
        return False
    if VERSIONED.search(p["name"]):
        return False
    if WRAPPED.search(p["name"]):
        return False
    return not any(p["name"].startswith(e) for e in EXCHANGES)


def gas_for(chain):
    if chain == "Ethereum":
        return ("$15", "$10", "$5")
    if chain == "Solana":
        return ("$0.10", "$0.10", "$0.10")
    if chain == "Binance":
        return ("$1", "$0.50", "$0.20")
    if chain in L2:
        return ("$2", "$1", "$0.50")
    return ("$3", "$2", "$1")


def capital_for(p):
    if p["tvl_usd"] >= 5_000_000_000:
        return 250
    if p["tvl_usd"] >= 1_000_000_000:
        return 150
    if p["tvl_usd"] >= 100_000_000:
        return 100
    return 50


def hold_days(age):
    if age is None:
        return 30
    if age < 180:
        return 60
    if age < 365:
        return 45
    return 30


def action_for(p, capital, chain):
    c = (p["category"] or "").lower()
    name = p["name"]
    if any(k in c for k in ("lend", "cdp", "collateral")):
        return f"Supply ${capital} of USDC to {name} on {chain} and keep the position open."
    if any(k in c for k in ("dex", "yield", "leveraged farm")):
        return f"Provide ${capital} of liquidity to {name}'s main pool on {chain} and keep the position open."
    if "bridge" in c:
        return f"Bridge ${capital} of USDC to {chain} through {name} and use the bridged funds in its app."
    if any(k in c for k in ("staking", "restak")):
        return f"Stake ${capital} of the chain's staking asset through {name} and keep the receipt."
    if any(k in c for k in ("perpetual", "derivative")):
        return f"Deposit ${capital} of USDC as margin on {name} and open one small hedge."
    if "prediction" in c:
        return f"Fund ${capital} and place one market position on {name}."
    if any(k in c for k in ("curator", "allocator")):
        return f"Deposit ${capital} into a {name} vault on {chain} and keep the shares."
    if "stable" in c:
        return f"Mint or deposit ${capital} of the stable asset through {name} on {chain}."
    if "rwa" in c:
        return f"Mint ${capital} of the protocol's yield asset on {chain} and hold it."
    if "insurance" in c:
        return f"Buy ${capital} of cover from {name} on {chain} and keep the policy."
    return f"Deposit ${capital} of USDC into {name} on {chain} and keep the position open."


def step_text(text, cost, time):
    s = f"{text} Cost: {cost}. Time: {time}."
    if len(s) > 600:
        s = s[:596] + "..."
    if len(s) < 20:
        s += " Hold the position and check the protocol's own page."
    return s


def farm_steps(p, age):
    chain = p["chains"][0] if p["chains"] else "its main chain"
    capital = capital_for(p)
    hold = hold_days(age)
    gas = gas_for(chain)
    steps = [
        ("Use a fresh wallet that holds only the funds you plan to farm, and keep its seed phrase offline.",
         f"under {gas[0]} of gas for the first transaction", "5 minutes"),
        (action_for(p, capital, chain),
         f"${capital} of capital and about {gas[1]} of gas", "15 minutes to set up"),
        ("Make one qualifying action each week, such as a deposit, a borrow, a swap or a vote.",
         f"about {gas[2]} of gas a week", "10 minutes a week"),
        (f"Hold the position for at least {hold} days so the activity is counted in more than one snapshot.",
         f"the ${capital} stays in the position", f"{hold} days"),
        ("Before you withdraw, open the protocol's own points or rewards page and claim only from the link it publishes.",
         "no fee to check, and never pay to claim", "10 minutes"),
        ("Write the wallet, the dates and every transaction in a farm log so you can repeat the position or unwind it.",
         "nothing but the log", "5 minutes"),
    ]
    return [step_text(t, c, tm) for t, c, tm in steps]


def build_board(snapshot):
    multiples, global_med = category_multiples(snapshot)
    by_slug = {p["slug"]: p for p in snapshot["protocols"]}
    chosen = {}
    for slug in snapshot["watchlist"]:
        if slug in by_slug:
            chosen[slug] = by_slug[slug]
    early = [p for p in snapshot["protocols"]
             if p["slug"] not in chosen and is_rankable(p)
             and p["tvl_usd"] < snapshot["floor_usd"]]
    early.sort(key=lambda p: (-p["tvl_usd"], p["slug"]))
    for p in early:
        chosen[p["slug"]] = p
    scored = []
    for p in chosen.values():
        multiple = multiples.get(p["category"], global_med) \
            if p["category"] is not None else global_med
        implied, growth, growth_mult, maturity, age = implied_value(
            p, snapshot["as_of"], multiple)
        scored.append((p, implied, growth, growth_mult, maturity, age, multiple))
    scored.sort(key=lambda s: (-s[1], s[0]["slug"]))
    rows = []
    for i, (p, implied, growth, growth_mult, maturity, age, multiple) in enumerate(scored):
        steps = farm_steps(p, age)
        if i < 40:
            steps.append(step_text(
                f"Implied value is a model, not a promise: this row's ${implied:,} is what the token could be worth if the protocol's record stayed as it is, never a guarantee it issues one.",
                "nothing but the check", "5 minutes"))
        rows.append({
            "rank": i + 1, "slug": p["slug"], "name": p["name"],
            "category": p["category"], "chains": p["chains"],
            "tvl_usd": p["tvl_usd"], "change_7d": p["change_7d"],
            "mcap_usd": p["mcap_usd"], "listed_at": p["listed_at"],
            "gecko_id": p["gecko_id"], "symbol": p["symbol"],
            "token_status": "pre-token", "age_days": age,
            "implied_value_usd": implied,
            "model": {"category_multiple": multiple, "growth_pct": growth,
                      "growth_multiplier": round4(growth_mult),
                      "maturity_multiplier": round4(maturity),
                      "age_days": age},
            "farm_steps": steps,
        })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--top", type=int, default=0)
    args = ap.parse_args()
    try:
        with open(args.input, encoding="utf-8") as f:
            snapshot = parse_snapshot(f.read())
        rows = build_board(snapshot)
    except (ValueError, OSError) as e:
        print(f"pre-token-board: {e}", file=sys.stderr)
        return 1
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"rows": rows}, f, indent=2)
        f.write("\n")
    shown = rows[:args.top] if args.top > 0 else rows[:10]
    for r in shown:
        print(f"{r['rank']:>3}  {r['name']:<30}  ${r['implied_value_usd']:,}")
    print(f"board: {len(rows)} rows, snapshot {snapshot['as_of']}, "
          f"source {snapshot['source']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
