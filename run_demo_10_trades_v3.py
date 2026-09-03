import asyncio
from integrated_pipeline_v3 import IntegratedTradingPipelineV3

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

async def run_v3_demo_trades():
    print("==========================================================")
    print("  MULTI-STRATEGY ENGINE (LONG/SHORT/RSI) — $20 SIMULATION")
    print("==========================================================\n")

    pipeline = IntegratedTradingPipelineV3(paper_trading=True, max_trade_capital=20.0)

    trades_executed = 0
    trades_rejected = 0

    try:
        for i, trade in enumerate(DEMO_TRADE_MATRIX, start=1):
            symbol = trade["symbol"]
            tf = trade["tf"]
            print(f"--- Trade {i}/10 | Asset: {symbol} | Timeframe: {tf} ---")
            
            res = await pipeline.run_cycle(symbol, timeframe=tf)
            if res.get("status") == "APPROVED_AND_EXECUTED":
                trades_executed += 1
                direction = res.get("direction")
                strat = res.get("selected_strategy")
                rr = res.get("rr_ratio")
                print(f"✅ EXECUTED [{direction} | {strat}] | Size: ${res.get('position_usd')} | R:R: {rr} | SL: ${res.get('stop_loss')} | TP: ${res.get('take_profit')}")
            else:
                trades_rejected += 1
                print(f"❌ REJECTED | Reason: {res.get('reason')}")
            
            await asyncio.sleep(0.3)

        print("\n==========================================================")
        print(f"Total: {len(DEMO_TRADE_MATRIX)} | Executed: {trades_executed} | Rejected: {trades_rejected}")
        print("==========================================================")

    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(run_v3_demo_trades())
