# Simulation and analysis of Denial of Service (DoS/DDoS)

## Introduction

Denial of service attacks are one of the oldest and most widespread threat in computer security. Unlike attacks targeting confidentiality or integrity of data, they target the availability of a service, making it inaccessible to its legitimate users. This report presents the conception and the analysis of a DoS and DDos attacks simulation laboratory produced in a controlled environment.

The objective is double: first, to understand the mechanisms underlying those attacks, second, to quantitatively measure the impact on hardware ressources allocated to the target server on its resilience. A comparison with and without defence mechanism (rate limiting) rounds out the analysis.

Section 1 sets the theoritical context. Sections 2 and 3 precise the goals. Section 4 presents the project structure. Section 5 and 6 present the results. Section 7 describes possible future work.

--- 

## 1. General context of the question

### 1.1 Definition and classification of DoS/DDoS attacks

A Denial of Service (DoS) attack consists or sending a large enough volume of requests or connections to exhaust target server computational ressources (CPU, memory, network connections), making it incapable of accepting legitimate requests [1]. When the attack originates from multiple coordinated sources, we call it Distributed Denial of Service (DDoS) which considerably complicates defense based on IP blocking.

From the network stack perspective, attacks can be classified in 3 main categories [2] :

| Layer | Type | Example |
| ----- | ---- | ------- |
| Layer 3/4 (network/transport) | Volume-based or protocol-related | SYN Flood, UDP Flood, ICMP Flood |
| Layer 7 (application) | application exhaustion | HTTP Flood, Slowloris |
| Amplification | Reflexion | DNS Amplification, NTP Amplification |

This project focuses on the layer 7 attacks (HTTP), the most relecant with a Flask web server, and on a multi-source DDos simulation.

### 1.2 Implemented attacks mechanisms

**HTTP Flood** : The attacker opens a large number of simultaneous TCP connections and sents full HTTP GET requests at a maximal rate. Each request is valid; it's the volume that saturates the server. The server must handle each request (header parsing, execute the application logic, response formating), consumming CPU and memory ressources for each.

**Slowloris** : Suggested by RSnake in 2009 [3], this method maintains a large number of TCP connections partially opens by sending incomplete HTTP headers at a very slow rate. The server keeps each connection opened, waiting for the end of the request, exhausting its workers pool or available threads. The legitimate requests can't find any available worker to process them.

**Simulated DDoS (multi-sources)** : Multiple independent processes, each with its own threads pool and a distinct User-Agent, simultaneously launch an HTTP Flood. This simulates attacks from various sources, making blocking based on source IP address ineffective: each individual source appears to be within acceptable limits.

### 1.3 Real life example and consequences

DDoS attacks are always increasing. In 2018, Github suffered from one of the most important attack ever recorded : 1,3 Tbps via a Memcached amplification [4]. In 2020, AWS reported a 2,3 Tbps attack [5]. Those figures show how even large scale infrastructure are vulnerable. For small organisation or a critical service (hospital, national infrastructure), even a modest-volumed attack can be enough to cause a total service outage, with serious financial or human consequences.

---

## 2. Conceptual objectives

1. Understand the mechanisms behind three types of Layer 7 DoS/DDoS attacks (HTTP Flood, Slowloris, multi-source DDoS) and their fundamental differences.

2. Correlate hardware resources with attack resilience: quantitatively determine how a server’s CPU and RAM limitations affect its ability to absorb a given attack volume.

3. Understand how a multi-process/multi-threaded web server (gunicorn) works and how the server’s architecture determines its vulnerability to each type of attack.

4. Evaluate the effectiveness of an application-level countermeasure (rate limiting) and understand its limitations when facing distributed attacks.

---

## 3. Practical objectives

1. Set up a reproducible target server: a Flask application deployed in a Docker container, whose resources (CPU, memory) are controlled by Docker parameters (`--cpus`, `--memory`).

2. Implement three attack scripts in Python:
   - `http_flood.py`: multi-threaded HTTP flood with metric collection (latency, req/s, error rate).
   - `slowloris.py`: maintaining partial connections while measuring the impact on legitimate clients.
   - `ddos_sim.py`: multi-process simulation of a DDoS attack from N distinct sources.

3. Automate benchmarks: a `benchmark.py` script orchestrates the entire sequence; that is, building the Docker image, starting the container with a given configuration, executing the attacks, stopping the container, and saving the results. This is done for four resource configurations and two modes (with/without protection).

