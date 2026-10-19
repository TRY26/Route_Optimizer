# Aiqon Route Optimizer: Multi-Objective Decision Support System

> **AI Internship Assignment** — Optimizing Shipment Routes Under Cost, Time, and Risk Constraints  
> Designed and built for **Aiqon** (`info@aiqon.in`)

---

## 📌 Executive Overview

In global logistics, route selection is fundamentally a multi-criteria decision-making (MCDM) problem under uncertainty. A cheaper route often involves severe transshipment dwell delays; a faster route frequently passes through hazardous geopolitical choke points (e.g., Red Sea / Bab-el-Mandeb Strait) or congested gateways (e.g., Los Angeles / Long Beach).

This system provides:
1. **Realistic Synthetic Data Generation Engine**: Simulates 35 real-world international trade corridors with multi-leg journeys and concrete trade-offs (Direct Ocean, Chokepoint Ocean, Geopolitical Bypass, Transshipment Economy, Rail Multimodal, Air Urgent).
2. **Multi-Objective Optimization Engine**:
   - **Normalized Multi-Attribute Utility Theory (MAUT)** with customizable business priority profiles.
   - **TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)**.
   - **Pareto Dominance Frontier Analysis** (guarantees non-dominated proposals).
   - **Stochastic Monte Carlo Simulation (1,000 iterations)** to model delay distributions, weather shocks, and 95th-percentile transit times ($P_{95}$ SLA buffer).
3. **Logistics-Operator Decision Explainability (XAI)**: Generates structured plain-English justifications quantifying exact cost/time/risk trade-offs against runner-ups, risk disqualification rationale, and sensitivity thresholds.
4. **Interactive Local Web Dashboard**: Built with zero external dependencies (pure Python standard library + Tailwind/Chart.js frontend) featuring real-time radar charts, Pareto scatter plots, and Monte Carlo transit distributions.
5. **System Evaluation Suite**: Benchmarks recommendations against industry baseline heuristics (Greedy Cheapest, Greedy Fastest, Greedy Safest).

---

## 🚀 Quickstart Guide

The core system is implemented in **pure Python 3 (standard library)** with **zero mandatory external dependencies**—it runs immediately on macOS, Linux, or Windows without requiring `pip install`.

### 1. Run Unit & Integration Tests
```bash
python3 -m unittest discover -s tests
```

### 2. Generate / Inspect the Dataset
```bash
# Generate 35 realistic shipments with 129 multi-leg routes
python3 cli.py generate --count 35 --seed 42
```
Outputs:
- `data/shipments.json` (Structured JSON with full multi-leg breakdowns)
- `data/routes_flat.csv` (Flat CSV for spreadsheet inspection)

### 3. Get an Intelligent Route Recommendation
```bash
# Standard balanced logistics profile
python3 cli.py recommend --shipment SHP-001 --profile balanced

# Cost-saver economic profile (bulk / low-margin goods)
python3 cli.py recommend --shipment SHP-001 --profile cost_saver

# Speed-first profile (urgent / perishable cargo)
python3 cli.py recommend --shipment SHP-001 --profile speed_first

# Risk-averse profile (high-value electronics / pharma)
python3 cli.py recommend --shipment SHP-001 --profile risk_averse

# Output structured JSON for system integration
python3 cli.py recommend --shipment SHP-001 --json
```

### 4. Run Quantitative Benchmark Evaluation
```bash
python3 cli.py evaluate --profile balanced
```

### 5. Run Parameter Sensitivity & Robustness Analysis
```bash
python3 cli.py sensitivity --shipment SHP-001
```

### 6. Launch the Interactive Web Dashboard
```bash
python3 cli.py serve --port 8080
```
Open **`http://localhost:8080`** in any browser to interact with the visual dashboard, adjust criteria weight sliders in real time, inspect Pareto frontiers, and view multi-leg breakdowns.

---

## 📂 Repository Structure

```
aiqon-route-optimizer/
├── src/
│   ├── models.py           # Domain models: Shipment, RouteOption, RouteLeg, PriorityProfile
│   ├── data_generator.py   # Realistic synthetic trade lane and multi-leg route generator
│   ├── optimizer.py        # Optimization engine: MAUT, TOPSIS, Pareto filtering, Monte Carlo
│   ├── explainer.py        # Decision Explainability: Natural language summaries & trade-offs
│   └── evaluation.py       # Benchmark evaluation against greedy heuristics & stability tests
├── web/
│   ├── server.py           # Standard library REST API server
│   └── index.html          # Modern Tailwind + Chart.js interactive dashboard
├── data/
│   ├── shipments.json      # Pre-generated 35 shipments (129 routes)
│   └── routes_flat.csv     # Tabular CSV export
├── tests/
│   ├── test_system.py      # Unit tests for core algorithms
│   └── test_server.py      # Handler logic tests
├── cli.py                  # Unified Command Line Interface
├── REPORT.md               # Complete 2-3 page technical report for submission
└── README.md               # Project documentation (this file)
```

---

## 📊 Business Priority Profiles

The optimizer includes 5 pre-configured supply chain profiles:

| Profile | Target Cargo / Context | Cost Weight | Time Weight | Delay Risk | Geo Risk | Carbon |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Balanced Logistics** | General merchandise | 30% | 30% | 20% | 15% | 5% |
| **Cost Saver** | High-volume industrial, low urgency | 60% | 15% | 15% | 8% | 2% |
| **Speed First** | Perishables, critical assembly parts | 10% | 60% | 15% | 10% | 5% |
| **Risk Averse** | High-value electronics, pharmaceuticals | 15% | 15% | 35% | 30% | 5% |
| **Eco-Conscious** | Green corporate supply chains | 25% | 20% | 15% | 10% | 30% |

Users can also define arbitrary custom weights via `--profile custom` or the web dashboard sliders.

---

## 📈 Evaluation Results Summary

Benchmarking against 35 international trade corridors reveals:
- **100.0% Pareto Optimality Rate**: 100% of recommended routes reside strictly on the non-dominated Pareto frontier.
- **97.1% Decision Stability Index**: Decisions remain invariant under $\pm 8\%$ stochastic input perturbations.
- **vs. Greedy Cheapest Baseline**: Saves **9.5 days (-41.5% lead time)** and reduces operational delay risk by **45.9%** for a justified freight premium.
- **vs. Greedy Fastest Baseline**: Captures **$43,408 (70.1%) capital savings** compared to naive charter air freight while incurring only a modest transit time addition.
