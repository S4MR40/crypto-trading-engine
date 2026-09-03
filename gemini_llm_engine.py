import os
from google import genai
from google.genai import types
from phase3_schemas import SignalPayload, LLMVerdict

class GeminiLLMEngine:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        self.client = genai.Client(api_key=api_key)

    async def evaluate_signal(self, payload: SignalPayload) -> LLMVerdict:
        prompt = f"""
        Act as an automated portfolio manager and strategy router.
        Analyze this technical context:
        {payload.model_dump_json(indent=2)}

        Tasks:
        1. Select the trading strategy that yields the highest probability of profit while defending capital:
           - SPOT_SCALP (High volatility, clear S/R levels, tight SL)
           - SPOT_SWING (Strong macro trend, wide SL, high R:R)
           - DOLLAR_COST_AVERAGE (Ranging/Accumulation, small position sizing)
           - PASS_NO_TRADE (High risk, bad orderbook liquidity, choppy noise)
        2. Assign position size (USD), Stop Loss %, and Take Profit % to keep Risk-to-Reward >= 2.0.
        3. Output approval decision (`APPROVE` or `REJECT`).
        """

        response = await self.client.aio.models.generate_content(
            model='gemini-3.6-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LLMVerdict,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
            ),
        )
        return LLMVerdict.model_validate_json(response.text)
