import json
import math
import subprocess
import time
import requests

# --- ALGORITHM MOMENTUM WEIGHTS ---
WEIGHT_VOL = 0.35
WEIGHT_BUY_VELOCITY = 0.65

# --- SYSTEM FILTERS ---
MIN_MARKET_CAP_USD = 30000
MAX_BATCH_SIZE = 30  # DEX Screener max block constraint


def fetch_all_target_mints():
    """
    Queries BOTH GMGN Trenches (Completed) and GMGN Trending (Pump.fun)
    to extract a complete, deduplicated firehose list of active contract addresses.
    """
    mints = set()

    # 1. Pull from Trenches
    trenches_cmd = [
        "gmgn-cli",
        "market",
        "trenches",
        "--chain",
        "sol",
        "--type",
        "completed",
        "--launchpad-platform",
        "Pump.fun",
        "--limit",
        "80",
    ]

    # 2. Pull from Trending
    trending_cmd = [
        "gmgn-cli",
        "market",
        "trending",
        "--chain",
        "sol",
        "--interval",
        "5m",
        "--platform",
        "Pump.fun",
    ]

    # Execute Trenches Data Gather
    try:
        res = subprocess.run(trenches_cmd, capture_output=True, text=True, check=True)
        payload = json.loads(res.stdout)
        for token in payload.get("completed", []):
            if isinstance(token, dict) and token.get("address"):
                mints.add(token["address"])
    except Exception as e:
        print(f"Warning: GMGN Trenches collection skipped or failed: {e}")

    # Execute Trending Data Gather
    try:
        res = subprocess.run(trending_cmd, capture_output=True, text=True, check=True)
        payload = json.loads(res.stdout)
        for token in payload.get("data", {}).get("rank", []):
            if isinstance(token, dict) and token.get("address"):
                mints.add(token["address"])
    except Exception as e:
        print(f"Warning: GMGN Trending collection skipped or failed: {e}")

    return list(mints)


def run_total_market_analysis(scored_tokens):
    """
    Computes and prints a macro overview summary block derived from
    the real-time dataset processed by the scoring pipeline.
    """
    if not scored_tokens:
        print("\n[!] Insufficient token depth to compute macro matrix report.")
        return

    total_tokens = len(scored_tokens)
    total_5m_vol = sum(t["vol"] for t in scored_tokens)
    avg_mcap = sum(t["mcap"] for t in scored_tokens) / total_tokens

    # Count micro caps vs established assets
    under_100k = sum(1 for t in scored_tokens if t["mcap"] < 100000)
    over_100k = total_tokens - under_100k

    # Isolate top volume outlier
    top_vol_token = max(scored_tokens, key=lambda x: x["vol"])

    print("\n" + "=" * 60)
    print("      GLOBAL PUMP.FUN MARKET ANALYSIS & HEALTH REPORT      ")
    print("=" * 60)
    print(f"► Active Vetted Pools Tracked : {total_tokens}")
    print(f"► Combined 5-Minute Volume    : ${total_5m_vol:,}")
    print(f"► Average Pipeline Market Cap : ${int(avg_mcap):,}")
    print(f"► Micro-Cap Tier (<$100k MC)  : {under_100k} tokens")
    print(f"► Mid-Cap Tier (>$100k MC)    : {over_100k} tokens")
    print(
        f"► 5M Volume Apex Leader       : {top_vol_token['symbol']} (${top_vol_token['vol']:,})"
    )
    print("=" * 60 + "\n")


def enrich_and_score_with_dexscreener(mints, exclude_mints=None):
    """
    Takes unified mint array, splits into 30-item batches, enriches data
    via DEX Screener, handles filtering boundaries, and scores.
    """
    if not mints:
        return []

    exclude_set = set(exclude_mints) if exclude_mints else set()

    mints = [m for m in mints if m not in exclude_set]

    all_pairs = []

    for i in range(0, len(mints), MAX_BATCH_SIZE):
        chunk = mints[i : i + MAX_BATCH_SIZE]
        mints_csv = ",".join(chunk)
        url = f"https://api.dexscreener.com/tokens/v1/solana/{mints_csv}"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue
            pairs = response.json()
            if isinstance(pairs, dict):
                pairs = pairs.get("pairs", [])
            if pairs:
                all_pairs.extend(pairs)
            time.sleep(0.2)
        except Exception:
            continue

    scored_tokens = []
    seen_mints = set()
    now_ms = int(time.time() * 1000)

    for pair in all_pairs:
        base_token = pair.get("baseToken", {})
        mint = base_token.get("address", "")

        if not mint or mint in seen_mints:
            continue
        seen_mints.add(mint)

        market_cap = pair.get("marketCap", 0)
        if market_cap < MIN_MARKET_CAP_USD:
            continue

        symbol = base_token.get("symbol", "UNKNOWN").strip()
        volume_stats = pair.get("volume", {})
        tx_stats = pair.get("txns", {})

        vol_5m = volume_stats.get("m5", 0)
        buys = tx_stats.get("m5", {}).get("buys", 0)
        sells = tx_stats.get("m5", {}).get("sells", 0)
        swaps = buys + sells

        created_at = pair.get("pairCreatedAt", 0)
        if created_at > 0:
            age_hours = max((now_ms - created_at) / 3600000.0, 0.02)
        else:
            age_hours = 1.0

        # Mathematical Scoring Logic
        log_vol = math.log(vol_5m + 1) if vol_5m > 0 else 0
        buy_velocity = (buys**2) / swaps if swaps > 0 else 0
        age_decay = 1.0 / math.sqrt(age_hours) if age_hours > 0.1 else 3.0

        score = WEIGHT_VOL * log_vol + WEIGHT_BUY_VELOCITY * buy_velocity
        scored_tokens.append(
            {
                "symbol": symbol,
                "score": round(score, 2),
                "vol": int(vol_5m),
                "buys": buys,
                "sells": sells,
                "mcap": int(market_cap),
                "age": round(age_hours, 1),
                "mint": mint,
            }
        )

    scored_tokens.sort(key=lambda x: x["score"], reverse=True)
    return scored_tokens


