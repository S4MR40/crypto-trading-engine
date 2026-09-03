import pandas as pd
import glob
import os

def analyze_trades():
    trade_files = glob.glob("trades_log_*.csv")
    if not trade_files:
        print("\n⚠️ No trade log CSV files found.")
        return

    all_trades = []
    for f in trade_files:
        df = pd.read_csv(f)
        df['exchange'] = f.split('_')[-1].replace('.csv', '').upper()
        all_trades.append(df)

    df_trades = pd.concat(all_trades, ignore_index=True)
    
    exits = df_trades[df_trades['event_type'].str.startswith('EXIT')].copy()

    if exits.empty:
        print("\n⚠️ Trades are currently active, but no completed (closed) trades logged yet.")
        return

    exits['pnl_usd'] = pd.to_numeric(exits['pnl_usd'])
    
    total_trades = len(exits)
    wins = exits[exits['pnl_usd'] > 0]
    losses = exits[exits['pnl_usd'] < 0]
    
    win_rate = (len(wins) / total_trades) * 100
    gross_profit = wins['pnl_usd'].sum()
    gross_loss = abs(losses['pnl_usd'].sum())
    net_pnl = exits['pnl_usd'].sum()
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

    print("\n==========================================================")
    print("                STRATEGY PERFORMANCE METRICS              ")
    print("==========================================================")
    print(f"Total Completed Trades : {total_trades}")
    print(f"Winning Trades         : {len(wins)} ({win_rate:.2f}%)")
    print(f"Losing Trades          : {len(losses)} ({100 - win_rate:.2f}%)")
    print(f"Gross Profit           : +${gross_profit:.2f}")
    print(f"Gross Loss             : -${gross_loss:.2f}")
    print(f"Net Profit/Loss        : ${net_pnl:+.2f}")
    print(f"Profit Factor          : {profit_factor:.2f}")
    print("----------------------------------------------------------")
    print("\nRecent Closed Trades Breakdown:")
    print(exits[['timestamp', 'exchange', 'symbol', 'direction', 'strategy', 'pnl_usd', 'balance_after']].tail(10).to_string(index=False))

if __name__ == "__main__":
    analyze_trades()
