import asyncio
import os
from integrated_pipeline import IntegratedTradingPipeline

# 10 Diverse combinations of crypto assets and timeframes
DEMO_TRADE_MATRIX = [
    {"symbol": "BTC/USDT", "tf": "5m"},
    {"symbol": "BTC/USDT", "tf": "15m"},
    {"symbol": "ETH/USDT", "tf": "5m"},
    {"symbol": "ETH/USDT", "tf": "1h"},
    {"symbol": "SOL/USDT", "tf": "15m"},
    {"symbol": "SOL/USDT", "tf": "1h"},
    {"symbol": "ADA/USDT", "tf": "15m"},
    {"symbol": "XRP/USDT", "tf": "1h"},
    {"symbol": "BTC/USDT", "tf": "4h"},
    {"symbol": "ETH/USDT", "tf": "4h"},
]

async def run_10_demo_trades():
    print("==========================================================")
    print("   AI TRADING ENGINE — 10 DEMO TRADE SIMULATION ($20 RISK)")
    print("==========================================================\n")

    # Force Paper Trading Mode with $20 fixed size per trade
    pipeline = IntegratedTradingPipeline(paper_trading=True, max_trade_capital=20.0)

    trades_executed = 0
    trades_rejected = 0
    executed_details = []

    try:
        for i, trade in enumerate(DEMO_TRADE_MATRIX, start=1):
            symbol = trade["symbol"]
            tf = trade["tf"]
            print(f"--- Trade {i}/10 | Asset: {symbol} | Timeframe: {tf} ---")
            
            # Temporary override timeframe on pipeline's fetch if available
            pipeline.data_engine.timeframe = tf
            
            res = await pipeline.run_cycle(symbol)
            status = res.get("status")

            if status == "APPROVED_AND_EXECUTED":
                trades_executed += 1
                executed_details.append({
                    "trade_num": i,
                    "symbol": symbol,
                    "timeframe": tf,
                    "strategy": res.get("selected_strategy"),
                    "position_usd": res.get("position_usd"),
                    "entry": res.get("entry"),
                    "sl": res.get("stop_loss"),
                    "tp": res.get("take_profit"),
                    "reasoning": res.get("reasoning")
                })
                print(f"✅ EXECUTED [{res.get('selected_strategy')}] | Size: ${res.get('position_usd')} | SL: ${res.get('stop_loss')} | TP: ${res.get('take_profit')}")
            else:
                trades_rejected += 1
                reason = res.get("reason", "Filtered by AI/Risk engine")
                print(f"❌ REJECTED/SKIPPED | Reason: {reason}")
            
            await asyncio.sleep(1)  # Brief delay between calls

        # --- SIMULATION SUMMARY ---
        print("\n==========================================================")
        print("                  DEMO TRADE RUN RESULTS                  ")
        print("==========================================================")
        total = len(DEMO_TRADE_MATRIX)
        approval_rate = (trades_executed / total) * 100
        print(f"Total Signals Processed : {total}")
        print(f"Approved & Executed      : {trades_executed}")
        print(f"Filtered / Passed       : {trades_rejected}")
        print(f"AI Signal Approval Rate : {approval_rate:.1f}%\n")

        if executed_details:
            print("--- APPROVED TRADES BREAKDOWN ---")
            for t in executed_details:
                print(f"Trade #{t['trade_num']} | {t['symbol']} ({t['timeframe']}) -> {t['strategy']}")
                print(f"  Alloc: ${t['position_usd']} | Entry: ${t['entry']} | SL: ${t['sl']} | TP: ${t['tp']}")
                print(f"  AI Logic: {t['reasoning'][:120]}...\n")

    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(run_10_demo_trades())