def get_market_signals(exclude_mints=None):
    """
    MASTER FUNCTION: Coordinates the full target extraction, filtration,
    and DEX enrichment sequence. Returns a clean payload dictionary.
    """
    raw_mints = fetch_all_target_mints()
    scored_list = enrich_and_score_with_dexscreener(
        raw_mints, exclude_mints=exclude_mints
    )

    return {"raw_collected_count": len(raw_mints), "vetted_tokens": scored_list}


# --- LOCAL TESTING / CALLABLE EXECUTION ONLY ---
if __name__ == "__main__":
    # Example blocklist: pass in any CAs you want to completely skip
    blacklist = ["7JfgvQdDAWnZodTzkEVdDmVbHmXD1YjgTupxc6W2pump"]

    print("[*] Launching pipeline through Master function...")
    pipeline_data = get_market_signals(exclude_mints=blacklist)

    scored_list = pipeline_data["vetted_tokens"]
    raw_total = pipeline_data["raw_collected_count"]

    print(
        f"[*] Aggregator pulled {raw_total} pools. Evaluated and processed survivors..."
    )

    print(scored_list)

    # # --- RENDER MACRO SUMMARY REPORT ---
    # if not scored_list:
    #     print("\n[!] Insufficient token depth to compute macro matrix report.")
    # else:
    #     total_tokens = len(scored_list)
    #     total_5m_vol = sum(t["vol"] for t in scored_list)
    #     avg_mcap = sum(t["mcap"] for t in scored_list) / total_tokens
    #     under_100k = sum(1 for t in scored_list if t["mcap"] < 100000)
    #     over_100k = total_tokens - under_100k
    #     top_vol_token = max(scored_list, key=lambda x: x["vol"])

    #     print("\n" + "=" * 60)
    #     print("      GLOBAL PUMP.FUN MARKET ANALYSIS & HEALTH REPORT      ")
    #     print("=" * 60)
    #     print(f"► Active Vetted Pools Tracked : {total_tokens}")
    #     print(f"► Combined 5-Minute Volume    : ${total_5m_vol:,}")
    #     print(f"► Average Pipeline Market Cap : ${int(avg_mcap):,}")
    #     print(f"► Micro-Cap Tier (<$100k MC)  : {under_100k} tokens")
    #     print(f"► Mid-Cap Tier (>$100k MC)    : {over_100k} tokens")
    #     print(
    #         f"► 5M Volume Apex Leader       : {top_vol_token['symbol']} (${top_vol_token['vol']:,})"
    #     )
    #     print("=" * 60 + "\n")

    # # --- RENDER GRANULAR LEADERBOARD VIEW ---
    # print("=" * 135)
    # print(
    #     f"{'RANK':<5} | {'SYMBOL':<10} | {'SCORE':<9} | {'VOL 5M':<8} | {'BUYS/SELLS':<11} | {'MCAP':<8} | {'AGE (H)':<7} | {'MINT':<44}"
    # )
    # print("=" * 135)

    # if not scored_list:
    #     print(
    #         f"{'No active matching tokens returned from the market data verification pipeline.':^135}"
    #     )
    # else:
    #     for idx, t in enumerate(scored_list[:20], 1):
    #         buys_sells_str = f"{t['buys']}/{t['sells']}"
    #         print(
    #             f"#{idx:<4} | {t['symbol'][:8]:<10} | {t['score']:<9} | ${t['vol']:<7} | {buys_sells_str:<11} | ${t['mcap']:<7} | {t['age']:<7} | {t['mint']:<44}"
    #         )

    # print("=" * 135 + "\n")
