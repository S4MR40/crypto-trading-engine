class RiskEngine:
    def validate_risk(self, symbol: str, direction: str, entry_price: float, depth_usd: float, min_depth: float):
        if depth_usd < min_depth:
            return {"passed": False, "reason": "Insufficient market depth"}
        return {"passed": True, "rr_ratio": 2.0}
