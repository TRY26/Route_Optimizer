"""
Multi-Criteria Optimization & Decision Engine for Shipment Route Selection.
Implements:
1. Multi-Attribute Utility Theory (MAUT) with Min-Max Score Normalization
2. TOPSIS (Technique for Order Preference by Similarity to Ideal Solution)
3. Pareto Dominance Frontier Filtering
4. Monte Carlo Simulation for Operational Uncertainty (P50, P95, On-Time Probability)
5. Parameter Sensitivity & Weight Robustness Analysis
"""

import math
import random
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from .models import RouteOption, Shipment, PriorityProfile, DEFAULT_PROFILES


@dataclass
class RouteEvaluation:
    route: RouteOption
    normalized_scores: Dict[str, float]  # 0 to 1, where 1.0 is best
    weighted_utility_score: float        # MAUT score
    topsis_closeness: float              # TOPSIS score
    is_pareto_optimal: bool              # True if not dominated on cost, time, and risk
    simulated_expected_days: float       # Monte Carlo mean
    simulated_p95_days: float            # 95th percentile transit time
    on_time_probability: float           # Prob(arrival <= target)
    rank: int = 1


@dataclass
class RecommendationResult:
    shipment_id: str
    origin: str
    destination: str
    corridor: str
    profile_used: PriorityProfile
    recommended: RouteEvaluation
    runner_up: Optional[RouteEvaluation]
    all_evaluations: List[RouteEvaluation]
    pareto_frontier_route_ids: List[str]
    trade_off_analysis: Dict[str, Any]


