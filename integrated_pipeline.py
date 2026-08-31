import asyncio
from typing import List, Dict, Any, Optional
from schemas import MacroRegime
from phase3_schemas import SignalPayload, TechnicalContext
from gemini_llm_engine import GeminiLLMAgent, DeterministicStubLLMAgent, BaseLLMAgent

class IntegratedTradingPipeline:
    def __init__(self, symbols: List[str], data_engine, risk_engine, circuit_breaker, llm_agent: Optional[BaseLLMAgent] = None, min_2pct_depth_usd: float = 50000.0):
        self.symbols = symbols
        self.data_engine = data_engine
        self.risk_engine = risk_engine
        self.circuit_breaker = circuit_breaker
        self.llm_agent = llm_agent or DeterministicStubLLMAgent()
        self.min_2pct_depth_usd = min_2pct_depth_usd

    async def evaluate_symbol_integrated(self, symbol: str, macro_regime: MacroRegime, micro_history: List[Any]) -> Dict[str, Any]:
        data = await self.data_engine.get_latest_data(symbol)
        direction = "LONG" if "BTC" in symbol else "SHORT"
        risk_check = self.risk_engine.validate_risk(symbol, direction, data["price"], data["depth_usd"], self.min_2pct_depth_usd)
        
        if not risk_check["passed"]:
            return {"symbol": symbol, "status": "REJECTED", "reason": risk_check["reason"]}

        payload = SignalPayload(
            symbol=symbol, timestamp="2026-08-31T00:00:00Z", timeframe="1h",
            regime=macro_regime, mtf_direction=direction,
            technical=TechnicalContext(
                entry_price=data["price"],
                stop_loss=data["price"] * 0.98,
                take_profit=data["price"] * 1.04,
                liquidity_depth_usd=data["depth_usd"],
                rr_ratio=risk_check["rr_ratio"]
            )
        )
        verdict = await self.llm_agent.evaluate_signal(payload)
        
        if verdict.action == "APPROVE":
            return {"symbol": symbol, "status": "APPROVED", "direction": direction, "entry_price": data["price"], "llm_reasoning": verdict.reasoning}
        return {"symbol": symbol, "status": "REJECTED", "reason": verdict.reasoning}
