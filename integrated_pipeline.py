import asyncio
from typing import Dict, Any, List

class IntegratedTradingPipeline:
    def __init__(self, paper_trading: bool = True, max_trade_capital: float = 20.0):
        self.paper_trading = paper_trading
        self.max_trade_capital = max_trade_capital
        
        # Portfolio exposure tracking (Correlation Cap rule)
        self.active_positions: List[Dict[str, Any]] = []
        self.MAX_CORRELATED_POSITIONS = 2  # Max simultaneous positions in correlated crypto assets
        self.MIN_RR_RATIO = 2.0             # Minimum 2.0 Risk-to-Reward ratio enforced

    async def fetch_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Simulates fetching real live market candles, EMAs, MACD, and orderbook metrics.
        In production, replace dummy values with your exchange API driver (e.g. CCXT / Binance).
        """
        # Base mock prices per asset
        base_prices = {
            "BTC/USDT": 77913.60,
            "ETH/USDT": 2452.28,
            "SOL/USDT": 102.03,
            "ADA/USDT": 0.197162,
            "XRP/USDT": 1.36768
        }
        entry_price = base_prices.get(symbol, 100.0)
        
        # Mocking local EMA trend alignment (20 EMA vs 50 EMA on execution timeframe)
        # Note: ADA/USDT and 4h ETH are set to bearish local EMA to demonstrate strict filtering.
        local_ema_bullish = True
        if symbol == "ADA/USDT" or (symbol == "ETH/USDT" and timeframe == "4h"):
            local_ema_bullish = False

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "entry_price": entry_price,
            "ema_20": entry_price * (1.002 if local_ema_bullish else 0.998),
            "ema_50": entry_price * (0.998 if local_ema_bullish else 1.002),
            "local_ema_bullish": local_ema_bullish,
            "macd_bullish": True,
            "rsi": 52.5,
            "bid_ask_ratio": 1.65 if symbol in ["BTC/USDT", "ETH/USDT", "SOL/USDT"] else 1.10
        }

    def calculate_trade_levels(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates stop loss and take profit based on volatility and target R:R."""
        entry = market_data["entry_price"]
        symbol = market_data["symbol"]

        # Tight stop-loss tailored to timeframe/symbol structure
        sl_pct = 0.015 if "BTC" in symbol else 0.012
        stop_loss = round(entry * (1.0 - sl_pct), 4)

        # Enforce minimum 2.0 R:R spacing
        risk = entry - stop_loss
        
        # Intentionally force low R:R on ADA to demonstrate risk engine filter rejection
        if symbol == "ADA/USDT":
            reward = risk * 1.2  # 1.2 R:R (Will be REJECTED)
        else:
            reward = risk * 2.5  # 2.5 R:R (APPROVED)

        take_profit = round(entry + reward, 4)
        rr_ratio = round(reward / risk, 2) if risk > 0 else 0.0

        return {
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "rr_ratio": rr_ratio
        }

    async def run_cycle(self, symbol: str, timeframe: str = "15m") -> Dict[str, Any]:
        """Runs validation checks across Market Data, Indicators, and Risk Engine."""
        data = await self.fetch_market_data(symbol, timeframe)
        levels = self.calculate_trade_levels(data)

        # --- STRICT AI FILTER 1: LOCAL EMA TREND ALIGNMENT ---
        if not data["local_ema_bullish"]:
            return {
                "status": "REJECTED",
                "reason": f"Local EMA Trend Mismatch ({timeframe} 20 EMA < 50 EMA)"
            }

        # --- STRICT AI FILTER 2: MINIMUM RISK-TO-REWARD RATIO (2.0+) ---
        if levels["rr_ratio"] < self.MIN_RR_RATIO:
            return {
                "status": "REJECTED",
                "reason": f"Insufficient R:R Ratio ({levels['rr_ratio']} < {self.MIN_RR_RATIO} min threshold)"
            }

        # --- STRICT AI FILTER 3: CORRELATION & CAPITAL EXPOSURE CAP ---
        active_btc_eth_count = sum(1 for p in self.active_positions if "BTC" in p["symbol"] or "ETH" in p["symbol"])
        if ("BTC" in symbol or "ETH" in symbol) and active_btc_eth_count >= self.MAX_CORRELATED_POSITIONS:
            return {
                "status": "REJECTED",
                "reason": f"Correlation Cap Exceeded (Max {self.MAX_CORRELATED_POSITIONS} active BTC/ETH positions allowed)"
            }

        # Trade Approved — Register position
        position = {
            "symbol": symbol,
            "timeframe": timeframe,
            "position_usd": self.max_trade_capital,
            "entry": levels["entry"],
            "stop_loss": levels["stop_loss"],
            "take_profit": levels["take_profit"],
            "rr_ratio": levels["rr_ratio"]
        }
        self.active_positions.append(position)

        return {
            "status": "APPROVED_AND_EXECUTED",
            "selected_strategy": "SPOT_SCALP_STRICT",
            "position_usd": self.max_trade_capital,
            "entry": levels["entry"],
            "stop_loss": levels["stop_loss"],
            "take_profit": levels["take_profit"],
            "rr_ratio": levels["rr_ratio"],
            "reasoning": (
                f"Approved: Local {timeframe} EMA aligned (20 > 50), R:R of {levels['rr_ratio']} exceeds minimum 2.0, "
                f"and correlation cap check passed ({len(self.active_positions)} active)."
            )
        }

    async def close(self):
        """Clean up pipeline resources."""
        self.active_positions.clear()
