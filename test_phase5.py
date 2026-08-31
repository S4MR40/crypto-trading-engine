import asyncio, os
from schemas import MacroRegime, MicroSignal
from circuit_breaker import SystemCircuitBreaker
from ws_engine import AsyncMultiAssetDataEngine
from risk_engine import RiskEngine
from gemini_llm_engine import GeminiLLMAgent, DeterministicStubLLMAgent
from integrated_pipeline import IntegratedTradingPipeline
from broker_adapter import BrokerAdapter

async def run_phase5_tests():
    print("==========================================")
    print("   RUNNING PHASE 5 E2E EXECUTION SUITE    ")
    print("==========================================")
    symbols = ["BTC/USDT", "ETH/USDT"]
    de = AsyncMultiAssetDataEngine(symbols=symbols)
    cb = SystemCircuitBreaker()
    risk = RiskEngine()
    broker = BrokerAdapter(exchange_id="kraken", paper_trading=True)

    api_key = os.getenv("GEMINI_API_KEY")
    llm = GeminiLLMAgent(api_key=api_key) if api_key else DeterministicStubLLMAgent()
    pipeline = IntegratedTradingPipeline(symbols=symbols, data_engine=de, risk_engine=risk, circuit_breaker=cb, llm_agent=llm)

    states = {
        "BTC/USDT": {"macro_regime": MacroRegime.BULLISH_TREND, "micro_history": [MicroSignal.BULLISH_REVERSAL_CONFIRMED]},
        "ETH/USDT": {"macro_regime": MacroRegime.BEARISH_PULLBACK, "micro_history": [MicroSignal.BEARISH_REVERSAL_CONFIRMED]}
    }

    executed_trades = []
    for sym in symbols:
        res = await pipeline.evaluate_symbol_integrated(sym, states[sym]["macro_regime"], states[sym]["micro_history"])
        if res.get("status") == "APPROVED":
            exec_res = await broker.execute_trade(res, position_size_usd=2500.0)
            executed_trades.append(exec_res)
            print(f"  -> Order Status for {sym}: {exec_res["status"]} | ID: {exec_res.get("paper_order_id")}")

    await de.close()
    await broker.close()
    print("\n==========================================")
    print("   PHASE 5 E2E SUITE COMPLETED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(run_phase5_tests())
