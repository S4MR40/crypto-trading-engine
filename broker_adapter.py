import asyncio, os
from typing import Dict, Any, Optional
import ccxt.async_support as ccxt

class BrokerAdapter:
    def __init__(self, exchange_id: str = "kraken", paper_trading: bool = True, api_key: Optional[str] = None, secret: Optional[str] = None):
        self.exchange_id = exchange_id
        self.paper_trading = paper_trading
        exchange_class = getattr(ccxt, exchange_id, None)
        self.exchange = exchange_class({"enableRateLimit": True})

    async def execute_trade(self, signal: Dict[str, Any], position_size_usd: float = 1000.0) -> Dict[str, Any]:
        symbol = signal["symbol"]
        direction = signal["direction"]
        entry_price = signal["entry_price"]
        quantity = position_size_usd / entry_price
        side = "buy" if direction == "LONG" else "sell"

        if self.paper_trading:
            return {
                "status": "EXECUTED_PAPER",
                "exchange": self.exchange_id,
                "symbol": symbol,
                "side": side,
                "amount": round(quantity, 6),
                "entry_price": entry_price,
                "paper_order_id": f"paper_{symbol.replace("/", "_")}_1001"
            }
        return {"status": "LIVE_DISABLED"}

    async def close(self):
        await self.exchange.close()
