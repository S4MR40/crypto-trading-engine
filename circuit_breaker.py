class SystemCircuitBreaker:
    def __init__(self, max_heartbeat_gap_sec: float = 60.0):
        self.max_gap = max_heartbeat_gap_sec
    def check_health(self) -> bool:
        return True
