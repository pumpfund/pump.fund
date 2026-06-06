```markdown
# 🚀 PumpFund ETF 

> **Algorithmic volume indexing and automated batch memecoin distributions on Solana.**

Hold `$PUMPFUND`, receive direct payouts in high-momentum assets. No staking required. PumpFund is a decentralized, automated ETF that passively harvests the hottest coins on Pump.fun. Every 10 minutes, pool fees are auto-swapped via Jupiter into a dynamically scored trending token and airdropped straight to holders' wallets.

---

## 🧠 The Trending Algorithm (The Secret Sauce)

Unlike manual funds, PumpFund removes human emotion and relies strictly on a quantitative scoring model to identify the token with the highest immediate momentum. 

Every 20 seconds, the Python keeper isolates the absolute best target using a proprietary 5-minute velocity formula:

**`Score = (0.35 × Log(Volume_5m)) + (0.65 × Buy_Velocity)`**

### Algorithm Breakdown:
* **Logarithmic Volume (35% Weight):** We use `math.log(vol_5m + 1)` rather than raw volume. This prevents massive, established mega-caps from completely overshadowing newly launched micro-caps that are experiencing exponential, parabolic growth.
* **Buy Velocity (65% Weight):** Calculated as `(Buys² / Swaps)`. This heavily penalizes farm tokens with high volume but equal buy/sell pressure (wash trading), while exponentially rewarding tokens experiencing extreme, one-sided buy pressure and FOMO.
* **Minimum Thresholds:** Tokens must meet a strict `$30,000` Market Cap floor to protect the fund from illiquid honeypots.

---

## ⚙️ How It Works (The Core Protocol)

The PumpFund engine operates on an automated 4-step perpetual loop:

1. **ACCUMULATE (Fees Pile Up):** Buy and hold `$PUMPFUND`. The Meteora pool automatically accumulates a 5% LP trading fee in wSOL with every buy and sell.
2. **SCAN (Algorithmic Indexing):** The keeper script continuously aggregates active Pump.fun contracts via multiple aggregators and enriches them via DexScreener, running them through the Trending Algorithm to rank the market in real-time.
3. **SWEEP (Jupiter Routing):** When the 10-minute countdown hits zero, the dispatcher claims the accrued wSOL fees and swaps 100% of it into the isolated #1 ranked token via Jupiter.
4. **DROP (Automatic Airdrop):** An on-chain snapshot triggers instantly. The acquired tokens are distributed directly to `$PUMPFUND` holders proportionally based on their holding weight. No manual claims, zero effort.

---

## 🛠️ Tech Stack

**Frontend & Dashboard**
* **Framework:** Next.js / React (`app` router)
* **Styling:** Tailwind CSS
* **Animations:** Framer Motion
* **Database & Realtime:** Supabase (PostgreSQL with Realtime WebSockets for live, sub-second dashboard updates)

**Backend & Keepers (Python)**
* **Market Aggregation:** `gmgn-cli` (Trenches & Trending) + DexScreener API
* **Blockchain Interaction:** Solana RPC (`solana-py`, `solders`)
* **State Management:** HTTP requests to Next.js API endpoints (`httpx`, `requests`)

---

## 📂 Repository Structure

* **`app/page.tsx`**: The main Next.js dashboard. Features live countdowns, real-time WebSocket state syncing, interactive SVG sparkline charts, and a "Recipient Log Portal" to scan wallet earnings.
* **`trending.py`**: The quantitative market scanner. Pulls raw contract addresses, enriches them, calculates the "Trending Score", and ranks the targets.
* **`keeper.py` / `dispatcher.py`**: The orchestration daemons. They ping the database to check schedules, trigger state changes (Scheduled -> Picking -> Airdropping -> Complete), interact with the Solana blockchain to execute the batch transfers, and schedule the next cycle.

---

## 🚀 Setup & Installation

### 1. Frontend Setup (Next.js)

Clone the repository and install dependencies:
```bash
npm install
# or
yarn install

```

Set up your Supabase Database with the required tables (`coins`, `airdrops`, `index_stats`, `leaderboard`, etc.).

**Crucial Database Step:** You must enable CDC (Change Data Capture) Replication in Supabase so the Next.js frontend can listen to Python keeper updates via WebSockets. Run this in your Supabase SQL Editor:

```sql
ALTER PUBLICATION supabase_realtime ADD TABLE coins;
ALTER PUBLICATION supabase_realtime ADD TABLE airdrops;

```

Run the development server:

```bash
npm run dev

```

### 2. Keeper Setup (Python)

Ensure you have Python 3.9+ installed. Install the required Python packages:

```bash
pip install requests httpx python-dotenv solana solders

```

*(Note: You will also need the `gmgn-cli` tool installed globally for the trending pipeline to successfully extract initial target mints).*

---

## 🔑 Environment Variables

Create a `.env` file in the root of your project for both the Next.js app and the Python keepers:

```env
# Next.js Application
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Python Keepers
DEV_RPC_URL=[https://api.devnet.solana.com](https://api.devnet.solana.com) # Or Mainnet Helius/QuickNode URL
KEEPER_API_KEY=your_secure_random_string_here # Must match the API check in Next.js
BOT_PRIVATE_KEY=[123, 45, 67, 89...] # Byte array of the distributing wallet

```

---

## 🤖 Running the Keepers

The Python daemons are designed to run indefinitely in the background (e.g., using `pm2` or `tmux` on a VPS).

**1. The Trending Matrix Updater**
Scans the market, runs the algorithm, and updates the dashboard with the Top 3 trending coins every 20 seconds.

```bash
python trending_keeper.py

```

**2. The Dispatcher / Orchestrator**
Listens to the airdrop timer. When the countdown hits zero, it locks the #1 trending coin, runs the on-chain Solana airdrop, updates the portfolio PnL, and schedules the next drop.

```bash
python dispatcher.py

```

---

## ⚠️ Disclaimer

Not financial advice. Single-token distributions are decided programmatically from the top trending token at the time of execution. All cycles are settled on-chain.
