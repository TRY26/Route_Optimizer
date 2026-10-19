"""
Lightweight REST API and Web Server for the Interactive Route Optimization Dashboard.
Built using standard library http.server and urllib (zero external dependencies required).
"""

import http.server
import json
import os
import socketserver
import urllib.parse
from typing import Dict, Any

from src.models import DEFAULT_PROFILES, PriorityProfile
from src.optimizer import RouteOptimizer
from src.explainer import RouteExplainer
from src.evaluation import SystemEvaluator
from cli import load_shipments


class RouteOptimizerHandler(http.server.SimpleHTTPRequestHandler):
    """Handles API requests and serves web frontend."""

    shipments_cache = None
    optimizer = RouteOptimizer(monte_carlo_runs=500, random_seed=42)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/shipments":
            self.send_json_response(self.get_shipments_summary())
        elif path == "/api/benchmark":
            query = urllib.parse.parse_qs(parsed.query)
            profile_name = query.get("profile", ["balanced"])[0]
            profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["balanced"])
            shipments = self.get_cached_shipments()
            evaluator = SystemEvaluator(self.optimizer)
            report = evaluator.evaluate_dataset(shipments, profile=profile)
            self.send_json_response(report)
        elif path == "/" or path == "/index.html":
            self.serve_frontend()
        else:
            # Fallback to file serving
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/recommend":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body) if body else {}
            except Exception:
                payload = {}

            shipment_id = payload.get("shipment_id", "SHP-001")
            profile_name = payload.get("profile", "balanced")
            custom_weights = payload.get("custom_weights")

            shipments = self.get_cached_shipments()
            target = next((s for s in shipments if s.shipment_id.upper() == shipment_id.upper()), None)
            if not target:
                self.send_json_response({"error": f"Shipment '{shipment_id}' not found."}, status=404)
                return

            profile = DEFAULT_PROFILES.get(profile_name, DEFAULT_PROFILES["balanced"])
            res = self.optimizer.evaluate_shipment(target, profile=profile, custom_weights=custom_weights)
            expl = RouteExplainer.generate_explanation(res)
            sens = self.optimizer.run_sensitivity_analysis(target, res.profile_used)

            # Package full response
            response_data = {
                "shipment": target.to_dict(),
                "profile_used": {
                    "name": res.profile_used.name,
                    "description": res.profile_used.description,
                    "weights": res.profile_used.normalized_weights(),
                },
                "recommended_route_id": res.recommended.route.route_id,
                "runner_up_route_id": res.runner_up.route.route_id if res.runner_up else None,
                "evaluations": [
                    {
                        "route_id": ev.route.route_id,
                        "name": ev.route.name,
                        "strategy": ev.route.strategy_type,
                        "rank": ev.rank,
                        "cost": ev.route.total_cost_usd,
                        "transit_time_days": ev.route.estimated_transit_time_days,
                        "delay_probability": ev.route.delay_probability,
                        "congestion_risk": ev.route.congestion_risk,
                        "geopolitical_risk": ev.route.geopolitical_risk,
                        "weather_risk": ev.route.weather_risk,
                        "carbon_kg": ev.route.carbon_emissions_kg,
                        "composite_risk": ev.route.composite_risk_score,
                        "utility_score": ev.weighted_utility_score,
                        "topsis_score": ev.topsis_closeness,
                        "is_pareto": ev.is_pareto_optimal,
                        "simulated_expected_days": ev.simulated_expected_days,
                        "simulated_p95_days": ev.simulated_p95_days,
                        "on_time_probability": ev.on_time_probability,
                        "legs": [leg.to_dict() for leg in ev.route.legs],
                    }
                    for ev in res.all_evaluations
                ],
                "explanation": expl,
                "sensitivity": sens,
                "markdown_briefing": RouteExplainer.format_markdown_report(res),
            }
            self.send_json_response(response_data)
        else:
            self.send_json_response({"error": "Endpoint not found"}, status=404)

    def send_json_response(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def serve_frontend(self):
        frontend_path = os.path.join(os.path.dirname(__file__), "index.html")
        if not os.path.exists(frontend_path):
            self.send_json_response({"error": "Dashboard template not found"}, status=404)
            return
        with open(frontend_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    @classmethod
    def get_cached_shipments(cls):
        if cls.shipments_cache is None:
            cls.shipments_cache = load_shipments()
        return cls.shipments_cache

    @classmethod
    def get_shipments_summary(cls):
        shipments = cls.get_cached_shipments()
        return [
            {
                "shipment_id": s.shipment_id,
                "corridor": s.corridor,
                "origin": s.origin,
                "destination": s.destination,
                "cargo_type": s.cargo_type.value if hasattr(s.cargo_type, "value") else str(s.cargo_type),
                "cargo_value_usd": s.cargo_value_usd,
                "priority_level": s.priority_level,
                "route_count": len(s.routes),
            }
            for s in shipments
        ]


def run_server(port: int = 8080):
    handler = RouteOptimizerHandler
    # Change root directory to current
    server_address = ("", port)
    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, handler) as httpd:
        print(f"\n=======================================================")
        print(f"🚀 AIQON Route Optimizer Dashboard is Live!")
        print(f"👉 Local URL: http://localhost:{port}")
        print(f"Press Ctrl+C to terminate the server.")
        print(f"=======================================================\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down web server...")
            httpd.server_close()


if __name__ == "__main__":
    run_server(8080)