4. Visualize the results: automatically generate comparative graphs (latency, success rate, blocking rate, connection saturation) using `visualize.py`.

---

## 4. Project architecture

The project is organized around a modular architecture that enables the automation of the entire experimental process, from server deployment to the generation of graphs.

### 4.1 Target server

The server is a Flask application running with Gunicorn in a Docker container. The resources allocated to the container (CPU and memory) are configurable so that their impact on attack resilience can be evaluated. A variant of the server incorporates Flask-Limiter to compare behavior with and without a protection mechanism.

### 4.2 Attack scripts

Three independent attack tools were developed in Python:

- **HTTP Flood**: Massive sending of concurrent HTTP GET requests using multiple threads.
- **Slowloris**: Maintaining a large number of incomplete HTTP connections to tie up server resources.
- **Simulated DDoS**: launches multiple independent processes, each executing an HTTP Flood, to simulate a distributed attack.

Each script collects various metrics, including the number of requests sent, throughput, average latency, latency percentiles, and error rate.

### 4.3 Benchmark orchestration

The `benchmark.py` script automates the entire experiment workflow. For each resource configuration, it:

1. builds the Docker image,
2. starts the server with the selected configuration,
3. runs the different attack scenarios,
4. records the produced metrics,
5. stops the container before moving to the next configuration.

This approach guarantees the reproducibility of the measurements and minimizes manual intervention.

### 4.4 Results visualization

The collected data is then processed by `visualize.py`, which generates the graphs used in this report. The visualizations make it possible to compare the different hardware configurations as well as the effect of defense mechanisms on server performance.

### 4.5 Repository organization

```text
.
├── benchmark.py          # Experiment orchestration
├── visualize.py          # Graph generation
├── attacks/
│   ├── http_flood.py
│   ├── slowloris.py
│   └── ddos_sim.py
├── server/
│   ├── app.py
│   ├── app_protected.py
│   └── Dockerfile
├── results/
│   └── graphs/
└── report.pdf
```

---

## 5. Obtained results

### 5.1 Test environment

| Component | Value |
|-----------|-------|
| Target server | Flask 3.1 + Gunicorn 23.0 (4 workers, 2 threads/worker) |
| Containerization | Docker, image `python:3.11-slim` |
| Tested configurations | 0.25 CPU / 128 MB — 0.5 CPU / 256 MB — 1.0 CPU / 512 MB — 2.0 CPU / 1 GB |
| Test duration | 20 seconds |
| Mitigation tested | Flask-Limiter: 200 req/min and 30 req/s per IP |
| Attacker language | Python 3.11 |
| Network | Local network (port 5001) |

Each configuration was tested successively against the three attack types, first on the unprotected server and then on the server with rate limiting.

### 5.2 HTTP Flood

The HTTP flood sends concurrent GET requests from 100 threads to the `/` endpoint.

**Table 5.1 — HTTP Flood without protection**

| Configuration | Total req | Req/s | Average latency | P95 latency |
|--------------|-----------|-------|-----------------|------------|
| 0.25 CPU / 128 MB | 19 711 | 982 | 101.89 ms | 162.8 ms |
| 0.5 CPU / 256 MB | 34 534 | 1 700 | 58.44 ms | 115.6 ms |
| 1.0 CPU / 512 MB | 41 523 | 1 899 | 51.36 ms | 133.5 ms |
| 2.0 CPU / 1 GB | 42 149 | 1 902 | 50.83 ms | 132.1 ms |

The success rate (HTTP 2xx) remains at 100% in all cases because the server responds to all requests, but with significantly higher latency under resource constraints. A plateau is observed between 1.0 and 2.0 CPU (1,899 vs 1,902 req/s), indicating that the bottleneck has changed in nature (see Section 6).

![Average latency and P95 of the HTTP Flood according to resources](results/graphs/http_flood_latency.png)

![Throughput (req/s) of the HTTP Flood according to resources](results/graphs/http_flood_rps.png)

### 5.3 Slowloris

The attack opens 150 partial TCP connections simultaneously. The Gunicorn server has 4 workers × 2 threads = 8 active threads.

**Table 5.2 — Slowloris**

| Configuration | Open sockets | Socket/worker ratio | Probe failures |
|--------------|--------------|---------------------|----------------|
| 0.25 CPU / 128 MB | 150 | ×18.75 | 3 |
| 0.5 CPU / 256 MB | 150 | ×18.75 | 3 |
| 1.0 CPU / 512 MB | 150 | ×18.75 | 3 |
| 2.0 CPU / 1 GB | 150 | ×18.75 | 3 |

