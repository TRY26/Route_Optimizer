"""
Unit and Integration Tests for AIQON Route Optimization System.
"""

import unittest
from src.data_generator import generate_synthetic_dataset
from src.optimizer import RouteOptimizer
from src.models import DEFAULT_PROFILES, RouteOption, RouteLeg
from src.explainer import RouteExplainer
from src.evaluation import SystemEvaluator


class TestRouteOptimizerSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.shipments = generate_synthetic_dataset(num_shipments=10, seed=123)
        cls.optimizer = RouteOptimizer(monte_carlo_runs=200, random_seed=42)

    def test_synthetic_data_generation(self):
        self.assertEqual(len(self.shipments), 10)
        for s in self.shipments:
            self.assertTrue(s.shipment_id.startswith("SHP-"))
            self.assertGreaterEqual(len(s.routes), 3)
            self.assertLessEqual(len(s.routes), 5)
            for r in s.routes:
                self.assertGreater(r.total_cost_usd, 0)
                self.assertGreater(r.estimated_transit_time_days, 0)
                self.assertGreater(len(r.legs), 0)
                self.assertTrue(0 <= r.delay_probability <= 1)
                self.assertTrue(0 <= r.geopolitical_risk <= 1)

    def test_optimization_and_ranking(self):
        s = self.shipments[0]
        res = self.optimizer.evaluate_shipment(s, profile=DEFAULT_PROFILES["balanced"])

        self.assertIsNotNone(res.recommended)
        self.assertIsNotNone(res.runner_up)
        self.assertEqual(res.recommended.rank, 1)
        self.assertEqual(res.runner_up.rank, 2)
        self.assertEqual(len(res.all_evaluations), len(s.routes))

        # Check score validity
        for ev in res.all_evaluations:
            self.assertTrue(0 <= ev.weighted_utility_score <= 1.0)
            self.assertTrue(0 <= ev.topsis_closeness <= 1.0)
            self.assertGreaterEqual(ev.simulated_p95_days, ev.simulated_expected_days)

    def test_pareto_dominance(self):
        # Construct synthetic routes where Route A strictly dominates Route B
        r_a = RouteOption(
            route_id="A",
            name="Dominant Route",
            strategy_type="Direct",
            legs=[],
            total_cost_usd=1000,
            estimated_transit_time_days=10,
            delay_probability=0.1,
            congestion_risk=0.1,
            geopolitical_risk=0.1,
            weather_risk=0.1,
            carbon_emissions_kg=100,
            composite_risk_score=0.1,
        )
        r_b = RouteOption(
            route_id="B",
            name="Dominated Route",
            strategy_type="Suboptimal",
            legs=[],
            total_cost_usd=2000,
            estimated_transit_time_days=20,
            delay_probability=0.3,
            congestion_risk=0.3,
            geopolitical_risk=0.3,
            weather_risk=0.3,
            carbon_emissions_kg=200,
            composite_risk_score=0.3,
        )

        flags = self.optimizer._compute_pareto_frontier([r_a, r_b])
        self.assertTrue(flags["A"])
        self.assertFalse(flags["B"])

    def test_explainer_output(self):
        s = self.shipments[1]
        res = self.optimizer.evaluate_shipment(s, profile=DEFAULT_PROFILES["balanced"])
        expl = RouteExplainer.generate_explanation(res)

        self.assertIn("executive_summary", expl)
        self.assertIn("trade_off_breakdown", expl)
        self.assertIn("alternatives_reviewed", expl)
        self.assertTrue(len(expl["executive_summary"]) > 10)

        # Markdown report rendering
        md = RouteExplainer.format_markdown_report(res)
        self.assertIn("Shipment Route Recommendation", md)
        self.assertIn("Freight Cost", md)

    def test_system_evaluator(self):
        evaluator = SystemEvaluator(self.optimizer)
        report = evaluator.evaluate_dataset(self.shipments, profile=DEFAULT_PROFILES["balanced"])

        self.assertEqual(report["total_shipments_evaluated"], 10)
        self.assertGreaterEqual(report["pareto_optimality_rate"], 80.0)
        self.assertIn("vs_greedy_cheapest", report["heuristic_comparisons"])
        self.assertIn("decision_stability_index", report)


if __name__ == "__main__":
    unittest.main()
