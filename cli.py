"""
Command-Line Interface (CLI) for AIQON Route Optimization System.
"""

import argparse
import json
import os
import sys
from typing import List

from src.models import DEFAULT_PROFILES, Shipment, RouteOption, RouteLeg, CargoType
from src.data_generator import generate_synthetic_dataset, save_dataset_to_files
from src.optimizer import RouteOptimizer
from src.explainer import RouteExplainer
from src.evaluation import SystemEvaluator


def load_shipments(json_path: str = "data/shipments.json") -> List[Shipment]:
    """Loads shipments from JSON file and hydrates domain objects."""
    if not os.path.exists(json_path):
        print(f"Dataset not found at '{json_path}'. Generating default dataset...")
        os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
        shipments = generate_synthetic_dataset(num_shipments=35, seed=42)
        save_dataset_to_files(shipments, json_path, "data/routes_flat.csv")
        return shipments

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    shipments = []
    for item in data:
        routes = []
        for r_dict in item["routes"]:
            legs = [
                RouteLeg(
                    leg_id=l["leg_id"],
                    origin=l["origin"],
                    destination=l["destination"],
                    mode=l["mode"],
                    carrier_type=l["carrier_type"],
                    transit_time_days=l["transit_time_days"],
                    cost_usd=l["cost_usd"],
                    delay_prob=l["delay_prob"],
                    congestion_risk=l["congestion_risk"],
                    geopolitical_risk=l["geopolitical_risk"],
                    weather_risk=l["weather_risk"],
                    carbon_kg=l["carbon_kg"],
                    notes=l.get("notes", ""),
                )
                for l in r_dict.get("legs", [])
            ]
            route = RouteOption(
                route_id=r_dict["route_id"],
                name=r_dict["name"],
                strategy_type=r_dict["strategy_type"],
                legs=legs,
                total_cost_usd=r_dict["total_cost_usd"],
                estimated_transit_time_days=r_dict["estimated_transit_time_days"],
                delay_probability=r_dict["delay_probability"],
                congestion_risk=r_dict["congestion_risk"],
                geopolitical_risk=r_dict["geopolitical_risk"],
                weather_risk=r_dict["weather_risk"],
                carbon_emissions_kg=r_dict["carbon_emissions_kg"],
                composite_risk_score=r_dict["composite_risk_score"],
                intermediate_nodes=r_dict.get("intermediate_nodes", []),
                description=r_dict.get("description", ""),
            )
            routes.append(route)

        cargo_type = CargoType.GENERAL
        for ct in CargoType:
            if ct.value == item["cargo_type"] or ct.name == item["cargo_type"]:
                cargo_type = ct
                break

        s = Shipment(
            shipment_id=item["shipment_id"],
            origin=item["origin"],
            origin_country=item["origin_country"],
            destination=item["destination"],
            destination_country=item["destination_country"],
            corridor=item["corridor"],
            cargo_type=cargo_type,
            cargo_weight_kg=item["cargo_weight_kg"],
            cargo_value_usd=item["cargo_value_usd"],
            priority_level=item["priority_level"],
            max_budget_usd=item.get("max_budget_usd"),
            target_delivery_days=item.get("target_delivery_days"),
            routes=routes,
        )
        shipments.append(s)

    return shipments


