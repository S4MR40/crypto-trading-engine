import asyncio
import pandas as pd
import pandas_ta as ta
import ccxt.pro as ccxtpro

class OptimizedBacktester:
    def __init__(self, exchange_id: str = "binance", symbol: str = "BTC/USDT", capital: float = 1000.0, position_size: float = 20.0):
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.capital = capital
        self.initial_capital = capital
        self.position_size = position_size
        self.exchange = getattr(ccxtpro, exchange_id)()
        self.trades = []
        self.equity_curve = []

    async def fetch_historical_data(self, limit: int = 1000) -> pd.DataFrame:
        print(f"📥 Fetching {limit} historical 15m candles for {self.symbol} on {self.exchange_id.upper()}...")
        ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe="15m", limit=limit)
        await self.exchange.close()
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Technical Indicators
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        df['ema_200'] = ta.ema(df['close'], length=200)
        
        macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
        df['macd_hist'] = macd.iloc[:, 1]
        
        return df.dropna().reset_index(drop=True)

    def run_backtest(self, df: pd.DataFrame):
        active_position = None

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            price = row['close']
            atr = row['atr']

            # 1. Manage active position
            if active_position:
                direction = active_position['direction']
                sl = active_position['sl']
                tp = active_position['tp']
                entry = active_position['entry']
                size = active_position['size']

                if (direction == "LONG" and row['high'] >= tp) or (direction == "SHORT" and row['low'] <= tp):
                    pnl = ((tp - entry) / entry) * size if direction == "LONG" else ((entry - tp) / entry) * size
                    self.capital += pnl
                    self.trades.append({"type": "EXIT_TP", "pnl": pnl, "entry": entry, "exit": tp, "direction": direction})
                    active_position = None
                    continue

                elif (direction == "LONG" and row['low'] <= sl) or (direction == "SHORT" and row['high'] >= sl):
                    pnl = ((sl - entry) / entry) * size if direction == "LONG" else ((entry - sl) / entry) * size
                    self.capital += pnl
                    self.trades.append({"type": "EXIT_SL", "pnl": pnl, "entry": entry, "exit": sl, "direction": direction})
                    active_position = None
                    continue

            # 2. Strict Signal Logic (Trend-aligned + RSI + MACD confirmation)
            if not active_position:
                # Long: Price > EMA200 (Uptrend) AND RSI <= 30 AND MACD histogram turning up
                if (price > row['ema_200']) and (row['rsi'] <= 30.0) and (row['macd_hist'] > prev_row['macd_hist']):
                    sl = price - (atr * 1.5)
                    tp = price + (atr * 3.0)
                    active_position = {"direction": "LONG", "entry": price, "sl": sl, "tp": tp, "size": self.position_size}
                
                # Short: Price < EMA200 (Downtrend) AND RSI >= 70 AND MACD histogram turning down
                elif (price < row['ema_200']) and (row['rsi'] >= 70.0) and (row['macd_hist'] < prev_row['macd_hist']):
                    sl = price + (atr * 1.5)
                    tp = price - (atr * 3.0)
                    active_position = {"direction": "SHORT", "entry": price, "sl": sl, "tp": tp, "size": self.position_size}

            self.equity_curve.append(self.capital)

        self.generate_report()

    def generate_report(self):
        df_trades = pd.DataFrame(self.trades)
        if df_trades.empty:
            print("No trades triggered with these strict parameters.")
            return

        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] < 0]
        
        win_rate = (len(wins) / len(df_trades)) * 100
        gross_profit = wins['pnl'].sum()
        gross_loss = abs(losses['pnl'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        print("\n==========================================================")
        print(f"      OPTIMIZED BACKTEST [EMA200 FILTER + MACD]          ")
        print("==========================================================")
        print(f"Initial Balance  : ${self.initial_capital:.2f}")
        print(f"Final Balance    : ${self.capital:.2f}")
        print(f"Total Trades     : {len(df_trades)}")
        print(f"Win Rate         : {win_rate:.2f}% ({len(wins)} W / {len(losses)} L)")
        print(f"Profit Factor    : {profit_factor:.2f}")
        print("==========================================================\n")

if __name__ == "__main__":
    tester = OptimizedBacktester(exchange_id="binance", symbol="BTC/USDT")
    df = asyncio.run(tester.fetch_historical_data(limit=1000))
    tester.run_backtest(df)
