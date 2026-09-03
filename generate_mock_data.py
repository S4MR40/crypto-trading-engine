import csv
import random
from datetime import datetime, timedelta

# Create mock trades_log.csv
trades_header = [
    "timestamp", "event_type", "symbol", "direction", "strategy",
    "entry_price", "exit_price", "pnl_usd", "stop_loss", "take_profit",
    "rr_ratio", "position_usd", "balance_after"
]

strategies = ["TREND_SCALP_LONG", "TREND_SCALP_SHORT", "MEAN_REVERSION_LONG", "MEAN_REVERSION_SHORT"]
symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

start_time = datetime.utcnow() - timedelta(days=3)
balance = 1000.0

trades = []
for i in range(12):
    t_time = start_time + timedelta(hours=i*6)
    symbol = random.choice(symbols)
    strat = random.choice(strategies)
    direction = "LONG" if "LONG" in strat else "SHORT"
    entry = round(random.uniform(2000, 60000), 2)
    
    # Simulate 60% win rate
    is_win = random.random() < 0.6
    pnl = round(random.uniform(1.5, 4.0), 2) if is_win else round(random.uniform(-1.5, -0.8), 2)
    exit_price = round(entry * (1 + (pnl / 20.0)), 2)
    balance += pnl
    
    event = "EXIT_TAKE_PROFIT" if is_win else "EXIT_STOP_LOSS"
    trades.append([
        t_time.strftime("%Y-%m-%d %H:%M:%S"), event, symbol, direction, strat,
        entry, exit_price, pnl, entry * 0.98, entry * 1.04, 2.0, 20.0, round(balance, 2)
    ])

with open("trades_log.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(trades_header)
    writer.writerows(trades)

# Create mock equity_log.csv
equity_header = ["timestamp", "realized_balance", "unrealized_pnl", "total_equity", "active_positions"]
equity_rows = []
curr_eq = 1000.0

for i in range(50):
    e_time = start_time + timedelta(hours=i*1.5)
    curr_eq += random.uniform(-1.2, 2.0)
    unrealized = round(random.uniform(-0.5, 0.5), 2)
    equity_rows.append([
        e_time.strftime("%Y-%m-%d %H:%M:%S"),
        round(curr_eq, 2),
        unrealized,
        round(curr_eq + unrealized, 2),
        random.choice([0, 1, 2])
    ])

with open("equity_log.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(equity_header)
    writer.writerows(equity_rows)

print("✅ Sample data generated for trades_log.csv and equity_log.csv.")
