import asyncio
import logging
import sys
import os
from typing import Dict, Optional
import pandas as pd
import pandas_ta as ta
import ccxt.pro as ccxtpro
import aiohttp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)


class TelegramNotifier:
    """Handles asynchronous notifications to a Telegram chat."""
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        # Fetch from parameters or fallback to environment variables
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.enabled = bool(self.bot_token and self.chat_id)

        if self.enabled:
            logging.info("📱 Telegram notifications initialized and active.")
        else:
            logging.info("ℹ️ Telegram credentials not found. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to enable alerts.")

    async def send_message(self, text: str):
        """Asynchronously sends a formatted text message to Telegram."""
        if not self.enabled:
            return

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=5) as resp:
                    if resp.status != 200:
                        logging.error(f"Failed to send Telegram alert: HTTP {resp.status}")
        except Exception as e:
            logging.error(f"Error sending Telegram notification: {e}")


class PositionManager:
    """Tracks active positions, manages SL/TP triggers, and logs realized PnL."""
    def __init__(self, initial_balance: float = 10000.0, risk_per_trade: float = 0.02, notifier: Optional[TelegramNotifier] = None):
        self.balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.positions: Dict[str, dict] = {}
        self.trade_history = []
        self.notifier = notifier or TelegramNotifier()

    async def open_position(self, symbol: str, side: str, entry_price: float, sl: float, tp: float, reason: str):
        """Calculates position sizing, registers active position, and sends Telegram alert."""
        if symbol in self.positions:
            return

        risk_amount = self.balance * self.risk_per_trade
        price_risk = abs(entry_price - sl)
        size = (risk_amount / price_risk) if price_risk > 0 else 0.0

        position = {
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "size": size,
            "sl": sl,
            "tp": tp,
            "reason": reason
        }

        self.positions[symbol] = position
        logging.info(
            f"📈 [POSITION OPENED] {symbol} | Side: {side} | Entry: ${entry_price:.2f} | "
            f"SL: ${sl:.2f} | TP: ${tp:.2f} | Size: {size:.4f} units"
        )

        # Telegram Alert
        msg = (
            f"🚀 *POSITION OPENED*\n"
            f"• *Symbol:* `{symbol}`\n"
            f"• *Side:* `{side}`\n"
            f"• *Entry:* `${entry_price:.2f}`\n"
            f"• *Size:* `{size:.4f}` units\n"
            f"• *Take Profit:* `${tp:.2f}`\n"
            f"• *Stop Loss:* `${sl:.2f}`\n"
            f"• *Reason:* {reason}"
        )
        await self.notifier.send_message(msg)

    async def check_and_update(self, symbol: str, current_price: float) -> Optional[dict]:
        """Monitors price against SL/TP thresholds, closes position, and sends Telegram alert on exit."""
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]
        side = pos["side"]
        entry = pos["entry_price"]
        size = pos["size"]
        sl = pos["sl"]
        tp = pos["tp"]

        exit_triggered = False
        exit_reason = ""
        exit_price = current_price

        # Evaluate Stop-Loss and Take-Profit conditions
        if side == "LONG":
            if current_price <= sl:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
                exit_price = sl
            elif current_price >= tp:
                exit_triggered = True
                exit_reason = "TAKE_PROFIT"
                exit_price = tp
        elif side == "SHORT":
            if current_price >= sl:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
                exit_price = sl
            elif current_price <= tp:
                exit_triggered = True
                exit_reason = "TAKE_PROFIT"
                exit_price = tp

        if exit_triggered:
            if side == "LONG":
                pnl = (exit_price - entry) * size
            else:
                pnl = (entry - exit_price) * size

            self.balance += pnl
            pnl_pct = (pnl / (entry * size)) * 100 if size > 0 else 0.0

            trade_record = {
                "symbol": symbol,
                "side": side,
                "entry": entry,
                "exit": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "reason": exit_reason
            }

            self.trade_history.append(trade_record)
            del self.positions[symbol]

            log_symbol = "✅" if pnl > 0 else "❌"
            logging.info(
                f"{log_symbol} [POSITION CLOSED] {symbol} | Trigger: {exit_reason} | "
                f"Exit: ${exit_price:.2f} | PnL: ${pnl:+.2f} ({pnl_pct:+.2f}%) | "
                f"New Balance: ${self.balance:.2f}"
            )

            # Telegram Alert
            status_emoji = "🎯 PROFIT" if pnl > 0 else "🛑 LOSS"
            msg = (
                f"{log_symbol} *POSITION CLOSED ({status_emoji})*\n"
                f"• *Symbol:* `{symbol}`\n"
                f"• *Trigger:* `{exit_reason}`\n"
                f"• *Entry:* `${entry:.2f}`\n"
                f"• *Exit:* `${exit_price:.2f}`\n"
                f"• *Realized PnL:* `${pnl:+.2f}` (`{pnl_pct:+.2f}%`)\n"
                f"• *Account Balance:* `${self.balance:.2f}`"
            )
            await self.notifier.send_message(msg)

            return trade_record

        return None


