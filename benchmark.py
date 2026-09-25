"""
Benchmark orchestrator
Builds the Docker image, then runs each attack against the server
under different resource constraints and saves results to results/.
"""

import subprocess
import time
import json
import os
import sys
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TARGET_HOST = "localhost"
TARGET_PORT = 5001
TARGET_URL = f"http://{TARGET_HOST}:{TARGET_PORT}"
IMAGE_NAME = "ddos-demo-server"
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")

ATTACK_DURATION = 20
FLOOD_THREADS = 100
SLOWLORIS_SOCKETS = 150
DDOS_SOURCES = 8
DDOS_THREADS_PER_SOURCE = 15

# Resource configurations to test
CONFIGS = [
    {"cpus": "0.25", "memory": "128m", "label": "0.25 CPU / 128 MB"},
    {"cpus": "0.5",  "memory": "256m", "label": "0.5 CPU / 256 MB"},
    {"cpus": "1.0",  "memory": "512m", "label": "1.0 CPU / 512 MB"},
    {"cpus": "2.0",  "memory": "1g",   "label": "2.0 CPU / 1 GB"},
]

# Attack types to run
ATTACKS = ["http_flood", "slowloris", "ddos_sim"]

# Whether to also run against the protected server
RUN_PROTECTED = True


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

def build_image():
    print("Building Docker image...")
    cmd = ["docker", "build", "-t", IMAGE_NAME, os.path.join(os.path.dirname(__file__), "server")]
    subprocess.run(cmd, check=True)
    print("Image built.")


def start_container(cpus: str, memory: str, app_module: str = "app:app") -> str:
    cmd = [
        "docker", "run", "-d",
        "--cpus", cpus,
        "--memory", memory,
        "-p", f"{TARGET_PORT}:5000",
        "-e", f"APP_MODULE={app_module}",
        IMAGE_NAME,
        "sh", "-c", f"gunicorn --workers 4 --threads 2 --bind 0.0.0.0:5000 {app_module}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    container_id = result.stdout.strip()
    return container_id


def stop_container(container_id: str):
    subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)


def wait_for_server(timeout: float = 30.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{TARGET_URL}/", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Server did not become ready within {timeout}s")


# ---------------------------------------------------------------------------
# Attack runners
# ---------------------------------------------------------------------------

def run_attack(attack_name: str) -> dict:
    """Run one attack and return a stats dict."""
    if attack_name == "http_flood":
        from attacks.http_flood import run as flood_run
        r = flood_run(f"{TARGET_URL}/", num_threads=FLOOD_THREADS, duration=ATTACK_DURATION)
        return {
            "total": r.total,
            "successes": r.successes,
            "rate_limited": r.rate_limited,
            "failures": r.failures,
            "success_rate": round(r.success_rate, 2),
            "block_rate": round(r.block_rate, 2),
            "req_per_sec": round(r.requests_per_second, 2),
            "avg_latency_ms": round(r.avg_latency * 1000, 2),
            "p95_latency_ms": round(r.p95_latency * 1000, 2),
        }

    elif attack_name == "slowloris":
        from attacks.slowloris import run as slow_run
        r = slow_run(TARGET_HOST, TARGET_PORT, num_sockets=SLOWLORIS_SOCKETS, duration=ATTACK_DURATION)
        avg_probe = (
            round(sum(r.probe_latencies) / len(r.probe_latencies) * 1000, 2)
            if r.probe_latencies else None
        )
        return {
            "sockets_opened": r.sockets_opened,
            "sockets_failed": r.sockets_failed,
            "keep_alive_sends": r.keep_alive_sends,
            "probe_avg_latency_ms": avg_probe,
            "probe_failures": r.probe_failures,
        }

    elif attack_name == "ddos_sim":
        from attacks.ddos_sim import run as ddos_run
        r = ddos_run(
            f"{TARGET_URL}/",
            num_sources=DDOS_SOURCES,
            threads_per_source=DDOS_THREADS_PER_SOURCE,
            duration=ATTACK_DURATION,
        )
        return {
            "total": r.total_requests,
            "successes": r.total_successes,
            "rate_limited": r.total_rate_limited,
            "failures": r.total_failures,
            "success_rate": round(r.success_rate, 2),
            "block_rate": round(r.block_rate, 2),
            "req_per_sec": round(r.requests_per_second, 2),
            "avg_latency_ms": round(r.avg_latency * 1000, 2),
            "p95_latency_ms": round(r.p95_latency * 1000, 2),
            "num_sources": r.num_sources,
        }

    raise ValueError(f"Unknown attack: {attack_name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_benchmark(protected: bool = False):
    tag = "protected" if protected else "unprotected"
    app_module = "app_protected:app" if protected else "app:app"
    all_results = {}

    for cfg in CONFIGS:
        label = cfg["label"]
        print(f"\n{'='*60}")
        print(f"Config: {label}  [{tag}]")
        print(f"{'='*60}")

        container_id = start_container(cfg["cpus"], cfg["memory"], app_module)
        try:
            wait_for_server()
            print(f"  Server ready.")

            cfg_results = {"config": cfg, "protected": protected, "attacks": {}}

            for attack in ATTACKS:
                print(f"\n  Running {attack}...")
                try:
                    stats = run_attack(attack)
                    cfg_results["attacks"][attack] = stats
                    for k, v in stats.items():
                        print(f"    {k}: {v}")
                except Exception as e:
                    print(f"    ERROR: {e}")
                    cfg_results["attacks"][attack] = {"error": str(e)}

                # Let the server recover between attacks
                time.sleep(3)

        finally:
            stop_container(container_id)
            print(f"  Container stopped.")

        all_results[label] = cfg_results

    os.makedirs(RESULTS_DIR, exist_ok=True)
    out_file = os.path.join(RESULTS_DIR, f"results_{tag}.json")
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to {out_file}")
    return all_results


if __name__ == "__main__":
    build_image()

    print("\n--- RUNNING UNPROTECTED SERVER BENCHMARK ---")
    run_benchmark(protected=False)

    if RUN_PROTECTED:
        print("\n--- RUNNING PROTECTED SERVER BENCHMARK ---")
        run_benchmark(protected=True)

    print("\nDone. Run visualize.py to generate graphs.")
