import pandas as pd

excel_file = "backtest_results.xlsx"

print("=" * 80)
print("📊 PERFORMANCE STATISTICS SUMMARY")
print("=" * 80)
stats_df = pd.read_excel(excel_file, sheet_name="Performance Statistics")
print(stats_df.to_string(index=False))

print("\n" + "=" * 80)
print("📜 RECENT TRADES (Last 10)")
print("=" * 80)
trades_df = pd.read_excel(excel_file, sheet_name="Trade Log")
if not trades_df.empty:
    print(trades_df.tail(10).to_string(index=False))
else:
    print("No trades executed.")

print("\n" + "=" * 80)
print("📈 EQUITY CURVE PREVIEW (Cleaned Headers)")
print("=" * 80)
# Read first two rows as multi-index headers
equity_df = pd.read_excel(excel_file, sheet_name="Equity Curves", header=[0, 1], index_col=0)
print(equity_df.tail(5).to_string())
