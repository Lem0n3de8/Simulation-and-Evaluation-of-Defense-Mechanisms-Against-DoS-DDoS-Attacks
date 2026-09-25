"""
Generates comparison graphs from benchmark results.
Reads results/results_unprotected.json and results/results_protected.json.
"""

import json
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
GRAPHS_DIR = os.path.join(RESULTS_DIR, "graphs")


def load(filename: str) -> dict:
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    # Fix ddos_sim totals that may have been saved before the total_requests bug was fixed
    for cfg in data.values():
        atk = cfg.get("attacks", {}).get("ddos_sim", {})
        if atk and "rate_limited" in atk:
            real_total = atk.get("successes", 0) + atk.get("rate_limited", 0) + atk.get("failures", 0)
            if real_total > 0:
                atk["block_rate"] = round(atk["rate_limited"] / real_total * 100, 2)
                atk["success_rate"] = round(atk["successes"] / real_total * 100, 2)
                atk["total"] = real_total
    return data


def _labels(data: dict) -> list[str]:
    return list(data.keys())


def _extract(data: dict, attack: str, metric: str) -> list:
    values = []
    for label, cfg in data.items():
        v = cfg.get("attacks", {}).get(attack, {}).get(metric)
        values.append(v if v is not None else 0)
    return values


# ---------------------------------------------------------------------------
# Figure 1 — HTTP Flood: success rate vs resources
# ---------------------------------------------------------------------------

def fig_http_flood_success_rate(unprotected: dict, protected: dict):
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    unp = _extract(unprotected, "http_flood", "success_rate")
    pro = _extract(protected, "http_flood", "success_rate") if protected else []

    ax.bar(x - width / 2, unp, width, label="Without protection", color="#e74c3c", alpha=0.85)
    if pro:
        ax.bar(x + width / 2, pro, width, label="With rate limiting", color="#2ecc71", alpha=0.85)

    ax.set_xlabel("Ressources allocated to the server")
    ax.set_ylabel("Success rate (%)")
    ax.set_title("HTTP Flood — Success rate by ressources")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylim(0, 110)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, "http_flood_success_rate.png")


# ---------------------------------------------------------------------------
# Figure 2 — HTTP Flood: average latency vs resources
# ---------------------------------------------------------------------------

def fig_http_flood_latency(unprotected: dict, protected: dict):
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    unp = _extract(unprotected, "http_flood", "avg_latency_ms")
    p95 = _extract(unprotected, "http_flood", "p95_latency_ms")

    ax.bar(x - width / 2, unp, width, label="Average Latency", color="#3498db", alpha=0.85)
    ax.bar(x + width / 2, p95, width, label="P95 Latency", color="#e67e22", alpha=0.85)

    ax.set_xlabel("Ressources allocated to the server")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("HTTP Flood — Average Latency and P95 (without protection)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, "http_flood_latency.png")


# ---------------------------------------------------------------------------
# Figure 3 — HTTP Flood: requests/s vs resources
# ---------------------------------------------------------------------------

def fig_http_flood_rps(unprotected: dict, protected: dict):
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    unp = _extract(unprotected, "http_flood", "req_per_sec")
    pro = _extract(protected, "http_flood", "req_per_sec") if protected else []

    ax.bar(x - width / 2, unp, width, label="Without protection", color="#e74c3c", alpha=0.85)
    if pro:
        ax.bar(x + width / 2, pro, width, label="With rate limiting", color="#2ecc71", alpha=0.85)

    ax.set_xlabel("Ressources allocated to the server")
    ax.set_ylabel("Requests / second (attacking side)")
    ax.set_title("HTTP Flood — Attack rate based on resources")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, "http_flood_rps.png")


# ---------------------------------------------------------------------------
# Figure 4 — Slowloris: probe failures vs resources
# ---------------------------------------------------------------------------

def fig_slowloris(unprotected: dict, protected: dict):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    # Left: probe failures (same across configs — shows consistent impact)
    unp_fail = _extract(unprotected, "slowloris", "probe_failures")
    pro_fail = _extract(protected, "slowloris", "probe_failures") if protected else []

    ax = axes[0]
    ax.bar(x - width / 2, unp_fail, width, label="Without protection", color="#e74c3c", alpha=0.85)
    if pro_fail:
        ax.bar(x + width / 2, pro_fail, width, label="With protection", color="#2ecc71", alpha=0.85)
    ax.set_title("Slowloris — Failed legitimate requests")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Number of failures (probe)")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)

    # Right: sockets opened vs gunicorn worker capacity (fixed at 8)
    unp_sockets = _extract(unprotected, "slowloris", "sockets_opened")
    gunicorn_capacity = [8] * len(labels)   # 4 workers × 2 threads

    ax = axes[1]
    ax.bar(x, unp_sockets, label="Opened Slowloris connections", color="#e74c3c", alpha=0.85)
    ax.bar(x, gunicorn_capacity, label="Gunicorn capacity (4w × 2t = 8)", color="#2ecc71", alpha=0.85)
    ax.set_title("Slowloris — Connections vs. Server Capacity")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylabel("Number of TCP connections")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    # Annotate the saturation ratio
    for xi, s in zip(x, unp_sockets):
        ax.text(xi, s + 2, f"×{s//8}", ha="center", fontsize=9, color="#c0392b", fontweight="bold")

    fig.suptitle("Slowloris Attack — Server connection congestion")
    fig.tight_layout()
    _save(fig, "slowloris.png")