The 150 Slowloris connections represent 18.75 times the server's simultaneous processing capacity. The observable impact is uniform regardless of the CPU/RAM configuration, which illustrates that Slowloris exploits an architectural vulnerability (the number of workers) rather than a computational resource limitation.

![Slowloris connection saturation versus Gunicorn capacity](results/graphs/slowloris.png)

### 5.4 Multi-source simulated DDoS

The attack is launched from 8 independent processes, each with 15 threads, for a total of 120 simultaneous "clients".

**Table 5.3 — Multi-source DDoS without protection**

| Configuration | Total req | Req/s | Average latency | P95 latency |
|--------------|-----------|-------|-----------------|------------|
| 0.25 CPU / 128 MB | 10 906 | 75 | 165.94 ms | 296.3 ms |
| 0.5 CPU / 256 MB | 28 970 | 165 | 83.04 ms | 183.4 ms |
| 1.0 CPU / 512 MB | 49 408 | 282 | 48.75 ms | 91.5 ms |
| 2.0 CPU / 1 GB | 78 307 | 391 | 30.73 ms | 61.4 ms |

Unlike the single-source HTTP Flood, the DDoS continues to benefit from increased resources beyond 1 CPU, reaching 391 req/s at 2.0 CPU. The variability of P95 latency is also more pronounced (from 61 ms to 296 ms).

![Comparison of single-source DoS vs multi-source DDoS](results/graphs/ddos_vs_flood.png)

### 5.5 Effect of rate limiting

The protected server applies a limit of 30 requests per second per source IP address via Flask-Limiter [6]. Excess requests receive an HTTP 429 (*Too Many Requests*) response.

**Table 5.4 — HTTP Flood with rate limiting**

| Configuration | Req 2xx | Req 429 (blocked) | Blocking rate |
|--------------|--------|------------------|---------------|
| 0.25 CPU / 128 MB | 299 | 9 965 | 97.09 % |
| 0.5 CPU / 256 MB | 399 | 19 648 | 98.01 % |
| 1.0 CPU / 512 MB | 399 | 36 743 | 98.93 % |
| 2.0 CPU / 1 GB | 399 | 39 369 | 99.00 % |

With a limit of 30 req/s, the server effectively serves only ~300–400 requests over the 20-second test duration, i.e. around 20 req/s on average, close to the configured limit. All other requests are rejected with a 429 code, without consuming significant application resources.

![Served requests (2xx) vs blocked requests (429) with and without rate limiting](results/graphs/rate_limiting_effect.png)

---

## 6. Interpretation of the results

### 6.1 Relationship between CPU and processing capacity (HTTP Flood)

The results in Table 5.1 show a nearly linear improvement in latency between 0.25 CPU (101.89 ms) and 0.5 CPU (58.44 ms), then 1.0 CPU (51.36 ms), corresponding to a 43% reduction in latency when doubling CPU from 0.25 to 0.5.

The plateau observed between 1.0 and 2.0 CPU (51.36 ms vs 50.83 ms) is explained by a change in the bottleneck: beyond 1.0 CPU, it is no longer the CPU that limits throughput, but the number of Gunicorn workers (4 workers × 2 threads = 8 simultaneous connections). Adding CPU does not increase the maximum number of requests processed in parallel. This observation illustrates the principle of architectural attack surface: even with abundant hardware resources, a software constraint can become the point of failure.

### 6.2 Slowloris and the multi-threaded architecture

Table 5.2 reveals a surprising result: the Slowloris attack produces the same impact (3 probe failures) regardless of the hardware configuration. This shows that Slowloris targets an architectural vulnerability, the finite number of workers, rather than a CPU or RAM limitation.

However, the observed impact remains limited: Gunicorn uses a default synchronous worker model with kernel backlog handling for connections. Slowloris connections are maintained in the kernel TCP backlog (default 2048) rather than directly in the application threads. This behavior would differ with an Apache server in prefork mode, against which Slowloris is historically more effective [3]. This result is an implicit countermeasure: choosing a multi-threaded server naturally reduces vulnerability to Slowloris.

### 6.3 Effectiveness of rate limiting

