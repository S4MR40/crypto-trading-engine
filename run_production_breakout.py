import asyncio
import numpy as np
import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt

SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
LIMIT_15M = 1500
INITIAL_BALANCE = 10000.0
RISK_PER_TRADE = 0.015
TAKER_FEE = 0.0005
SLIPPAGE = 0.0002
MAX_OPEN_POSITIONS = 1

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

def compute_production_indicators(df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> pd.DataFrame:
    # 1H Macro Trend & Momentum
    df_1h['ema_200'] = ta.ema(df_1h['close'], length=200)
    macd_1h = ta.macd(df_1h['close'], fast=12, slow=26, signal=9)
    df_1h['macd_hist'] = macd_1h.iloc[:, 2]
    
    df_1h_sorted = df_1h[['timestamp', 'ema_200', 'macd_hist']].sort_values('timestamp')
    df_15m_sorted = df_15m.sort_values('timestamp')

    df = pd.merge_asof(df_15m_sorted, df_1h_sorted, on='timestamp', direction='backward')

    # 15M Indicators
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['vol_ma'] = ta.sma(df['volume'], length=20)
    df['donchian_high'] = df['high'].shift(1).rolling(20).max()
    df['donchian_low'] = df['low'].shift(1).rolling(20).min()

    return df.dropna().reset_index(drop=True)

def run_production_portfolio(dfs: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    balance = INITIAL_BALANCE
    positions = {}
    trades = []
    portfolio_equity = []

    common_timestamps = dfs[SYMBOLS[0]]['timestamp']

    for i in range(1, len(common_timestamps)):
        t_stamp = common_timestamps.iloc[i]

        # 1. Active Position Management (Trailing Chandelier Exit)
        active_syms = list(positions.keys())
        for sym in active_syms:
            pos = positions[sym]
            df = dfs[sym]
            if i >= len(df):
                continue
            curr = df.iloc[i]
            price = curr['close']
            high = curr['high']
            low = curr['low']
            atr = curr['atr']

            exit_triggered = False
            exit_price = price

            if pos['side'] == "LONG":
                # Dynamic Trailing Stop (Chandelier style based on highest high reached)
                if high > pos['highest_price']:
                    pos['highest_price'] = high
                    new_sl = high - (2.5 * atr)
                    if new_sl > pos['sl']:
                        pos['sl'] = new_sl

                if low <= pos['sl']:
                    exit_triggered, exit_price = True, pos['sl']

            elif pos['side'] == "SHORT":
                if low < pos['lowest_price']:
                    pos['lowest_price'] = low
                    new_sl = low + (2.5 * atr)
                    if new_sl < pos['sl']:
                        pos['sl'] = new_sl

                if high >= pos['sl']:
                    exit_triggered, exit_price = True, pos['sl']

            if exit_triggered:
                raw_pnl = (exit_price - pos['entry_price']) * pos['size'] if pos['side'] == "LONG" else (pos['entry_price'] - exit_price) * pos['size']
                fee_cost = (pos['entry_price'] * pos['size'] * TAKER_FEE) + (exit_price * pos['size'] * TAKER_FEE)
                slippage_cost = (pos['entry_price'] + exit_price) * pos['size'] * SLIPPAGE
                net_pnl = raw_pnl - fee_cost - slippage_cost

                balance += net_pnl
                trades.append({
                    "Symbol": sym,
                    "Side": pos['side'],
                    "Entry Time": pos['entry_time'],
                    "Exit Time": t_stamp,
                    "Net PnL ($)": round(net_pnl, 2),
                    "Return (%)": round((net_pnl / (pos['entry_price'] * pos['size'])) * 100, 2)
                })
                del positions[sym]

        # 2. Entry Rules (1H Macro Trend + 15M Donchian Breakout + Volume)
        if len(positions) < MAX_OPEN_POSITIONS:
            for sym in SYMBOLS:
                if sym in positions:
                    continue
                df = dfs[sym]
                if i >= len(df):
                    continue
                curr = df.iloc[i]
                price = curr['close']
                atr = curr['atr']
                
                macro_trend_up = (price > curr['ema_200']) and (curr['macd_hist'] > 0)
                macro_trend_down = (price < curr['ema_200']) and (curr['macd_hist'] < 0)

                signal_side = None
                if curr['volume'] > curr['vol_ma'] * 1.5:
                    if (price > curr['donchian_high']) and macro_trend_up:
                        signal_side = "LONG"
                    elif (price < curr['donchian_low']) and macro_trend_down:
                        signal_side = "SHORT"

                if signal_side:
                    sl = price - (atr * 2.0) if signal_side == "LONG" else price + (atr * 2.0)
                    risk_amt = balance * RISK_PER_TRADE
                    price_risk = abs(price - sl)
                    size = (risk_amt / price_risk) if price_risk > 0 else 0.0

                    positions[sym] = {
                        "side": signal_side,
                        "entry_price": price,
                        "entry_time": t_stamp,
                        "sl": sl,
                        "size": size,
                        "highest_price": price,
                        "lowest_price": price
                    }
                    break

        portfolio_equity.append({"timestamp": t_stamp, "Portfolio Balance": round(balance, 2)})

    return pd.DataFrame(portfolio_equity), pd.DataFrame(trades)

async def main():
    print("🚀 Running Production Multi-Timeframe Trend Breakout Strategy...\n")
    dfs = {}
    for sym in SYMBOLS:
        df_1h, df_15m = await fetch_data(sym)
        dfs[sym] = compute_production_indicators(df_1h, df_15m)

    eq_df, trades_df = run_production_portfolio(dfs)
    final_bal = eq_df["Portfolio Balance"].iloc[-1]
    net_pnl = final_bal - INITIAL_BALANCE
    ret = (net_pnl / INITIAL_BALANCE) * 100

    print("=" * 80)
    print("📊 PRODUCTION STRATEGY PERFORMANCE RESULTS")
    print("=" * 80)
    print(f"Initial Balance:    ${INITIAL_BALANCE:,.2f}")
    print(f"Final Balance:      ${final_bal:,.2f}")
    print(f"Net PnL:            ${net_pnl:,.2f} ({ret:.2f}%)")
    print(f"Total Trades:       {len(trades_df)}")
    if not trades_df.empty:
        win_rate = (len(trades_df[trades_df["Net PnL ($)"] > 0]) / len(trades_df)) * 100
        print(f"Win Rate:           {win_rate:.2f}%")
        print("\n📜 RECENT EXECUTED TRADES:")
        print(trades_df.tail(8).to_string(index=False))
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
