import asyncio
from integrated_pipeline import IntegratedTradingPipeline

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

async def run_strict_demo_trades():
    print("==========================================================")
    print("  STRICT AI TRADING ENGINE — 10 DEMO SIMULATION ($20 RISK)")
    print("==========================================================\n")

    pipeline = IntegratedTradingPipeline(paper_trading=True, max_trade_capital=20.0)

    trades_executed = 0
    trades_rejected = 0
    executed_details = []

    try:
        for i, trade in enumerate(DEMO_TRADE_MATRIX, start=1):
            symbol = trade["symbol"]
            tf = trade["tf"]
            print(f"--- Trade {i}/10 | Asset: {symbol} | Timeframe: {tf} ---")
            
            res = await pipeline.run_cycle(symbol, timeframe=tf)
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
                    "rr": res.get("rr_ratio"),
                    "reasoning": res.get("reasoning")
                })
                print(f"✅ EXECUTED [{res.get('selected_strategy')}] | Size: ${res.get('position_usd')} | R:R: {res.get('rr_ratio')} | SL: ${res.get('stop_loss')} | TP: ${res.get('take_profit')}")
            else:
                trades_rejected += 1
                reason = res.get("reason", "Filtered by AI/Risk engine")
                print(f"❌ REJECTED | Reason: {reason}")
            
            await asyncio.sleep(0.5)

        # --- SIMULATION SUMMARY ---
        print("\n==========================================================")
        print("                  STRICT RUN RESULTS                      ")
        print("==========================================================")
        total = len(DEMO_TRADE_MATRIX)
        approval_rate = (trades_executed / total) * 100
        print(f"Total Signals Processed : {total}")
        print(f"Approved & Executed      : {trades_executed}")
        print(f"Filtered / Rejected     : {trades_rejected}")
        print(f"Filtered Approval Rate  : {approval_rate:.1f}%\n")

        if executed_details:
            print("--- APPROVED TRADES BREAKDOWN ---")
            for t in executed_details:
                print(f"Trade #{t['trade_num']} | {t['symbol']} ({t['timeframe']}) -> {t['strategy']}")
                print(f"  Alloc: ${t['position_usd']} | Entry: ${t['entry']} | R:R: {t['rr']} | SL: ${t['sl']} | TP: ${t['tp']}")
                print(f"  AI Logic: {t['reasoning']}\n")

    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(run_strict_demo_trades())
