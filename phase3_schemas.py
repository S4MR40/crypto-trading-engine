from pydantic import BaseModel, Field
from typing import Optional
from schemas import MacroRegime
class TechnicalContext(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit: float
    liquidity_depth_usd: float
    rr_ratio: float
class SignalPayload(BaseModel):
    symbol: str
    timestamp: str
    timeframe: str
    regime: MacroRegime
    mtf_direction: str
    technical: TechnicalContext
    sentiment_summary: Optional[str] = ""
class LLMExecutionVerdict(BaseModel):
    action: str
    confidence: float
    reasoning: str