class CCXTTradingPipeline:
    def __init__(self, exchange_id: str = "binance", rsi_period: int = 14, ema_period: int = 200, telegram_token: Optional[str] = None, telegram_chat_id: Optional[str] = None):
        self.exchange_id = exchange_id
        self.rsi_period = rsi_period
        self.ema_period = ema_period
        
        exchange_class = getattr(ccxtpro, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        self.data_buffers = {}
        self.notifier = TelegramNotifier(bot_token=telegram_token, chat_id=telegram_chat_id)
        self.position_manager = PositionManager(initial_balance=10000.0, risk_per_trade=0.02, notifier=self.notifier)

    async def initialize_buffer(self, symbol: str, timeframe: str = "15m"):
        """Fetches historical OHLCV data to initialize indicators."""
        logging.info(f"📥 [{self.exchange_id.upper()}] Initializing buffer for {symbol}...")
        limit = self.ema_period * 2
        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        self.data_buffers[symbol] = df
        
        self._calculate_indicators(symbol)
        logging.info(f"✅ [{self.exchange_id.upper()}] {symbol} Buffer Ready | EMA 200: {df['ema_200'].iloc[-1]:.2f}")

    def _calculate_indicators(self, symbol: str):
        """Calculates EMA 200, RSI, MACD, and ATR indicators."""
        df = self.data_buffers[symbol]
        df['ema_200'] = ta.ema(df['close'], length=self.ema_period)
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['macd_hist'] = macd.iloc[:, 1]

    def update_latest_tick(self, symbol: str, current_price: float):
        """Updates the latest candle price and recalculates technical indicators."""
        df = self.data_buffers[symbol]
        df.iloc[-1, df.columns.get_loc('close')] = current_price
        self._calculate_indicators(symbol)

    def evaluate_signal(self, symbol: str) -> dict:
        """Evaluates entry signals (EMA 200 Trend + RSI Threshold + MACD Reversal)."""
        df = self.data_buffers[symbol]
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        price = curr['close']
        ema_200 = curr['ema_200']
        rsi = curr['rsi']
        atr = curr['atr']
        macd_hist_curr = curr['macd_hist']
        macd_hist_prev = prev['macd_hist']

        # Long Evaluation
        if (price > ema_200) and (rsi <= 32.0) and (macd_hist_curr > macd_hist_prev):
            return {
                "signal": "LONG",
                "price": price,
                "sl": price - (atr * 1.5),
                "tp": price + (atr * 3.0),
                "reason": f"Uptrend (>EMA200 {ema_200:.2f}) + RSI Oversold ({rsi:.1f}) + MACD Upward Turn"
            }

        # Short Evaluation
        if (price < ema_200) and (rsi >= 68.0) and (macd_hist_curr < macd_hist_prev):
            return {
                "signal": "SHORT",
                "price": price,
                "sl": price + (atr * 1.5),
                "tp": price - (atr * 3.0),
                "reason": f"Downtrend (<EMA200 {ema_200:.2f}) + RSI Overbought ({rsi:.1f}) + MACD Downward Turn"
            }

        return {"signal": "NONE", "price": price}

    async def run_cycle(self, symbol: str) -> dict:
        """Runs on each ticker update: manages open positions and evaluates new entry signals."""
        ticker = await self.exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        self.update_latest_tick(symbol, current_price)
        
        # 1. Update existing positions and check SL/TP triggers
        exit_event = await self.position_manager.check_and_update(symbol, current_price)
        if exit_event:
            return {"status": "POSITION_CLOSED", "details": exit_event}

        # 2. Evaluate new entries if no active position exists for the symbol
        if symbol not in self.position_manager.positions:
            signal_data = self.evaluate_signal(symbol)
            if signal_data["signal"] != "NONE":
                await self.position_manager.open_position(
                    symbol=symbol,
                    side=signal_data["signal"],
                    entry_price=signal_data["price"],
                    sl=signal_data["sl"],
                    tp=signal_data["tp"],
                    reason=signal_data["reason"]
                )
                return {"status": "POSITION_OPENED", "details": signal_data}

        return {"status": "NO_CHANGE", "price": current_price}

    async def close(self):
        """Cleanly closes WebSocket connections."""
        await self.exchange.close()

if __name__ == "__main__":
    async def main():
        symbol = "BTC/USDT"
        pipeline = CCXTTradingPipeline(exchange_id="binance")
        await pipeline.initialize_buffer(symbol)
        
        logging.info(f"⚡ Testing position tracking & notification lifecycle for {symbol}...")
        try:
            for _ in range(3):
                await pipeline.run_cycle(symbol)
                await asyncio.sleep(2)
        finally:
            await pipeline.close()
            logging.info("✅ Exchange session cleanly closed.")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