Rate limiting achieves a blocking rate of 97% to 99% depending on the configuration (see Section 5.5). This countermeasure is very effective against a single-source HTTP Flood because all requests originate from the same IP address. The server effectively handles only ~20 req/s instead of the ~1,000–1,800 req/s submitted.

However, this countermeasure has a limitation when facing the simulated multi-source DDoS described in Section 5.4. Each source has its own limit of 30 req/s. With 8 distinct sources, the effective allowed rate becomes 8 × 30 = 240 req/s, which is well above the server's capacity at 0.25 CPU. An attacker with many sources can therefore bypass IP-based rate limiting. Complementary countermeasures (global rate limiting, CAPTCHA, CDN, BGP blackholing) would be necessary in this case [7].

### 6.4 The server never "crashed"

A notable point: in no configuration did the server return any HTTP 5xx error. The error rate remains 0% for all attacks without protection. This is explained by two factors: (1) the attacker and the server are running on the same physical machine, limiting the total attack power; and (2) Gunicorn properly handles excess connections through the TCP backlog without crashing. In a real scenario with an external attacker and unlimited bandwidth, the result would be different.

---

## 7. Possible improvements

### 7.1 Additional attacks

The SYN Flood attack (Layer 4) was not implemented because it requires raw sockets and root privileges, and its effectiveness depends strongly on network parameters. An implementation using the `scapy` library would be conceivable in a dedicated Linux VM [8].

A DNS amplification attack would illustrate volume-based attacks at the network layer, but it requires a more complex network infrastructure.

### 7.2 More precise metrics

The Slowloris probing mechanism could be improved by increasing the number of simultaneous probes and starting them at the beginning of the test, before the slow connections are opened. This would make it possible to capture the temporal evolution of service degradation (see Section 5.3).

### 7.3 Additional mitigations

- **Nginx as a reverse proxy**: limits connections per IP at the HTTP server level, before requests even reach Flask.
- **fail2ban**: automatic detection and blocking of IPs based on access logs.
- **CDN / WAF** (e.g. Cloudflare): absorbs volume-based attacks upstream of the origin server.
- **Global rate limiting**: a limit on the total number of requests per second (all IPs combined) would be more effective against a multi-source DDoS.

### 7.4 More realistic scenarios

Testing from a separate machine (local network or VPN) would make it possible to apply a more realistic load to the server without sharing the host machine's CPU resources with the attacker.

---

## Conclusion

This project enabled the simulation and quantitative measurement of the impact of three types of DoS/DDoS attacks on a containerized Flask web server. The results show that hardware resources (CPU, RAM) significantly influence resistance to an HTTP Flood, with a 43% improvement in latency when moving from 0.25 to 0.5 CPU. However, a plateau appears at 1.0 CPU, revealing an architectural bottleneck (the number of Gunicorn workers).

The Slowloris attack illustrates that an architectural vulnerability can be independent of hardware resources, while the multi-source DDoS simulation demonstrates the limits of IP-based mitigations.

Rate limiting proves to be a very effective countermeasure against a single-source attacker (97–99% blocking), but insufficient against a distributed DDoS. These results confirm that there is no single solution: defense in depth, combining several complementary mechanisms, is essential to protect the availability of a service against denial-of-service attacks.

---

## References

[1] OWASP, *Denial of Service Cheat Sheet*, available at: https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html (accessed June 2026).

[2] Cloudflare, *What is a DDoS Attack?*, available at: https://www.cloudflare.com/learning/ddos/what-is-a-ddos-attack/ (accessed June 2026).

[3] RSnake (R. Hansen), *Slowloris HTTP DoS*, 2009, available at: https://web.archive.org/web/20150315054838/http://ha.ckers.org/slowloris/ (accessed June 2026).

[4] GitHub, *February 28 DDoS Incident Report*, 2018, available at: https://github.blog/2018-03-01-ddos-incident-report/ (accessed June 2026).

[5] AWS, *AWS Shield Threat Landscape Report Q1 2020*, available at: https://aws-shield-tlr.s3.amazonaws.com/2020-Q1_AWS_Shield_TLR.pdf (accessed June 2026).

[6] Flask-Limiter, *Official documentation*, available at: https://flask-limiter.readthedocs.io/ (accessed June 2026).

[7] CERT.org / CISA, *Understanding Denial-of-Service Attacks*, available at: https://www.cisa.gov/news-events/news/understanding-denial-service-attacks (accessed June 2026).

[8] Scapy Project, *Scapy documentation*, available at: https://scapy.readthedocs.io/ (accessed June 2026).