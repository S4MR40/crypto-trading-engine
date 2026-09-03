import asyncio
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt
from tabulate import tabulate

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
LIMIT_15M = 1500  # Fetch extra 15m candles to ensure historical coverage for 1H EMA 200
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.02

async def fetch_multi_timeframe_data(symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetches both 1h and 15m historical OHLCV data from Binance."""
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        # Fetch 1h candles for Macro Trend (EMA 200)
        ohlcv_1h = await exchange.fetch_ohlcv(symbol, timeframe="1h", limit=500)
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms')

        # Fetch 15m candles for Micro Execution (RSI, MACD, ATR)
        ohlcv_15m = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=LIMIT_15M)
        df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')

        return df_1h, df_15m
    finally:
        await exchange.close()

def compute_indicators(df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> pd.DataFrame:
    """Calculates 1h EMA 200 trend and maps it to 15m candles alongside 15m entry indicators."""
    # 1. Macro Trend on 1h candles
    df_1h['ema_200_1h'] = ta.ema(df_1h['close'], length=200)
    
    # Merge 1h EMA 200 into 15m timeline using merge_asof (backward looking to prevent lookahead bias)
    df_1h_sorted = df_1h[['timestamp', 'ema_200_1h']].sort_values('timestamp')
    df_15m_sorted = df_15m.sort_values('timestamp')
    
    df = pd.merge_asof(
        df_15m_sorted,
        df_1h_sorted,
        on='timestamp',
        direction='backward'
    )
    
    # 2. Micro Technical Indicators on 15m candles
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    df['adx'] = adx_df.iloc[:, 0]
    
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['macd_hist'] = macd.iloc[:, 1]
    
    # Drop warm-up NaN rows
    df = df.dropna().reset_index(drop=True)
    return df

def run_backtest(df: pd.DataFrame, rsi_l: float, rsi_h: float, sl_m: float, tp_m: float, min_adx: float = 20, be_trigger_mult: float = 1.0, trail_mult: float = 1.0) -> dict:
    balance = INITIAL_BALANCE
    position = None
    trades = []

    for i in range(1, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i - 1]

        price = curr['close']
        high = curr['high']
        low = curr['low']
        open_p = curr['open']
        
        # Multi-Timeframe Signals
        ema_200_1h = curr['ema_200_1h']
        rsi = curr['rsi']
        atr = curr['atr']
        adx = curr['adx']
        macd_curr = curr['macd_hist']
        macd_prev = prev['macd_hist']

        # 1. Active Position Management & Trailing SL Logic
        if position is not None:
            side = position['side']
            sl = position['sl']
            tp = position['tp']
            entry = position['entry_price']
            size = position['size']
            entry_atr = position['entry_atr']
            be_activated = position['be_activated']

            # Dynamic Break-Even & Trailing Stop Updates
            if side == "LONG":
                unrealized_profit = high - entry
                # Move SL to Entry (Break-Even) after +1.0x ATR unrealized profit
                if not be_activated and (unrealized_profit >= entry_atr * be_trigger_mult):
                    sl = max(sl, entry)
                    position['be_activated'] = True
                    position['sl'] = sl
                
                # Trailing Stop: Trail stop loss behind peak high price by trailing ATR distance
                if position['be_activated']:
                    new_sl = high - (atr * trail_mult)
                    if new_sl > position['sl']:
                        position['sl'] = new_sl
                        sl = new_sl

            elif side == "SHORT":
                unrealized_profit = entry - low
                # Move SL to Entry (Break-Even) after +1.0x ATR unrealized profit
                if not be_activated and (unrealized_profit >= entry_atr * be_trigger_mult):
                    sl = min(sl, entry)
                    position['be_activated'] = True
                    position['sl'] = sl

                # Trailing Stop: Trail stop loss above valley low price by trailing ATR distance
                if position['be_activated']:
                    new_sl = low + (atr * trail_mult)
                    if new_sl < position['sl']:
                        position['sl'] = new_sl
                        sl = new_sl

            # Evaluate Trade Exits
            exit_triggered = False
            exit_price = price

            if side == "LONG":
                if open_p >= entry:
                    if high >= tp:
                        exit_triggered, exit_price = True, tp
                    elif low <= sl:
                        exit_triggered, exit_price = True, sl
                else:
                    if low <= sl:
                        exit_triggered, exit_price = True, sl
                    elif high >= tp:
                        exit_triggered, exit_price = True, tp

            elif side == "SHORT":
                if open_p <= entry:
                    if low <= tp:
                        exit_triggered, exit_price = True, tp
                    elif high >= sl:
                        exit_triggered, exit_price = True, sl
                else:
                    if high >= sl:
                        exit_triggered, exit_price = True, sl
                    elif low <= tp:
                        exit_triggered, exit_price = True, tp

            if exit_triggered:
                pnl = (exit_price - entry) * size if side == "LONG" else (entry - exit_price) * size
                balance += pnl
                trades.append(pnl)
                position = None

        # 2. MTF Entry Rules
        if position is None and adx >= min_adx:
            # LONG Signal
            if (price > ema_200_1h) and (rsi <= rsi_l) and (macd_curr > macd_prev):
                sl = price - (atr * sl_m)
                tp = price + (atr * tp_m)
                risk_amt = balance * RISK_PER_TRADE
                price_risk = abs(price - sl)
                size = (risk_amt / price_risk) if price_risk > 0 else 0.0
                position = {
                    "side": "LONG",
                    "entry_price": price,
                    "sl": sl,
                    "tp": tp,
                    "size": size,
                    "entry_atr": atr,
                    "be_activated": False
                }

            # SHORT Signal
            elif (price < ema_200_1h) and (rsi >= rsi_h) and (macd_curr < macd_prev):
                sl = price + (atr * sl_m)
                tp = price - (atr * tp_m)
                risk_amt = balance * RISK_PER_TRADE
                price_risk = abs(price - sl)
                size = (risk_amt / price_risk) if price_risk > 0 else 0.0
                position = {
                    "side": "SHORT",
                    "entry_price": price,
                    "sl": sl,
                    "tp": tp,
                    "size": size,
                    "entry_atr": atr,
                    "be_activated": False
                }

    total_trades = len(trades)
    wins = [t for t in trades if t > 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
    net_pnl = balance - INITIAL_BALANCE

    return {"trades": total_trades, "win_rate": win_rate, "net_pnl": net_pnl, "balance": balance}

async def main():
    print("📊 Running MTF Backtest with Break-Even & Dynamic Trailing Stop Loss...\n")
    
    dfs = {}
    for sym in SYMBOLS:
        df_1h, df_15m = await fetch_multi_timeframe_data(sym)
        dfs[sym] = compute_indicators(df_1h, df_15m)

    configs = [
        {"name": "Fixed Stop (No BE / Trail)", "rsi_l": 40, "rsi_h": 60, "sl": 1.5, "tp": 2.5, "adx": 20, "be": 999.0, "trail": 999.0},
        {"name": "Break-Even @ +1.0x ATR", "rsi_l": 40, "rsi_h": 60, "sl": 1.5, "tp": 2.5, "adx": 20, "be": 1.0, "trail": 999.0},
        {"name": "Break-Even @ +1.0x ATR + Trailing SL (1.5x ATR)", "rsi_l": 40, "rsi_h": 60, "sl": 1.5, "tp": 3.0, "adx": 20, "be": 1.0, "trail": 1.5},
        {"name": "Aggressive Trail (1.0x ATR)", "rsi_l": 42, "rsi_h": 58, "sl": 1.8, "tp": 3.0, "adx": 22, "be": 1.0, "trail": 1.0},
    ]

    for cfg in configs:
        print(f"🔍 Testing: {cfg['name']} (BE: {cfg['be']}x ATR | Trail: {cfg['trail']}x ATR)")
        table_data = []

        for sym in SYMBOLS:
            res = run_backtest(
                dfs[sym],
                cfg['rsi_l'],
                cfg['rsi_h'],
                cfg['sl'],
                cfg['tp'],
                cfg['adx'],
                be_trigger_mult=cfg['be'],
                trail_mult=cfg['trail']
            )
            table_data.append([
                sym,
                res['trades'],
                f"{res['win_rate']:.1f}%",
                f"${res['net_pnl']:+.2f}",
                f"${res['balance']:.2f}"
            ])

        print(tabulate(table_data, headers=["Symbol", "Trades", "Win Rate", "Net PnL", "End Balance"], tablefmt="grid"))
        print("\n")

if __name__ == "__main__":
    asyncio.run(main())
