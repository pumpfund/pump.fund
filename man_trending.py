import os
import sys
import time
import requests
from dotenv import load_dotenv

# --- ENVIRONMENT CONFIGURATION ---
load_dotenv()

BASE_URL = os.getenv("NEXT_PUBLIC_APP_URL")
KEEPER_API_KEY = os.getenv("KEEPER_API_KEY")

if not BASE_URL or not KEEPER_API_KEY:
    print(
        "❌ CONFIGURATION ERROR: 'NEXT_PUBLIC_APP_URL' or 'KEEPER_API_KEY' missing from .env"
    )
    sys.exit(1)

# --- API CONFIGURATION ---
API_ENDPOINT = f"{BASE_URL}/api/coins"
API_TOKEN = f"Bearer {KEEPER_API_KEY}"

# --- MANUAL TARGET OVERRIDES ---
# Leave this list empty [] to be prompted in the terminal when running the script,
# or paste 3 mints here to skip the prompts and push instantly.
MANUAL_MINTS = [
    # "MINT_ADDRESS_1_HERE",
    # "MINT_ADDRESS_2_HERE",
    # "MINT_ADDRESS_3_HERE",
]


def fetch_complete_token_data(mint):
    """
    Queries DexScreener to pull complete real-time market cap,
    symbols, logos, and socials for manual asset profiling.
    """
    try:
        print(f"🔍 Compiling live market metrics for CA: {mint[:8]}...")
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            data = res.json()
            pairs = data.get("pairs", [])
            if not pairs:
                print(f"⚠️ DexScreener returned zero active pairs for: {mint[:8]}")
                return None

            primary_pair = pairs[0]
            base_token = primary_pair.get("baseToken", {})
            info = primary_pair.get("info", {})
            socials = info.get("socials", [])

            # Extract market cap with FDV fallback
            mcap = primary_pair.get("marketCap") or primary_pair.get("fdv") or 10000
            symbol = base_token.get("symbol", "UNKNOWN")
            name = base_token.get("name", symbol)
            logo = info.get("imageUrl", "https://example.com/default.png")

            twitter = next(
                (s.get("url") for s in socials if s.get("type") == "twitter"), ""
            )

            return {
                "ticker": symbol,
                "name": name,
                "marketCap": int(mcap),
                "contractAddress": mint,
                "logo": logo,
                "twitter": twitter,
            }
    except Exception as e:
        print(f"❌ Error fetching metadata from DexScreener: {e}")
    return None


def push_to_dashboard(cleaned_coins):
    """Dispatches the structured manual token payload to the central dashboard ledger."""
    headers = {"Authorization": API_TOKEN, "Content-Type": "application/json"}
    payload = {"coins": cleaned_coins}

    try:
        print(
            f"[*] Broadcasting {len(cleaned_coins)} manual target assets to Dashboard API..."
        )
        response = requests.post(
            API_ENDPOINT, json=payload, headers=headers, timeout=10
        )
        if response.status_code in [200, 201]:
            print("[✓] Dashboard manual synchronization completed successfully.")
            return True
        else:
            print(
                f"[!] Server rejected payload: Status {response.status_code} - {response.text}"
            )
    except Exception as e:
        print(f"[!] Transmission matrix breakdown: {e}")
    return False


def main():
    print("=" * 80)
    print("🛠️  MANUAL TRENDING KEEPER DISPATCH ENGINE ONLINE")
    print(f"🔗 Target Dashboard API Gateway: {API_ENDPOINT}")
    print("=" * 80)

    target_mints = [m for m in MANUAL_MINTS if m.strip()]

    # If no mints are hardcoded, collect them cleanly via user input prompts
    if not target_mints:
        print(
            "\n[+] No hardcoded mints found. Please provide exactly 3 token contract coordinates:"
        )
        for i in range(1, 4):
            while True:
                mint_input = input(f"    👉 Enter Mint Address #{i}: ").strip()
                if len(mint_input) >= 32:  # Safe Solana public key length floor check
                    target_mints.append(mint_input)
                    break
                print(
                    "    ❌ Invalid address length. Please provide a true Solana contract string."
                )

    # Slice strictly to the top 3 items to preserve database structural bounds
    target_mints = target_mints[:3]

    print("\n[*] Initializing target extraction sequences...")
    compiled_payload_coins = []

    # Assign artificial matching trending scores based on the input order sequence (Rank #1, #2, #3)
    mock_scores = [100.0, 85.0, 70.0]

    for idx, mint in enumerate(target_mints):
        token_data = fetch_complete_token_data(mint)
        if token_data:
            # Map required presentation layer configurations
            token_data["price"] = 0.0
            token_data["change24h"] = 0.0
            token_data["trendingScore"] = mock_scores[idx]
            compiled_payload_coins.append(token_data)
            print(
                f"    🔥 Slot #{idx+1} Isolated: ${token_data['ticker']} | MCAP: ${token_data['marketCap']:,}"
            )
        else:
            print(f"    ❌ Skipping invalid or untrackable address slot: {mint}")

    if not compiled_payload_coins:
        print(
            "\n❌ Process Terminated: Could not resolve valid network parameters for any provided target."
        )
        sys.exit(1)

    print("\n" + "=" * 60)
    print("                    MANUAL INJECTION SUMMARY                 ")
    print("=" * 60)
    for index, coin in enumerate(compiled_payload_coins, 1):
        print(
            f" #{index} | ${coin['ticker']:<10} | MCAP: ${coin['marketCap']:,} | CA: {coin['contractAddress'][:12]}..."
        )
    print("=" * 60 + "\n")

    # Broadcast directly to your central web infrastructure
    success = push_to_dashboard(compiled_payload_coins)
    if success:
        print(
            "\n🏆 Manual override cycle completed successfully. Dashboard is updated."
        )
    else:
        print("\n❌ Failed to sync manual update to web architecture.")


if __name__ == "__main__":
    main()
