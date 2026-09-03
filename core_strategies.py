import numpy as np
import pandas as pd
import pandas_ta as ta

def calculate_core_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes technical indicators and boolean signals for 5 foundational strategies:
    1. Trend Following (EMA Cross + Supertrend)
    2. Support & Resistance (Pivot Reversals)
    3. Breakout Trading (Donchian / Range Expansion)
    4. Mean Reversion (RSI + Bollinger Bands)
    5. Buying Pullbacks in an Uptrend (EMA Trend + Dip)
    """
    df = df.copy()

    # Base Indicators
    df['ema_50'] = ta.ema(df['close'], length=50)
    df['ema_200'] = ta.ema(df['close'], length=200)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # Bollinger Bands for Mean Reversion
    bb = ta.bbands(df['close'], length=20, std=2)
    df['bb_lower'] = bb.iloc[:, 0]
    df['bb_upper'] = bb.iloc[:, 2]

    # Donchian Channels for Breakout Trading
    df['donchian_high_20'] = df['high'].shift(1).rolling(20).max()
    df['donchian_low_20'] = df['low'].shift(1).rolling(20).min()

    # 1. Trend Following Signal
    # Condition: 50 EMA > 200 EMA & Price closing above 50 EMA
    df['sig_trend_following'] = (df['ema_50'] > df['ema_200']) & (df['close'] > df['ema_50'])

    # 2. Support & Resistance Signal
    # Condition: Low hits recent 20-period support level and bounces back up
    df['sig_support_bounce'] = (df['low'] <= df['donchian_low_20']) & (df['close'] > df['open'])

    # 3. Breakout Trading Signal
    # Condition: Close breaks above the 20-period highest high
    df['sig_breakout'] = df['close'] > df['donchian_high_20']

    # 4. Mean Reversion Signal
    # Condition: Price dips below lower Bollinger Band while RSI is oversold (< 30)
    df['sig_mean_reversion'] = (df['close'] < df['bb_lower']) & (df['rsi'] < 30)

    # 5. Buying Pullbacks in an Uptrend Signal
    # Condition: Strong macro uptrend (Price > 200 EMA) + Short-term pullback (RSI < 45 & Low <= 50 EMA)
    df['sig_uptrend_pullback'] = (
        (df['close'] > df['ema_200']) & 
        (df['low'] <= df['ema_50']) & 
        (df['rsi'] < 45) & 
        (df['close'] > df['open'])
    )

    return df

# Example Execution
if __name__ == "__main__":
    # Generate dummy price data to illustrate signal generation
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=250, freq="1h")
    prices = 100 + np.cumsum(np.random.randn(250) * 0.5)
    
    sample_df = pd.DataFrame({
        "timestamp": dates,
        "open": prices,
        "high": prices + np.abs(np.random.randn(250)),
        "low": prices - np.abs(np.random.randn(250)),
        "close": prices + (np.random.randn(250) * 0.2),
        "volume": np.random.randint(100, 1000, size=250)
    })

    signal_df = calculate_core_signals(sample_df)
    
    print("=" * 70)
    print("🎯 STRATEGY SIGNAL COUNT SUMMARY (250 Sample Bars)")
    print("=" * 70)
    print(f"1. Trend Following Triggered:         {signal_df['sig_trend_following'].sum()} bars")
    print(f"2. Support Bounce Triggered:          {signal_df['sig_support_bounce'].sum()} bars")
    print(f"3. Breakout Triggered:                {signal_df['sig_breakout'].sum()} bars")
    print(f"4. Mean Reversion Triggered:          {signal_df['sig_mean_reversion'].sum()} bars")
    print(f"5. Uptrend Pullback Triggered:        {signal_df['sig_uptrend_pullback'].sum()} bars")
