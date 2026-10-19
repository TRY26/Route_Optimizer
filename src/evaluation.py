"""
Evaluation and Benchmarking Framework for Route Optimization.
Assesses decision quality against industry baseline heuristics:
1. Greedy Cheapest (Cost Minimizer)
2. Greedy Fastest (Time Minimizer)
3. Greedy Safest (Risk Minimizer)
4. Random Baseline
Measures Pareto optimality rates, trade-off efficiency, and decision robustness under input noise.
"""

import random
from typing import List, Dict, Any
from .models import Shipment, PriorityProfile, DEFAULT_PROFILES
from .optimizer import RouteOptimizer


class SystemEvaluator:
    """
    Evaluates recommendation quality across a full shipment testbed.
    """

    def __init__(self, optimizer: RouteOptimizer):
        self.optimizer = optimizer

    def evaluate_dataset(
        self, shipments: List[Shipment], profile: PriorityProfile = DEFAULT_PROFILES["balanced"]
    ) -> Dict[str, Any]:
        """
        Runs comprehensive benchmark across all shipments in dataset.
        """
        total_shipments = len(shipments)
        if total_shipments == 0:
            return {"error": "Empty shipment dataset"}

        # Track cumulative metrics
        sys_costs, sys_times, sys_risks, sys_p95s = [], [], [], []
        cheap_costs, cheap_times, cheap_risks = [], [], []
        fast_costs, fast_times, fast_risks = [], [], []
        safe_costs, safe_times, safe_risks = [], [], []

        pareto_count = 0
        decisions_summary = []

        for s in shipments:
            # 1. System Recommendation
            res = self.optimizer.evaluate_shipment(s, profile=profile)
            rec = res.recommended
            r_rec = rec.route

            sys_costs.append(r_rec.total_cost_usd)
            sys_times.append(r_rec.estimated_transit_time_days)
            sys_risks.append(r_rec.composite_risk_score)
            sys_p95s.append(rec.simulated_p95_days)

            if rec.is_pareto_optimal:
                pareto_count += 1

            # 2. Greedy Baselines
            cheapest = min(s.routes, key=lambda r: r.total_cost_usd)
            fastest = min(s.routes, key=lambda r: r.estimated_transit_time_days)
            safest = min(s.routes, key=lambda r: r.composite_risk_score)

            cheap_costs.append(cheapest.total_cost_usd)
            cheap_times.append(cheapest.estimated_transit_time_days)
            cheap_risks.append(cheapest.composite_risk_score)

            fast_costs.append(fastest.total_cost_usd)
            fast_times.append(fastest.estimated_transit_time_days)
            fast_risks.append(fastest.composite_risk_score)

            safe_costs.append(safest.total_cost_usd)
            safe_times.append(safest.estimated_transit_time_days)
            safe_risks.append(safest.composite_risk_score)

            decisions_summary.append({
                "shipment_id": s.shipment_id,
                "corridor": s.corridor,
                "recommended": r_rec.name,
                "cost": r_rec.total_cost_usd,
                "time": r_rec.estimated_transit_time_days,
                "risk": r_rec.composite_risk_score,
                "is_pareto": rec.is_pareto_optimal,
            })

        avg = lambda vals: sum(vals) / len(vals)

        # Baseline comparisons
        avg_sys_cost = avg(sys_costs)
        avg_cheap_cost = avg(cheap_costs)
        avg_fast_cost = avg(fast_costs)

        avg_sys_time = avg(sys_times)
        avg_cheap_time = avg(cheap_times)
        avg_fast_time = avg(fast_times)

        avg_sys_risk = avg(sys_risks)
        avg_cheap_risk = avg(cheap_risks)
        avg_safe_risk = avg(safe_risks)

        # Robustness test
        robustness_score = self._test_decision_stability(shipments, profile)

        return {
            "total_shipments_evaluated": total_shipments,
            "profile_tested": profile.name,
            "pareto_optimality_rate": round((pareto_count / total_shipments) * 100, 1),
            "system_averages": {
                "avg_cost_usd": round(avg_sys_cost, 2),
                "avg_transit_days": round(avg_sys_time, 1),
                "avg_composite_risk": round(avg_sys_risk, 3),
                "avg_p95_buffer_days": round(avg(sys_p95s), 1),
            },
            "heuristic_comparisons": {
                "vs_greedy_cheapest": {
                    "cost_premium_usd": round(avg_sys_cost - avg_cheap_cost, 2),
                    "cost_premium_pct": round(((avg_sys_cost - avg_cheap_cost) / avg_cheap_cost) * 100, 1),
                    "transit_time_saved_days": round(avg_cheap_time - avg_sys_time, 1),
                    "transit_time_saved_pct": round(((avg_cheap_time - avg_sys_time) / avg_cheap_time) * 100, 1),
                    "risk_reduction_pct": round(((avg_cheap_risk - avg_sys_risk) / avg_cheap_risk) * 100, 1),
                },
                "vs_greedy_fastest": {
                    "cost_saved_usd": round(avg_fast_cost - avg_sys_cost, 2),
                    "cost_saved_pct": round(((avg_fast_cost - avg_sys_cost) / avg_fast_cost) * 100, 1),
                    "transit_time_delta_days": round(avg_sys_time - avg_fast_time, 1),
                },
                "vs_greedy_safest": {
                    "cost_delta_usd": round(avg_sys_cost - avg(safe_costs), 2),
                    "risk_delta": round(avg_sys_risk - avg_safe_risk, 3),
                },
            },
            "decision_stability_index": robustness_score,
            "sample_decisions": decisions_summary[:5],
        }

    def _test_decision_stability(
        self, shipments: List[Shipment], profile: PriorityProfile, noise_level: float = 0.08
    ) -> float:
        """
        Tests how often the recommended route remains unchanged when inputs are subjected
        to random jitter (+/- 8% cost, time, and risk perturbation).
        """
        rng = random.Random(1234)
        consistent_count = 0

        for s in shipments:
            base_rec = self.optimizer.evaluate_shipment(s, profile=profile).recommended.route.route_id

            # Perturb routes slightly
            perturbed_routes = []
            for r in s.routes:
                factor_c = 1.0 + rng.uniform(-noise_level, noise_level)
                factor_t = 1.0 + rng.uniform(-noise_level, noise_level)
                factor_r = 1.0 + rng.uniform(-noise_level, noise_level)

                # Clone route with slight noise
                r_perturbed = type(r)(
                    route_id=r.route_id,
                    name=r.name,
                    strategy_type=r.strategy_type,
                    legs=r.legs,
                    total_cost_usd=round(r.total_cost_usd * factor_c, 2),
                    estimated_transit_time_days=round(r.estimated_transit_time_days * factor_t, 1),
                    delay_probability=round(min(0.99, max(0.01, r.delay_probability * factor_r)), 3),
                    congestion_risk=round(min(0.99, max(0.01, r.congestion_risk * factor_r)), 3),
                    geopolitical_risk=r.geopolitical_risk,
                    weather_risk=r.weather_risk,
                    carbon_emissions_kg=r.carbon_emissions_kg,
                    composite_risk_score=round(min(0.99, max(0.01, r.composite_risk_score * factor_r)), 3),
                    intermediate_nodes=r.intermediate_nodes,
                    description=r.description,
                )
                perturbed_routes.append(r_perturbed)

            s_copy = Shipment(
                shipment_id=s.shipment_id,
                origin=s.origin,
                origin_country=s.origin_country,
                destination=s.destination,
                destination_country=s.destination_country,
                corridor=s.corridor,
                cargo_type=s.cargo_type,
                cargo_weight_kg=s.cargo_weight_kg,
                cargo_value_usd=s.cargo_value_usd,
                priority_level=s.priority_level,
                max_budget_usd=s.max_budget_usd,
                target_delivery_days=s.target_delivery_days,
                routes=perturbed_routes,
            )

            noisy_rec = self.optimizer.evaluate_shipment(s_copy, profile=profile).recommended.route.route_id
            if noisy_rec == base_rec:
                consistent_count += 1

        return round((consistent_count / len(shipments)) * 100, 1)
