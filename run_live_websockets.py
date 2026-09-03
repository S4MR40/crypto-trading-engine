import asyncio
import logging
import sys
from integrated_pipeline_ccxt import CCXTTradingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def monitor_symbol(pipeline: CCXTTradingPipeline, symbol: str, interval_seconds: int = 5):
    """Continuously monitors and evaluates trading signals for a single asset."""
    await pipeline.initialize_buffer(symbol)
    
    logging.info(f"⚡ Live stream active for {symbol}")
    try:
        while True:
            result = await pipeline.run_cycle(symbol)
            if result["status"] == "NO_TRADE":
                logging.debug(f"[{symbol}] Price: ${result['price']:.2f} | Status: Filtered / No Signal")
            
            await asyncio.sleep(interval_seconds)
    except asyncio.CancelledError:
        pass

async def main():
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    pipeline = CCXTTradingPipeline(exchange_id="binance", rsi_period=14, ema_period=200)

    logging.info(f"Starting Multi-Asset Live WebSocket Monitor for {symbols}...")
    
    # Create concurrent background tasks for all target trading pairs
    tasks = [asyncio.create_task(monitor_symbol(pipeline, symbol)) for symbol in symbols]

    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        pass
    finally:
        # Cancel running tasks
        for task in tasks:
            task.cancel()
        
        # Clean up exchange connection
        await pipeline.close()
        logging.info("✅ Exchange session cleanly closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\n🛑 Keyboard interrupt received. Exiting live WebSocket stream...")
