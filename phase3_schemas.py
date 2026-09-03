from pydantic import BaseModel, Field
from typing import Optional

class TechnicalContext(BaseModel):
    symbol: str
    timeframe: str = "1h"
    current_price: float
    rsi_14: float
    macd_signal: str
    orderbook_bids_usd: float
    orderbook_asks_usd: float

class LLMVerdict(BaseModel):
    verdict: str = Field(description="APPROVE or REJECT")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    recommended_strategy: str = Field(
        description="SPOT_SCALP, SPOT_SWING, DOLLAR_COST_AVERAGE, or PASS_NO_TRADE"
    )
    recommended_position_usd: float = Field(
        description="Dynamic position sizing based on risk-to-reward analysis"
    )
    suggested_sl_pct: float = Field(description="Dynamic Stop Loss percentage, e.g. 0.015 for 1.5%")
    suggested_tp_pct: float = Field(description="Dynamic Take Profit percentage, e.g. 0.045 for 4.5%")
    reasoning: str = Field(
        description="Explanation for why this specific strategy provides optimal risk/reward"
    )

class SignalPayload(BaseModel):
    technical: TechnicalContext
    target_capital_usd: float
