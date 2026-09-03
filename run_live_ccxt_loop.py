import asyncio
from integrated_pipeline_ccxt import CCXTTradingPipeline

EXCHANGE_CONFIGS = [
    {
        "exchange_id": "binance",
        "symbols": ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    },
    {
        "exchange_id": "kraken",
        "symbols": ["BTC/USD", "ETH/USD", "SOL/USD"]
    }
]

async def run_exchange_loop(config):
    exchange_id = config["exchange_id"]
    symbols = config["symbols"]
    
    print(f"🚀 Launching Pipeline Engine for [{exchange_id.upper()}]...")
    pipeline = CCXTTradingPipeline(exchange_id=exchange_id, paper_trading=True, use_ai_filter=True)
    pipeline.log_equity()

    try:
        while True:
            current_prices = {}
            print(f"\n--- [{exchange_id.upper()}] CYCLE START ---")
            for symbol in symbols:
                res = await pipeline.run_cycle(symbol, timeframe="15m")
                if res.get("status") == "APPROVED_AND_EXECUTED":
                    print(f"✅ EXECUTED [{exchange_id.upper()} | {res['direction']} | {res['selected_strategy']}]")
                    print(f"   {symbol} | Entry: ${res['entry']} | SL: ${res['stop_loss']} | TP: ${res['take_profit']}")
                    current_prices[symbol] = res['entry']
                else:
                    print(f"❌ REJECTED [{exchange_id.upper()} | {symbol}] -> {res.get('reason')}")

            pipeline.log_equity(current_prices)
            await asyncio.sleep(15)

    except asyncio.CancelledError:
        print(f"🛑 Shutting down [{exchange_id.upper()}] engine...")
    finally:
        await pipeline.close()

async def main():
    print("==========================================================")
    print("   MULTI-EXCHANGE DUAL ENGINE (BINANCE + KRAKEN)          ")
    print("==========================================================\n")
    
    await asyncio.gather(
        run_exchange_loop(EXCHANGE_CONFIGS[0]),
        run_exchange_loop(EXCHANGE_CONFIGS[1])
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Engine stopped gracefully by user.")
