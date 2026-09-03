import asyncio
from integrated_pipeline import IntegratedTradingPipeline

async def main():
    pipeline = IntegratedTradingPipeline(paper_trading=True, max_trade_capital=150.0)
    assets = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    try:
        for symbol in assets:
            print(f"\n--- AI Evaluating Market & Strategy for {symbol} ---")
            res = await pipeline.run_cycle(symbol)
            print(f"Status:            {res.get('status')}")
            if res.get('status') == 'ERROR':
                print(f"Error Details:     {res.get('error')}")
            print(f"Selected Strategy: {res.get('selected_strategy', 'N/A')}")
            if "reasoning" in res:
                print(f"AI Reasoning:      {res['reasoning']}")
                print(f"Position Size:     ${res.get('position_usd')}")
                print(f"Calculated SL:     ${res.get('stop_loss')} | TP: ${res.get('take_profit')}")
    finally:
        await pipeline.close()

if __name__ == "__main__":
    asyncio.run(main())