class RouteOptimizer:
    """
    Core algorithmic engine for evaluating and ranking logistics routes.
    """

    def __init__(self, monte_carlo_runs: int = 1000, random_seed: int = 42):
        self.monte_carlo_runs = monte_carlo_runs
        self.random_seed = random_seed

    def evaluate_shipment(
        self,
        shipment: Shipment,
        profile: Optional[PriorityProfile] = None,
        custom_weights: Optional[Dict[str, float]] = None,
    ) -> RecommendationResult:
        """
        Evaluates all route options for a shipment and returns a comprehensive recommendation.
        """
        routes = shipment.routes
        if not routes:
            raise ValueError(f"Shipment {shipment.shipment_id} has no route options.")

        # Determine active profile / weights
        if custom_weights:
            active_profile = PriorityProfile(
                name="Custom User Profile",
                description="Custom user-defined weighting configuration",
                weight_cost=custom_weights.get("cost", 0.3),
                weight_time=custom_weights.get("time", 0.3),
                weight_delay_risk=custom_weights.get("delay_risk", 0.2),
                weight_geopolitical_risk=custom_weights.get("geopolitical_risk", 0.15),
                weight_carbon=custom_weights.get("carbon", 0.05),
            )
        elif profile is not None:
            active_profile = profile
        else:
            # Automatic profile selection based on cargo type and priority
            active_profile = self._infer_default_profile(shipment)

        weights = active_profile.normalized_weights()

        # 1. Pareto Frontier Identification
        pareto_flags = self._compute_pareto_frontier(routes)

        # 2. Monte Carlo Uncertainty Simulation
        mc_results = self._run_monte_carlo(routes, target_days=shipment.target_delivery_days)

        # 3. Normalization (Min-Max where 1.0 is best performance)
        norm_scores = self._normalize_metrics(routes)

        # 4. TOPSIS Analysis
        topsis_scores = self._compute_topsis(routes, weights)

        # 5. Composite MAUT Utility Score
        evaluations: List[RouteEvaluation] = []
        for idx, r in enumerate(routes):
            r_id = r.route_id
            ns = norm_scores[r_id]

            # Weighted utility: sum(weight_j * norm_score_j)
            utility = (
                weights["cost"] * ns["cost"]
                + weights["time"] * ns["time"]
                + weights["delay_risk"] * ns["delay_risk"]
                + weights["geopolitical_risk"] * ns["geopolitical_risk"]
                + weights["carbon"] * ns["carbon"]
            )

            mc = mc_results[r_id]

            eval_item = RouteEvaluation(
                route=r,
                normalized_scores=ns,
                weighted_utility_score=round(utility, 4),
                topsis_closeness=round(topsis_scores[r_id], 4),
                is_pareto_optimal=pareto_flags[r_id],
                simulated_expected_days=mc["expected_days"],
                simulated_p95_days=mc["p95_days"],
                on_time_probability=mc["on_time_probability"],
            )
            evaluations.append(eval_item)

        # Rank routes primarily by combined decision metric (blending MAUT and TOPSIS)
        # Decision Score = 0.5 * MAUT + 0.5 * TOPSIS
        evaluations.sort(
            key=lambda ev: (0.5 * ev.weighted_utility_score + 0.5 * ev.topsis_closeness),
            reverse=True,
        )

        for rank, ev in enumerate(evaluations, start=1):
            ev.rank = rank

        recommended = evaluations[0]
        runner_up = evaluations[1] if len(evaluations) > 1 else None

        pareto_ids = [r.route_id for r in routes if pareto_flags[r.route_id]]

        trade_off_analysis = self._analyze_trade_offs(recommended, runner_up)

        return RecommendationResult(
            shipment_id=shipment.shipment_id,
            origin=shipment.origin,
            destination=shipment.destination,
            corridor=shipment.corridor,
            profile_used=active_profile,
            recommended=recommended,
            runner_up=runner_up,
            all_evaluations=evaluations,
            pareto_frontier_route_ids=pareto_ids,
            trade_off_analysis=trade_off_analysis,
        )

    def _infer_default_profile(self, shipment: Shipment) -> PriorityProfile:
        """Infers an intelligent default business profile based on shipment traits."""
        cargo_str = str(shipment.cargo_type)
        if "Perishable" in cargo_str or shipment.priority_level == "Critical":
            return DEFAULT_PROFILES["speed_first"]
        elif "High-Value" in cargo_str or "Pharma" in cargo_str:
            return DEFAULT_PROFILES["risk_averse"]
        elif "Bulk" in cargo_str:
            return DEFAULT_PROFILES["cost_saver"]
        else:
            return DEFAULT_PROFILES["balanced"]

    def _compute_pareto_frontier(self, routes: List[RouteOption]) -> Dict[str, bool]:
        """
        Determines Pareto dominance in 3 core dimensions (cost, time, composite risk).
        All 3 are minimization objectives.
        A route A dominates B (A > B) if A <= B on all 3, and A < B on at least one.
        A route is Pareto optimal if no other route dominates it.
        """
        is_pareto: Dict[str, bool] = {r.route_id: True for r in routes}

        for i, r_a in enumerate(routes):
            for j, r_b in enumerate(routes):
                if i == j:
                    continue
                # Check if r_b dominates r_a
                # r_b is better (smaller or equal) in all metrics
                cost_b_le_a = r_b.total_cost_usd <= r_a.total_cost_usd
                time_b_le_a = r_b.estimated_transit_time_days <= r_a.estimated_transit_time_days
                risk_b_le_a = r_b.composite_risk_score <= r_a.composite_risk_score

                strictly_better = (
                    r_b.total_cost_usd < r_a.total_cost_usd
                    or r_b.estimated_transit_time_days < r_a.estimated_transit_time_days
                    or r_b.composite_risk_score < r_a.composite_risk_score
                )

                if cost_b_le_a and time_b_le_a and risk_b_le_a and strictly_better:
                    is_pareto[r_a.route_id] = False
                    break

        return is_pareto

    def _normalize_metrics(self, routes: List[RouteOption]) -> Dict[str, Dict[str, float]]:
        """
        Min-Max normalization inverted so that 1.0 represents the most desirable
        (lowest cost, shortest time, lowest risk, lowest carbon) and 0.0 is least desirable.
        """
        costs = [r.total_cost_usd for r in routes]
        times = [r.estimated_transit_time_days for r in routes]
        delay_risks = [r.delay_probability for r in routes]
        geo_risks = [r.geopolitical_risk for r in routes]
        carbons = [r.carbon_emissions_kg for r in routes]

        def get_min_max(vals):
            min_v, max_v = min(vals), max(vals)
            span = max_v - min_v
            return min_v, max_v, span if span > 1e-9 else 1.0

        c_min, c_max, c_span = get_min_max(costs)
        t_min, t_max, t_span = get_min_max(times)
        d_min, d_max, d_span = get_min_max(delay_risks)
        g_min, g_max, g_span = get_min_max(geo_risks)
        cb_min, cb_max, cb_span = get_min_max(carbons)

        normalized = {}
        for r in routes:
            # Score = (Max - Value) / Span -> 1.0 is lowest/best, 0.0 is highest/worst
            normalized[r.route_id] = {
                "cost": round((c_max - r.total_cost_usd) / c_span, 4),
                "time": round((t_max - r.estimated_transit_time_days) / t_span, 4),
                "delay_risk": round((d_max - r.delay_probability) / d_span, 4),
                "geopolitical_risk": round((g_max - r.geopolitical_risk) / g_span, 4),
                "carbon": round((cb_max - r.carbon_emissions_kg) / cb_span, 4),
            }
        return normalized

    def _compute_topsis(self, routes: List[RouteOption], weights: Dict[str, float]) -> Dict[str, float]:
        """
        Technique for Order Preference by Similarity to Ideal Solution (TOPSIS).
        All 5 attributes are cost attributes (lower is better).
        """
        keys = ["cost", "time", "delay_risk", "geopolitical_risk", "carbon"]

        raw_matrix = {}
        for r in routes:
            raw_matrix[r.route_id] = {
                "cost": r.total_cost_usd,
                "time": r.estimated_transit_time_days,
                "delay_risk": r.delay_probability,
                "geopolitical_risk": r.geopolitical_risk,
                "carbon": r.carbon_emissions_kg,
            }

        # Vector normalization denominators: sqrt(sum(x_ij^2))
        denominators = {}
        for k in keys:
            sum_sq = sum(raw_matrix[r.route_id][k] ** 2 for r in routes)
            denominators[k] = math.sqrt(sum_sq) if sum_sq > 0 else 1.0

        # Weighted normalized matrix
        weighted_norm = {}
        for r in routes:
            r_id = r.route_id
            weighted_norm[r_id] = {}
            for k in keys:
                r_ij = raw_matrix[r_id][k] / denominators[k]
                weighted_norm[r_id][k] = r_ij * weights[k]

        # Ideal best (A*) is MIN value for cost criteria
        # Ideal worst (A-) is MAX value for cost criteria
        ideal_best = {k: min(weighted_norm[r.route_id][k] for r in routes) for k in keys}
        ideal_worst = {k: max(weighted_norm[r.route_id][k] for r in routes) for k in keys}

        # Separation distances
        closeness_scores = {}
        for r in routes:
            r_id = r.route_id
            dist_best = math.sqrt(
                sum((weighted_norm[r_id][k] - ideal_best[k]) ** 2 for k in keys)
            )
            dist_worst = math.sqrt(
                sum((weighted_norm[r_id][k] - ideal_worst[k]) ** 2 for k in keys)
            )

            total_dist = dist_best + dist_worst
            if total_dist == 0:
                closeness = 0.5
            else:
                closeness = dist_worst / total_dist
            closeness_scores[r_id] = round(closeness, 4)

        return closeness_scores

    def _run_monte_carlo(
        self, routes: List[RouteOption], target_days: Optional[float] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Simulates 1,000 operational journeys per route to account for stochastic delays:
        - Port dwell times and queueing
        - Weather disruption impact
        - Geopolitical shock diversion risk (e.g. Suez closure diversion to Cape)
        """
        rng = random.Random(self.random_seed)
        results = {}

        for r in routes:
            simulated_durations = []
            base_time = r.estimated_transit_time_days

            for _ in range(self.monte_carlo_runs):
                duration = base_time

                # Stochastic delay event check
                if rng.random() < r.delay_probability:
                    # Delay duration follows log-normal shape influenced by port congestion
                    delay_days = rng.lognormvariate(
                        mu=math.log(max(1.0, 3.5 * r.congestion_risk + 1.0)),
                        sigma=0.45,
                    )
                    duration += delay_days

                # Weather surge disruption
                if rng.random() < (r.weather_risk * 0.4):
                    weather_delay = rng.uniform(1.0, 4.0)
                    duration += weather_delay

                # Geopolitical shock disruption (e.g. vessel stoppage or Cape diversion)
                if r.geopolitical_risk > 0.40 and rng.random() < (r.geopolitical_risk * 0.15):
                    geo_delay = rng.uniform(4.0, 11.0)
                    duration += geo_delay

                simulated_durations.append(duration)

            simulated_durations.sort()
            n = len(simulated_durations)
            expected = sum(simulated_durations) / n
            p50 = simulated_durations[int(0.50 * n)]
            p95 = simulated_durations[int(0.95 * n)]

            # On-time probability calculation
            if target_days:
                on_time_count = sum(1 for d in simulated_durations if d <= target_days)
                on_time_prob = round(on_time_count / n, 3)
            else:
                # Default benchmark against base_time + 20%
                on_time_benchmark = base_time * 1.20
                on_time_count = sum(1 for d in simulated_durations if d <= on_time_benchmark)
                on_time_prob = round(on_time_count / n, 3)

            results[r.route_id] = {
                "expected_days": round(expected, 1),
                "p50_days": round(p50, 1),
                "p95_days": round(p95, 1),
                "on_time_probability": on_time_prob,
            }

        return results

    def _analyze_trade_offs(
        self, rec: RouteEvaluation, runner_up: Optional[RouteEvaluation]
    ) -> Dict[str, Any]:
        """Calculates precise numerical trade-offs between winner and runner-up."""
        if not runner_up:
            return {"status": "Only one option available"}

        r1 = rec.route
        r2 = runner_up.route

        cost_diff = round(r1.total_cost_usd - r2.total_cost_usd, 2)
        cost_diff_pct = round((cost_diff / r2.total_cost_usd) * 100, 1)

        time_diff = round(r1.estimated_transit_time_days - r2.estimated_transit_time_days, 1)
        time_diff_pct = round((time_diff / r2.estimated_transit_time_days) * 100, 1)

        delay_risk_diff = round(r1.delay_probability - r2.delay_probability, 3)
        geo_risk_diff = round(r1.geopolitical_risk - r2.geopolitical_risk, 3)
        p95_diff = round(rec.simulated_p95_days - runner_up.simulated_p95_days, 1)

        return {
            "winner_id": r1.route_id,
            "runner_up_id": r2.route_id,
            "cost_diff_usd": cost_diff,
            "cost_diff_pct": cost_diff_pct,
            "time_diff_days": time_diff,
            "time_diff_pct": time_diff_pct,
            "delay_risk_diff": delay_risk_diff,
            "geo_risk_diff": geo_risk_diff,
            "p95_diff_days": p95_diff,
            "on_time_prob_diff": round(rec.on_time_probability - runner_up.on_time_probability, 3),
        }

    def run_sensitivity_analysis(
        self, shipment: Shipment, active_profile: PriorityProfile
    ) -> Dict[str, Any]:
        """
        Tests stability of recommendation by perturbing criteria weights from 0.05 to 0.80.
        Identifies weight flipping thresholds where the top choice changes.
        """
        base_weights = active_profile.normalized_weights()
        base_rec = self.evaluate_shipment(shipment, profile=active_profile).recommended.route.route_id

        sensitivities = {}
        criteria = ["cost", "time", "delay_risk", "geopolitical_risk"]

        for crit in criteria:
            flips = []
            test_weights_values = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85]

            for w_val in test_weights_values:
                # Re-distribute remaining weight proportionally
                remaining = 1.0 - w_val
                other_sum = sum(base_weights[c] for c in criteria if c != crit)
                test_weights = {}
                for c in criteria:
                    if c == crit:
                        test_weights[c] = w_val
                    else:
                        test_weights[c] = (
                            (base_weights[c] / other_sum) * remaining
                            if other_sum > 0
                            else remaining / (len(criteria) - 1)
                        )
                test_weights["carbon"] = 0.0

                test_res = self.evaluate_shipment(shipment, custom_weights=test_weights)
                top_id = test_res.recommended.route.route_id

                if top_id != base_rec:
                    flips.append({
                        "weight_value": w_val,
                        "new_winner_id": top_id,
                        "new_winner_name": test_res.recommended.route.name,
                    })

            sensitivities[crit] = {
                "base_weight": round(base_weights[crit], 2),
                "is_stable": len(flips) == 0,
                "flips": flips,
            }

        return {
            "base_recommended_id": base_rec,
            "criteria_sensitivity": sensitivities,
        }