# ---------------------------------------------------------------------------
# Figure 5 — DDoS Simulation: comparison with single-source flood
# ---------------------------------------------------------------------------

def fig_ddos_vs_flood(unprotected: dict):
    fig, ax = plt.subplots(figsize=(9, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    flood_rps = _extract(unprotected, "http_flood", "req_per_sec")
    ddos_rps = _extract(unprotected, "ddos_sim", "req_per_sec")

    ax.bar(x - width / 2, flood_rps, width, label="DoS mono-source (HTTP Flood)", color="#3498db", alpha=0.85)
    ax.bar(x + width / 2, ddos_rps, width, label="DDoS multi-sources simulé", color="#e74c3c", alpha=0.85)

    ax.set_xlabel("Ressources allocated to the server")
    ax.set_ylabel("Requests / second")
    ax.set_title("DoS vs DDoS — Total flow based on available resources")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.legend()
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    fig.tight_layout()
    _save(fig, "ddos_vs_flood.png")


# ---------------------------------------------------------------------------
# Figure 6 — Rate limiting effectiveness: block rate vs success rate
# ---------------------------------------------------------------------------

def fig_rate_limiting(unprotected: dict, protected: dict):
    if not protected:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    width = 0.35

    for ax, attack, title in [
        (axes[0], "http_flood", "HTTP Flood"),
        (axes[1], "ddos_sim", "DDoS Simulé"),
    ]:
        unp_ok = _extract(unprotected, attack, "success_rate")
        pro_ok = _extract(protected, attack, "success_rate")
        pro_blocked = _extract(protected, attack, "block_rate")

        ax.bar(x - width, unp_ok, width, label="Wihtout protection (2xx)", color="#e74c3c", alpha=0.85)
        ax.bar(x, pro_ok, width, label="With rate limiting (2xx)", color="#2ecc71", alpha=0.85)
        ax.bar(x + width, pro_blocked, width, label="Blocked (429)", color="#f39c12", alpha=0.85)

        ax.set_title(f"{title} — Effect of rate limiting")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15, ha="right")
        ax.set_ylabel("Percentage of requests")
        ax.set_ylim(0, 115)
        ax.yaxis.set_major_formatter(mticker.PercentFormatter())
        ax.legend(fontsize=8)
        ax.grid(axis="y", linestyle="--", alpha=0.5)

    fig.suptitle("Rate Limiting Effectiveness — Requests Served vs. Blocked")
    fig.tight_layout()
    _save(fig, "rate_limiting_effect.png")


# ---------------------------------------------------------------------------
# Figure 7 — Overview dashboard (all attacks, success rate)
# ---------------------------------------------------------------------------

def fig_overview(unprotected: dict):
    attacks = ["http_flood", "slowloris", "ddos_sim"]
    attack_labels = ["HTTP Flood", "Slowloris\n(probe failures)", "DDoS Simulé"]
    labels = _labels(unprotected)
    x = np.arange(len(labels))
    colors = ["#e74c3c", "#9b59b6", "#e67e22"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=False)

    for i, (atk, atk_label, color) in enumerate(zip(attacks, attack_labels, colors)):
        ax = axes[i]
        if atk == "slowloris":
            metric = "probe_failures"
            ylabel = "Probe failures (nb)"
        else:
            metric = "success_rate"
            ylabel = "Success rate (%)"

        values = _extract(unprotected, atk, metric)
        bars = ax.bar(x, values, color=color, alpha=0.85)
        ax.set_title(atk_label)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        if metric == "success_rate":
            ax.set_ylim(0, 110)
            ax.yaxis.set_major_formatter(mticker.PercentFormatter())

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                    f"{val:.0f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Overview — Impact of DoS/DDoS Attacks (Without Protection)", fontsize=13)
    fig.tight_layout()
    _save(fig, "overview.png")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save(fig, filename: str):
    os.makedirs(GRAPHS_DIR, exist_ok=True)
    path = os.path.join(GRAPHS_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Loading results...")
    unprotected = load("results_unprotected.json")
    protected = load("results_protected.json")

    if not unprotected:
        print("No results found. Run benchmark.py first.")
        raise SystemExit(1)

    print("Generating graphs...")
    fig_http_flood_success_rate(unprotected, protected)
    fig_http_flood_latency(unprotected, protected)
    fig_http_flood_rps(unprotected, protected)
    fig_slowloris(unprotected, protected)
    fig_ddos_vs_flood(unprotected)
    fig_rate_limiting(unprotected, protected)
    fig_overview(unprotected)

    print(f"\nAll graphs saved in {GRAPHS_DIR}/")
