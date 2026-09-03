import asyncio
import pandas as pd
import pandas_ta as ta
import ccxt.pro as ccxtpro

class HistoricalBacktester:
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
        print(f"\n📥 Fetching {limit} historical 15m candles for {self.symbol} on {self.exchange_id.upper()}...")
        ohlcv = await self.exchange.fetch_ohlcv(self.symbol, timeframe="15m", limit=limit)
        await self.exchange.close()
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        bbands = ta.bbands(df['close'], length=20, std=2.0)
        df['bb_lower'] = bbands.iloc[:, 0]
        df['bb_upper'] = bbands.iloc[:, 2]
        
        return df.dropna().reset_index(drop=True)

    def run_backtest(self, df: pd.DataFrame):
        active_position = None

        for i in range(1, len(df)):
            row = df.iloc[i]
            price = row['close']
            atr = row['atr']

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

            if not active_position:
                if row['rsi'] <= 32.0:
                    sl = price - (atr * 1.5)
                    tp = price + (atr * 3.0)
                    active_position = {"direction": "LONG", "entry": price, "sl": sl, "tp": tp, "size": self.position_size}
                
                elif row['rsi'] >= 68.0:
                    sl = price + (atr * 1.5)
                    tp = price - (atr * 3.0)
                    active_position = {"direction": "SHORT", "entry": price, "sl": sl, "tp": tp, "size": self.position_size}

            self.equity_curve.append(self.capital)

        self.generate_report()

    def generate_report(self):
        df_trades = pd.DataFrame(self.trades)
        if df_trades.empty:
            print("No trades generated during this backtest period.")
            return

        wins = df_trades[df_trades['pnl'] > 0]
        losses = df_trades[df_trades['pnl'] < 0]
        
        win_rate = (len(wins) / len(df_trades)) * 100
        gross_profit = wins['pnl'].sum()
        gross_loss = abs(losses['pnl'].sum())
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf')

        equity_series = pd.Series(self.equity_curve)
        peak = equity_series.cummax()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min() * 100

        print("\n==========================================================")
        print(f"         BACKTEST RESULTS [{self.exchange_id.upper()} | {self.symbol}]       ")
        print("==========================================================")
        print(f"Initial Balance  : ${self.initial_capital:.2f}")
        print(f"Final Balance    : ${self.capital:.2f}")
        print(f"Total Trades     : {len(df_trades)}")
        print(f"Win Rate         : {win_rate:.2f}% ({len(wins)} W / {len(losses)} L)")
        print(f"Profit Factor    : {profit_factor:.2f}")
        print(f"Max Drawdown     : {max_drawdown:.2f}%")
        print("==========================================================\n")

if __name__ == "__main__":
    tester = HistoricalBacktester(exchange_id="binance", symbol="BTC/USDT")
    df = asyncio.run(tester.fetch_historical_data(limit=1000))
    tester.run_backtest(df)
