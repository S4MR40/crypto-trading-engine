import asyncio
from typing import Dict, Any, List

class IntegratedTradingPipelineV3:
    def __init__(self, paper_trading: bool = True, max_trade_capital: float = 20.0):
        self.paper_trading = paper_trading
        self.max_trade_capital = max_trade_capital
        self.active_positions: List[Dict[str, Any]] = []
        self.MAX_CORRELATED_POSITIONS = 2
        self.MIN_RR_RATIO = 2.0
        
        # ATR Multipliers
        self.ATR_SL_MULT = 1.5
        self.ATR_TP_MULT = 3.75

    async def fetch_market_data(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """Fetches candle data, ATR(14), EMAs, MACD, and RSI levels."""
        base_prices = {
            "BTC/USDT": 77913.60,
            "ETH/USDT": 2452.28,
            "SOL/USDT": 102.03,
            "ADA/USDT": 0.197162,
            "XRP/USDT": 1.36768
        }
        entry = base_prices.get(symbol, 100.0)

        # Volatility ATR simulation (1.2% - 2.5% of price depending on asset)
        atr_pct = 0.012 if "BTC" in symbol else (0.018 if "ETH" in symbol else 0.025)
        atr = round(entry * atr_pct, 4)

        is_bearish = (symbol == "ADA/USDT") or (symbol == "ETH/USDT" and timeframe in ["1h", "4h"])
        is_oversold = (symbol == "SOL/USDT" and timeframe == "1h")

        rsi = 28.0 if is_oversold else (68.0 if is_bearish else 52.5)
        ema_20 = entry * (0.995 if is_bearish else 1.005)
        ema_50 = entry * (1.005 if is_bearish else 0.995)
        macd_signal = "BEARISH_CROSS" if is_bearish else "BULLISH_CROSS"

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "entry_price": entry,
            "atr": atr,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "rsi": rsi,
            "macd_signal": macd_signal,
        }

    def evaluate_strategies(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluates setups and calculates ATR-based dynamic risk levels."""
        entry = data["entry_price"]
        atr = data["atr"]
        ema_20 = data["ema_20"]
        ema_50 = data["ema_50"]
        rsi = data["rsi"]
        macd = data["macd_signal"]

        sl_dist = atr * self.ATR_SL_MULT
        tp_dist = atr * self.ATR_TP_MULT

        # Strategy 1: RSI Mean-Reversion (Oversold Long / Overbought Short)
        if rsi <= 30.0:
            sl = round(entry - sl_dist, 4)
            tp = round(entry + tp_dist, 4)
            rr = round((tp - entry) / (entry - sl), 2)
            return {
                "signal": "LONG", "strategy": "MEAN_REVERSION_LONG",
                "entry": entry, "sl": sl, "tp": tp, "rr": rr, "atr": atr,
                "reason": f"RSI Oversold ({rsi} <= 30). Expecting bounce to mean."
            }
        elif rsi >= 70.0:
            sl = round(entry + sl_dist, 4)
            tp = round(entry - tp_dist, 4)
            rr = round((entry - tp) / (sl - entry), 2)
            return {
                "signal": "SHORT", "strategy": "MEAN_REVERSION_SHORT",
                "entry": entry, "sl": sl, "tp": tp, "rr": rr, "atr": atr,
                "reason": f"RSI Overbought ({rsi} >= 70). Expecting pullback to mean."
            }

        # Strategy 2: Trend Following Long
        if ema_20 > ema_50 and macd == "BULLISH_CROSS":
            sl = round(entry - sl_dist, 4)
            tp = round(entry + tp_dist, 4)
            rr = round((tp - entry) / (entry - sl), 2)
            return {
                "signal": "LONG", "strategy": "TREND_SCALP_LONG",
                "entry": entry, "sl": sl, "tp": tp, "rr": rr, "atr": atr,
                "reason": f"Bullish EMA Alignment (20 > 50) + Bullish MACD Cross. ATR: ${atr}"
            }

        # Strategy 3: Trend Following Short
        if ema_20 < ema_50 and macd == "BEARISH_CROSS":
            sl = round(entry + sl_dist, 4)
            tp = round(entry - tp_dist, 4)
            rr = round((entry - tp) / (sl - entry), 2)
            return {
                "signal": "SHORT", "strategy": "TREND_SCALP_SHORT",
                "entry": entry, "sl": sl, "tp": tp, "rr": rr, "atr": atr,
                "reason": f"Bearish EMA Alignment (20 < 50) + Bearish MACD Cross. ATR: ${atr}"
            }

        return {"signal": "NONE", "reason": "No valid strategy setup identified."}

    def update_trailing_stops(self, current_prices: Dict[str, float]) -> List[str]:
        """
        Evaluates active positions against live mark prices to trail stop-loss.
        - Moves SL to Break-Even at +1.5x ATR.
        - Trails SL dynamically behind price at 1.5x ATR distance when profit > +2.0x ATR.
        """
        updates = []
        for pos in self.active_positions:
            symbol = pos["symbol"]
            if symbol not in current_prices:
                continue

            current_price = current_prices[symbol]
            direction = pos["direction"]
            entry = pos["entry"]
            atr = pos["atr"]
            current_sl = pos["stop_loss"]

            if direction == "LONG":
                profit = current_price - entry
                # Break-Even adjustment
                if profit >= (1.5 * atr) and current_sl < entry:
                    pos["stop_loss"] = entry
                    updates.append(f"[{symbol} LONG] Break-Even Triggered -> SL moved to Entry (${entry})")
                # Trailing Stop adjustment
                elif profit >= (2.0 * atr):
                    new_sl = round(current_price - (1.5 * atr), 4)
                    if new_sl > pos["stop_loss"]:
                        pos["stop_loss"] = new_sl
                        updates.append(f"[{symbol} LONG] Trailing SL Updated -> New SL: ${new_sl} (Price: ${current_price})")

            elif direction == "SHORT":
                profit = entry - current_price
                # Break-Even adjustment
                if profit >= (1.5 * atr) and current_sl > entry:
                    pos["stop_loss"] = entry
                    updates.append(f"[{symbol} SHORT] Break-Even Triggered -> SL moved to Entry (${entry})")
                # Trailing Stop adjustment
                elif profit >= (2.0 * atr):
                    new_sl = round(current_price + (1.5 * atr), 4)
                    if new_sl < pos["stop_loss"]:
                        pos["stop_loss"] = new_sl
                        updates.append(f"[{symbol} SHORT] Trailing SL Updated -> New SL: ${new_sl} (Price: ${current_price})")

        return updates

    async def run_cycle(self, symbol: str, timeframe: str = "15m") -> Dict[str, Any]:
        data = await self.fetch_market_data(symbol, timeframe)
        setup = self.evaluate_strategies(data)

        if setup["signal"] == "NONE":
            return {"status": "REJECTED", "reason": setup["reason"]}

        if setup["rr"] < self.MIN_RR_RATIO:
            return {
                "status": "REJECTED",
                "reason": f"R:R ({setup['rr']}) below required {self.MIN_RR_RATIO} threshold."
            }

        active_btc_eth = sum(1 for p in self.active_positions if "BTC" in p["symbol"] or "ETH" in p["symbol"])
        if ("BTC" in symbol or "ETH" in symbol) and active_btc_eth >= self.MAX_CORRELATED_POSITIONS:
            return {
                "status": "REJECTED",
                "reason": f"Correlation Cap Exceeded (Max {self.MAX_CORRELATED_POSITIONS} active BTC/ETH positions allowed)."
            }

        position = {
            "symbol": symbol, "timeframe": timeframe, "direction": setup["signal"],
            "strategy": setup["strategy"], "position_usd": self.max_trade_capital,
            "entry": setup["entry"], "stop_loss": setup["sl"], "take_profit": setup["tp"],
            "rr_ratio": setup["rr"], "atr": setup["atr"]
        }
        self.active_positions.append(position)

        return {
            "status": "APPROVED_AND_EXECUTED",
            "direction": setup["signal"],
            "selected_strategy": setup["strategy"],
            "position_usd": self.max_trade_capital,
            "entry": setup["entry"],
            "stop_loss": setup["sl"],
            "take_profit": setup["tp"],
            "rr_ratio": setup["rr"],
            "atr": setup["atr"],
            "reasoning": setup["reason"]
        }

    async def close(self):
        self.active_positions.clear()
