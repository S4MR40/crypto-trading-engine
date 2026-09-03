import asyncio
from integrated_pipeline_v3 import IntegratedTradingPipelineV3

DEMO_TRADE_MATRIX = [
    {"symbol": "BTC/USDT", "tf": "15m"},
    {"symbol": "SOL/USDT", "tf": "15m"},
    {"symbol": "ADA/USDT", "tf": "15m"},
]

async def run_atr_trailing_demo():
    print("==========================================================")
    print("  ATR DYNAMIC STOPS & TRAILING STOP LOSS ENGINE TEST      ")
    print("==========================================================\n")

    pipeline = IntegratedTradingPipelineV3(paper_trading=True, max_trade_capital=20.0)

    try:
        # Step 1: Execute initial batch of trades
        print("--- PHASE 1: Executing Signal Matrix ---")
        for trade in DEMO_TRADE_MATRIX:
            res = await pipeline.run_cycle(trade["symbol"], timeframe=trade["tf"])
            if res.get("status") == "APPROVED_AND_EXECUTED":
                print(f"✅ EXECUTED [{res['direction']} | {res['symbol']}] | Entry: ${res['entry']} | ATR: ${res['atr']} | SL: ${res['stop_loss']} | TP: ${res['take_profit']}")
            else:
                print(f"❌ REJECTED [{trade['symbol']}] | {res.get('reason')}")

        # Step 2: Simulate price movements upwards/downwards to test trailing engine
        print("\n--- PHASE 2: Simulating Market Movement & Trailing Stop Updates ---")
        
        # Simulated mark price movement: BTC surges +$2,500, SOL surges +$5.00, ADA drops -$0.008 (profitable short)
        simulated_prices_step_1 = {
            "BTC/USDT": 79500.00,  # BTC moves up +1.7x ATR -> Triggers Break-Even
            "SOL/USDT": 107.50,    # SOL moves up +2.1x ATR -> Triggers Dynamic Trail
            "ADA/USDT": 0.1910,    # ADA moves down +2.1x ATR (Short Profit) -> Triggers Dynamic Trail
        }

        updates = pipeline.update_trailing_stops(simulated_prices_step_1)
        for update in updates:
            print(f"🔔 {update}")

    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(run_atr_trailing_demo())
