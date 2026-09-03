import os
import asyncio
import ccxt.async_support as ccxt
from typing import Dict, Any

class BrokerAdapter:
    def __init__(self, exchange_id: str = "kraken", paper_trading: bool = True):
        self.exchange_id = exchange_id
        self.paper_trading = paper_trading
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            "apiKey": os.getenv("EXCHANGE_API_KEY", ""),
            "secret": os.getenv("EXCHANGE_SECRET", ""),
            "enableRateLimit": True
        })

    async def execute_trade(self, symbol: str, direction: str, amount_usd: float = 100.0) -> Dict[str, Any]:
        side = "buy" if direction == "LONG" else "sell"
        
        print(f"\n[SIGNAL GENERATED] {direction} {symbol} | Amount: ${amount_usd:.2f}")

        if self.paper_trading:
            return {
                "status": "EXECUTED_PAPER",
                "order_id": f"paper_{symbol.replace('/', '_')}_1001",
                "symbol": symbol,
                "side": side,
                "amount_usd": amount_usd,
                "mode": "PAPER"
            }

        try:
            ticker = await self.exchange.fetch_ticker(symbol)
            quantity = amount_usd / ticker['last']
            order = await self.exchange.create_order(symbol, 'market', side, quantity)
            return {"status": "EXECUTED_LIVE", "order_id": order['id'], "details": order}
        except Exception as e:
            return {"status": "EXECUTION_FAILED", "error": str(e)}

    async def close(self):
        await self.exchange.close()
