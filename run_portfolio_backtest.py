import asyncio
import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
LIMIT_15M = 1500
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.015  # Scaled to 1.5% per trade for portfolio management
TAKER_FEE = 0.0005
SLIPPAGE = 0.0002

async def fetch_data(symbol: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    exchange = ccxt.binance({'enableRateLimit': True})
    try:
        ohlcv_1h = await exchange.fetch_ohlcv(symbol, timeframe="1h", limit=500)
        df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms')

        ohlcv_15m = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=LIMIT_15M)
        df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
        return df_1h, df_15m
    finally:
        await exchange.close()

def compute_filtered_indicators(df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> pd.DataFrame:
    df_1h['ema_200_1h'] = ta.ema(df_1h['close'], length=200)
    df_1h_sorted = df_1h[['timestamp', 'ema_200_1h']].sort_values('timestamp')
    df_15m_sorted = df_15m.sort_values('timestamp')

    df = pd.merge_asof(df_15m_sorted, df_1h_sorted, on='timestamp', direction='backward')

    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['vol_ma'] = ta.sma(df['volume'], length=20)
    
    # ADX Volatility Regime Filter
    adx_df = ta.adx(df['high'], df['low'], df['close'], length=14)
    df['adx'] = adx_df.iloc[:, 0]

    # Donchian Channels
    df['donchian_high_20'] = df['high'].shift(1).rolling(20).max()
    df['donchian_low_20'] = df['low'].shift(1).rolling(20).min()

    return df.dropna().reset_index(drop=True)

def run_portfolio_strategy(dfs: dict) -> pd.DataFrame:
    balance = INITIAL_BALANCE
    positions = {sym: None for sym in SYMBOLS}
    portfolio_equity = []
    
    # Align timestamps across all assets
    common_timestamps = dfs[SYMBOLS[0]]['timestamp']
    
    for i in range(1, len(common_timestamps)):
        t_stamp = common_timestamps.iloc[i]
        
        for sym in SYMBOLS:
            df = dfs[sym]
            if i >= len(df):
                continue

            curr = df.iloc[i]
            price = curr['close']
            high = curr['high']
            low = curr['low']
            open_p = curr['open']
            atr = curr['atr']
            adx = curr['adx']

            # 1. Manage Active Positions
            if positions[sym] is not None:
                pos = positions[sym]
                exit_triggered = False
                exit_price = price

                if pos['side'] == "LONG":
                    if high >= pos['tp']:
                        exit_triggered, exit_price = True, pos['tp']
                    elif low <= pos['sl']:
                        exit_triggered, exit_price = True, pos['sl']
                elif pos['side'] == "SHORT":
                    if low <= pos['tp']:
                        exit_triggered, exit_price = True, pos['tp']
                    elif high >= pos['sl']:
                        exit_triggered, exit_price = True, pos['sl']

                if exit_triggered:
                    raw_pnl = (exit_price - pos['entry_price']) * pos['size'] if pos['side'] == "LONG" else (pos['entry_price'] - exit_price) * pos['size']
                    fee_cost = (pos['entry_price'] * pos['size'] * TAKER_FEE) + (exit_price * pos['size'] * TAKER_FEE)
                    slippage_cost = (pos['entry_price'] + exit_price) * pos['size'] * SLIPPAGE
                    net_pnl = raw_pnl - fee_cost - slippage_cost
                    balance += net_pnl
                    positions[sym] = None

            # 2. Check Signals (Filtered by ADX Regime)
            if positions[sym] is None and adx > 22:
                signal_side = None
                sl_mult, tp_mult = 1.5, 3.5

                # Breakout Condition (High Volatility)
                if (price > curr['donchian_high_20']) and (curr['volume'] > curr['vol_ma'] * 1.3):
                    signal_side = "LONG"
                elif (price < curr['donchian_low_20']) and (curr['volume'] > curr['vol_ma'] * 1.3):
                    signal_side = "SHORT"

                if signal_side:
                    sl = price - (atr * sl_mult) if signal_side == "LONG" else price + (atr * sl_mult)
                    tp = price + (atr * tp_mult) if signal_side == "LONG" else price - (atr * tp_mult)
                    risk_amt = balance * RISK_PER_TRADE
                    price_risk = abs(price - sl)
                    size = (risk_amt / price_risk) if price_risk > 0 else 0.0

                    positions[sym] = {
                        "side": signal_side,
                        "entry_price": price,
                        "sl": sl,
                        "tp": tp,
                        "size": size
                    }

        portfolio_equity.append({"timestamp": t_stamp, "Portfolio Balance": round(balance, 2)})

    return pd.DataFrame(portfolio_equity)

async def main():
    dfs = {}
    for sym in SYMBOLS:
        df_1h, df_15m = await fetch_data(sym)
        dfs[sym] = compute_filtered_indicators(df_1h, df_15m)

    portfolio_df = run_portfolio_strategy(dfs)
    final_bal = portfolio_df["Portfolio Balance"].iloc[-1]
    net_pnl = final_bal - INITIAL_BALANCE
    ret = (net_pnl / INITIAL_BALANCE) * 100

    print("=" * 70)
    print("🛡️ ADX-FILTERED BREAKOUT PORTFOLIO RESULTS")
    print("=" * 70)
    print(f"Initial Balance: ${INITIAL_BALANCE:,.2f}")
    print(f"Final Balance:   ${final_bal:,.2f}")
    print(f"Net PnL:         ${net_pnl:,.2f} ({ret:.2f}%)")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
