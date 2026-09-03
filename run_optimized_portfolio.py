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
MAX_OPEN_POSITIONS = 1  # Limits portfolio correlation risk

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

def compute_enhanced_indicators(df_1h: pd.DataFrame, df_15m: pd.DataFrame) -> pd.DataFrame:
    df_1h['ema_200_1h'] = ta.ema(df_1h['close'], length=200)
    df_1h_sorted = df_1h[['timestamp', 'ema_200_1h']].sort_values('timestamp')
    df_15m_sorted = df_15m.sort_values('timestamp')

    df = pd.merge_asof(df_15m_sorted, df_1h_sorted, on='timestamp', direction='backward')

    df['ema_50'] = ta.ema(df['close'], length=50)
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    df['vol_ma'] = ta.sma(df['volume'], length=20)
    
    # Donchian Breakout Levels
    df['donchian_high_20'] = df['high'].shift(1).rolling(20).max()
    df['donchian_low_20'] = df['low'].shift(1).rolling(20).min()

    # Volatility Squeeze Metric (BB Width vs ATR)
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_width'] = (bb.iloc[:, 2] - bb.iloc[:, 0]) / df['close']
    df['squeeze_low_vol'] = df['bb_width'] < df['bb_width'].rolling(50).quantile(0.35)

    return df.dropna().reset_index(drop=True)

def run_optimized_portfolio(dfs: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    balance = INITIAL_BALANCE
    positions = {}
    trades = []
    portfolio_equity = []
    
    common_timestamps = dfs[SYMBOLS[0]]['timestamp']

    for i in range(1, len(common_timestamps)):
        t_stamp = common_timestamps.iloc[i]
        
        # 1. Manage Active Positions & Trailing Stops
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

            # Profit Locking / Dynamic Trailing
            if pos['side'] == "LONG":
                # Trailing stop adjustments
                if high >= pos['entry_price'] + (1.5 * pos['initial_atr']) and not pos['be_active']:
                    pos['sl'] = pos['entry_price'] * (1 + (TAKER_FEE * 2 + SLIPPAGE * 2))  # Cover fees
                    pos['be_active'] = True
                
                if high >= pos['tp']:
                    exit_triggered, exit_price = True, pos['tp']
                elif low <= pos['sl']:
                    exit_triggered, exit_price = True, pos['sl']

            elif pos['side'] == "SHORT":
                if low <= pos['entry_price'] - (1.5 * pos['initial_atr']) and not pos['be_active']:
                    pos['sl'] = pos['entry_price'] * (1 - (TAKER_FEE * 2 + SLIPPAGE * 2))
                    pos['be_active'] = True

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
                trades.append({
                    "Symbol": sym,
                    "Side": pos['side'],
                    "Entry Time": pos['entry_time'],
                    "Exit Time": t_stamp,
                    "Net PnL ($)": round(net_pnl, 2),
                    "Return (%)": round((net_pnl / (pos['entry_price'] * pos['size'])) * 100, 2)
                })
                del positions[sym]

        # 2. Open New Positions (Strict HTF Trend & Correlation Cap)
        if len(positions) < MAX_OPEN_POSITIONS:
            for sym in SYMBOLS:
                if sym in positions:
                    continue
                df = dfs[sym]
                if i >= len(df):
                    continue
                curr = df.iloc[i]
                prev = df.iloc[i-1]
                price = curr['close']
                atr = curr['atr']
                macro_ema = curr['ema_200_1h']

                signal_side = None

                # Breakout out of low-volatility compression (Squeeze) aligned with 1H Trend
                if prev['squeeze_low_vol'] and (curr['volume'] > curr['vol_ma'] * 1.4):
                    if (price > curr['donchian_high_20']) and (price > macro_ema):
                        signal_side = "LONG"
                    elif (price < curr['donchian_low_20']) and (price < macro_ema):
                        signal_side = "SHORT"

                if signal_side:
                    sl = price - (atr * 1.5) if signal_side == "LONG" else price + (atr * 1.5)
                    tp = price + (atr * 3.5) if signal_side == "LONG" else price - (atr * 3.5)
                    risk_amt = balance * RISK_PER_TRADE
                    price_risk = abs(price - sl)
                    size = (risk_amt / price_risk) if price_risk > 0 else 0.0

                    positions[sym] = {
                        "side": signal_side,
                        "entry_price": price,
                        "entry_time": t_stamp,
                        "sl": sl,
                        "tp": tp,
                        "size": size,
                        "initial_atr": atr,
                        "be_active": False
                    }
                    break # Position cap reached for this bar

        portfolio_equity.append({"timestamp": t_stamp, "Portfolio Balance": round(balance, 2)})

    return pd.DataFrame(portfolio_equity), pd.DataFrame(trades)

async def main():
    print("🚀 Fetching market data & executing optimized portfolio backtest...\n")
    dfs = {}
    for sym in SYMBOLS:
        df_1h, df_15m = await fetch_data(sym)
        dfs[sym] = compute_enhanced_indicators(df_1h, df_15m)

    eq_df, trades_df = run_optimized_portfolio(dfs)
    final_bal = eq_df["Portfolio Balance"].iloc[-1]
    net_pnl = final_bal - INITIAL_BALANCE
    ret = (net_pnl / INITIAL_BALANCE) * 100

    print("=" * 80)
    print("📊 OPTIMIZED TREND-ALIGNED SQUEEZE BREAKOUT PORTFOLIO RESULTS")
    print("=" * 80)
    print(f"Initial Balance:    ${INITIAL_BALANCE:,.2f}")
    print(f"Final Balance:      ${final_bal:,.2f}")
    print(f"Net PnL:            ${net_pnl:,.2f} ({ret:.2f}%)")
    print(f"Total Portfolio Trades: {len(trades_df)}")
    if not trades_df.empty:
        win_rate = (len(trades_df[trades_df["Net PnL ($)"] > 0]) / len(trades_df)) * 100
        print(f"Portfolio Win Rate: {win_rate:.2f}%")
        print("\n📜 RECENT EXECUTED TRADES:")
        print(trades_df.tail(8).to_string(index=False))
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