def main():
    parser = argparse.ArgumentParser(
        description="AIQON: Intelligent Logistics Route Optimization System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: generate
    gen_p = subparsers.add_parser("generate", help="Generate synthetic logistics dataset")
    gen_p.add_argument("--count", type=int, default=35, help="Number of shipments to simulate")
    gen_p.add_argument("--seed", type=int, default=42, help="Deterministic random seed")

    # Command: recommend
    rec_p = subparsers.add_parser("recommend", help="Recommend optimal route for a shipment")
    rec_p.add_argument("--shipment", type=str, default="SHP-001", help="Shipment ID (e.g. SHP-001)")
    rec_p.add_argument(
        "--profile",
        type=str,
        default="balanced",
        choices=["balanced", "cost_saver", "speed_first", "risk_averse", "eco_conscious"],
        help="Business priority profile",
    )
    rec_p.add_argument("--json", action="store_true", help="Output raw JSON results")

    # Command: evaluate
    eval_p = subparsers.add_parser("evaluate", help="Benchmark optimizer against greedy heuristics")
    eval_p.add_argument(
        "--profile",
        type=str,
        default="balanced",
        choices=["balanced", "cost_saver", "speed_first", "risk_averse", "eco_conscious"],
    )

    # Command: sensitivity
    sens_p = subparsers.add_parser("sensitivity", help="Run weight sensitivity analysis")
    sens_p.add_argument("--shipment", type=str, default="SHP-001")
    sens_p.add_argument("--profile", type=str, default="balanced")

    # Command: serve
    serve_p = subparsers.add_parser("serve", help="Launch local interactive Web UI Dashboard")
    serve_p.add_argument("--port", type=int, default=8080, help="Web server port")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "generate":
        print(f"Generating {args.count} synthetic shipments (seed={args.seed})...")
        os.makedirs("data", exist_ok=True)
        shipments = generate_synthetic_dataset(num_shipments=args.count, seed=args.seed)
        save_dataset_to_files(shipments, "data/shipments.json", "data/routes_flat.csv")
        total_routes = sum(len(s.routes) for s in shipments)
        print(f"Created data/shipments.json & data/routes_flat.csv ({len(shipments)} shipments, {total_routes} routes).")

    elif args.command == "recommend":
        shipments = load_shipments()
        target = next((s for s in shipments if s.shipment_id.upper() == args.shipment.upper()), None)
        if not target:
            print(f"Error: Shipment '{args.shipment}' not found in dataset. Available IDs: {[s.shipment_id for s in shipments[:5]]}...")
            sys.exit(1)

        profile = DEFAULT_PROFILES.get(args.profile, DEFAULT_PROFILES["balanced"])
        optimizer = RouteOptimizer(monte_carlo_runs=1000)
        res = optimizer.evaluate_shipment(target, profile=profile)

        if args.json:
            expl = RouteExplainer.generate_explanation(res)
            print(json.dumps(expl, indent=2))
        else:
            md_report = RouteExplainer.format_markdown_report(res)
            print("\n" + "=" * 70)
            print(md_report)
            print("=" * 70 + "\n")

    elif args.command == "evaluate":
        shipments = load_shipments()
        profile = DEFAULT_PROFILES.get(args.profile, DEFAULT_PROFILES["balanced"])
        optimizer = RouteOptimizer(monte_carlo_runs=500)
        evaluator = SystemEvaluator(optimizer)
        report = evaluator.evaluate_dataset(shipments, profile=profile)

        print("\n" + "=" * 70)
        print(f"SYSTEM BENCHMARK EVALUATION [{report['profile_tested'].upper()}]")
        print("=" * 70)
        print(f"Total Shipments Evaluated: {report['total_shipments_evaluated']}")
        print(f"Pareto Optimality Rate:   {report['pareto_optimality_rate']}% of recommendations lie on Pareto Frontier")
        print(f"Decision Stability Index: {report['decision_stability_index']}% (robust to +/-8% input perturbations)")
        print("\n--- System Averages ---")
        for k, v in report["system_averages"].items():
            print(f"  {k:24}: {v}")
        print("\n--- Comparison Against Greedy Heuristics ---")
        vs_c = report["heuristic_comparisons"]["vs_greedy_cheapest"]
        print(f"  vs Cheapest Baseline    : Saves {vs_c['transit_time_saved_days']} days ({vs_c['transit_time_saved_pct']}%) with {vs_c['risk_reduction_pct']}% risk reduction (premium: ${vs_c['cost_premium_usd']:,.2f})")
        vs_f = report["heuristic_comparisons"]["vs_greedy_fastest"]
        print(f"  vs Fastest Baseline     : Saves ${vs_f['cost_saved_usd']:,.2f} ({vs_f['cost_saved_pct']}%) with only +{vs_f['transit_time_delta_days']} days lead time")
        print("=" * 70 + "\n")

    elif args.command == "sensitivity":
        shipments = load_shipments()
        target = next((s for s in shipments if s.shipment_id.upper() == args.shipment.upper()), None)
        if not target:
            print(f"Shipment {args.shipment} not found.")
            sys.exit(1)

        profile = DEFAULT_PROFILES.get(args.profile, DEFAULT_PROFILES["balanced"])
        optimizer = RouteOptimizer(monte_carlo_runs=300)
        sens = optimizer.run_sensitivity_analysis(target, profile)

        print("\n" + "=" * 70)
        print(f"SENSITIVITY ANALYSIS FOR {target.shipment_id} (Base Winner: {sens['base_recommended_id']})")
        print("=" * 70)
        for crit, info in sens["criteria_sensitivity"].items():
            status = "STABLE (No flips across tested range)" if info["is_stable"] else f"FLIPS DETECTED ({len(info['flips'])} conditions)"
            print(f"\nCriterion: {crit.upper()} (Base Weight = {info['base_weight']}) -> {status}")
            for flip in info["flips"]:
                print(f"  - When weight reaches {flip['weight_value']:.2f} -> Flips to {flip['new_winner_id']} ({flip['new_winner_name']})")
        print("=" * 70 + "\n")

    elif args.command == "serve":
        from web.server import run_server
        run_server(port=args.port)


if __name__ == "__main__":
    main()
