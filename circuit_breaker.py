import time

class CircuitBreaker:
    def __init__(self, max_failures: int = 3, reset_timeout: int = 60):
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = 0

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()

    def record_success(self):
        self.failure_count = 0

    def is_tripped(self) -> bool:
        if self.failure_count >= self.max_failures:
            if time.time() - self.last_failure_time < self.reset_timeout:
                return True
            else:
                self.failure_count = 0
        return False
