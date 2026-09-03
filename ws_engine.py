import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Any, List, Optional

class AsyncMultiAssetDataEngine:
    def __init__(self, symbols: Optional[List[str]] = None, exchange_id: str = "kraken"):
        self.symbols = symbols or []
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({'enableRateLimit': True})

    async def fetch_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        ticker = await self.exchange.fetch_ticker(symbol)
        orderbook = await self.exchange.fetch_order_book(symbol, limit=20)
        
        bids_usd = sum(bid[0] * bid[1] for bid in orderbook['bids'])
        asks_usd = sum(ask[0] * ask[1] for ask in orderbook['asks'])

        return {
            "symbol": symbol,
            "last_price": ticker['last'],
            "bids_depth_usd": bids_usd,
            "asks_depth_usd": asks_usd
        }

    async def close(self):
        await self.exchange.close()
