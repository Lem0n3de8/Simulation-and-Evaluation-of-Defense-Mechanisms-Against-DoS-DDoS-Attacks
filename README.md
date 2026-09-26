# Simulating and Evaluating Defense Mechanisms Against DoS/DDoS Attacks

A Python-based simulation to evaluate Layer 7 DoS/DDoS attacks and comparing mitigation strategies in a controlled Docker environment.

## Overview

This project evaluates the impact of several denial-of-service attacks against a Flask web server deployed inside Docker containers with configurable CPU and memory limits.

The implemented attacks are:
- HTTP Flood
- Slowloris
- Simulated distributed HTTP Flood (multi-process DDoS)

The project also evaluates the effectiveness of per-IP rate limiting using Flask-Limiter.

## Experimental Setup

| Component        | Implementation   |
| ---------------- | ---------------- |
| Target Server    | Flask + Gunicorn |
| Containerization | Docker           |
| Attack Script    | Python           |
| Mitigation       | Flask Limiter    |
| Visualization    | Matplotlib       |


## Repository Structure

```text
.
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
├── benchmark.py
├── visualize.py
├── report-en.pdf
├── report-fr.pdf
├── README.md
└── requirements.txt
```

## Installation
> ⚠️ You should have docker installed on your machine

```bash
# clone repository
git clone https://github.com/Lem0n3de8/Simulation-and-Evaluation-of-Defense-Mechanisms-Against-DoS-DDoS-Attacks
````
```bash
# switch to directory
cd Simulation-and-Evaluation-of-Defense-Mechanisms-Against-DoS-DDoS-Attacks
```

```bash
#create python environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Once you have the project and dependencies, you can run the benchmark by running the following command from the directory

```bash
python benchmark.py
```

Wait for the whole project to run.
You can find the raw results in `/results/`.

The graphs are in `/results/graphs/`. You can generate them using

```bash
python vizualize.py
```

## Report

The complete project report is available in `report-en.pdf` and in `report-fr.pdf`.