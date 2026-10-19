"""
Decision Explainability & Natural Language Justification Engine.
Translates mathematical optimization and trade-off metrics into clear,
actionable, logistics-operator-friendly explanations.
"""

from typing import Dict, Any, List
from .optimizer import RecommendationResult, RouteEvaluation


class RouteExplainer:
    """
    Generates structured, plain-English explanations for route recommendations.
    """

    @staticmethod
    def generate_explanation(result: RecommendationResult) -> Dict[str, Any]:
        """
        Builds a comprehensive explanation package:
        - Executive Summary (1-2 sentence bottom line)
        - Key Trade-Off Rationale (winner vs runner-up)
        - Risk & Reliability Justification (P95 and choke points)
        - Alternative Route Disqualification Reasons
        - Dispatcher Checklist & Advisory
        """
        rec = result.recommended
        runner_up = result.runner_up
        r_rec = rec.route
        profile = result.profile_used

        # 1. Executive Summary
        summary = RouteExplainer._build_executive_summary(rec, runner_up, profile)

        # 2. Comparative Trade-off Breakdown
        comparative_analysis = RouteExplainer._build_comparative_analysis(rec, runner_up)

        # 3. Disqualification / Alternative Rationale
        alternative_notes = RouteExplainer._build_alternatives_rationale(result.all_evaluations)

        # 4. Uncertainty & Risk Perspective
        uncertainty_brief = (
            f"Under stochastic Monte Carlo simulation (1,000 runs), '{r_rec.name}' delivers an expected transit "
            f"of {rec.simulated_expected_days} days and a 95th percentile SLA buffer of {rec.simulated_p95_days} days, "
            f"achieving an on-time delivery probability of {rec.on_time_probability * 100:.1f}%."
        )

        return {
            "shipment_id": result.shipment_id,
            "corridor": result.corridor,
            "recommended_route_id": r_rec.route_id,
            "recommended_route_name": r_rec.name,
            "strategy": r_rec.strategy_type,
            "executive_summary": summary,
            "trade_off_breakdown": comparative_analysis,
            "uncertainty_and_reliability": uncertainty_brief,
            "alternatives_reviewed": alternative_notes,
            "is_pareto_optimal": rec.is_pareto_optimal,
            "composite_score": round(
                0.5 * rec.weighted_utility_score + 0.5 * rec.topsis_closeness, 3
            ),
        }

    @staticmethod
    def _build_executive_summary(
        rec: RouteEvaluation, runner_up: RouteEvaluation, profile
    ) -> str:
        r1 = rec.route
        if not runner_up:
            return f"Route '{r1.name}' is the sole available option for this corridor."

        r2 = runner_up.route

        cost_diff = r1.total_cost_usd - r2.total_cost_usd
        time_diff = r1.estimated_transit_time_days - r2.estimated_transit_time_days

        # Case 1: Winner is cheaper and faster (Dominates)
        if cost_diff <= 0 and time_diff <= 0:
            return (
                f"Route '{r1.name}' was selected as the dominant choice under the '{profile.name}' profile. "
                f"It is ${abs(cost_diff):,.2f} cheaper and {abs(time_diff):.1f} days faster than '{r2.name}'."
            )

        # Case 2: Winner is cheaper, but takes slightly longer
        if cost_diff < 0 and time_diff > 0:
            return (
                f"Route '{r1.name}' is recommended to optimize freight spend under the '{profile.name}' profile. "
                f"It yields significant cost savings of ${abs(cost_diff):,.2f} "
                f"({abs(cost_diff)/r2.total_cost_usd * 100:.1f}%) in exchange for a manageable transit addition of {time_diff:.1f} days."
            )

        # Case 3: Winner is faster, but costs more (Speed/Urgency justification)
        if cost_diff > 0 and time_diff < 0:
            return (
                f"Route '{r1.name}' is recommended for speed and schedule security under the '{profile.name}' profile. "
                f"It accelerates delivery by {abs(time_diff):.1f} days compared to '{r2.name}', justifying an additional "
                f"investment of ${cost_diff:,.2f}."
            )

        # Case 4: Equal time/cost, decided on risk
        return (
            f"Route '{r1.name}' is recommended based on superior reliability and lower composite risk "
            f"({r1.composite_risk_score:.2f} vs {r2.composite_risk_score:.2f}) under the '{profile.name}' profile."
        )

    @staticmethod
    def _build_comparative_analysis(
        rec: RouteEvaluation, runner_up: RouteEvaluation
    ) -> Dict[str, Any]:
        if not runner_up:
            return {}

        r1 = rec.route
        r2 = runner_up.route

        # Detailed points
        highlights = []

        # Cost comparison
        c_diff = r1.total_cost_usd - r2.total_cost_usd
        if abs(c_diff) > 1:
            direction = "savings of" if c_diff < 0 else "premium of"
            highlights.append(
                f"Cost difference: A {direction} ${abs(c_diff):,.2f} "
                f"({abs(c_diff)/r2.total_cost_usd * 100:.1f}%)"
            )

        # Transit time comparison
        t_diff = r1.estimated_transit_time_days - r2.estimated_transit_time_days
        if abs(t_diff) > 0.1:
            direction = "faster by" if t_diff < 0 else "slower by"
            highlights.append(
                f"Lead time: {direction} {abs(t_diff):.1f} days "
                f"({r1.estimated_transit_time_days:.1f} d vs {r2.estimated_transit_time_days:.1f} d)"
            )

        # Risk comparison
        if r1.geopolitical_risk < r2.geopolitical_risk:
            highlights.append(
                f"Geopolitical exposure: Lower geopolitical risk index ({r1.geopolitical_risk:.2f} vs {r2.geopolitical_risk:.2f}), "
                f"avoiding critical bottleneck friction"
            )
        elif r1.geopolitical_risk > r2.geopolitical_risk:
            highlights.append(
                f"Geopolitical exposure: Accepted higher geopolitical risk ({r1.geopolitical_risk:.2f} vs {r2.geopolitical_risk:.2f}) "
                f"due to compelling lead time and cost advantages"
            )

        if r1.delay_probability < r2.delay_probability:
            highlights.append(
                f"Delay risk: Lower delay likelihood ({r1.delay_probability*100:.0f}% vs {r2.delay_probability*100:.0f}%)"
            )

        # SLA / P95 comparison
        p95_diff = rec.simulated_p95_days - runner_up.simulated_p95_days
        if abs(p95_diff) > 0.1:
            dir_p95 = "tighter" if p95_diff < 0 else "wider"
            highlights.append(
                f"Worst-case (P95) transit: {dir_p95} buffer by {abs(p95_diff):.1f} days "
                f"({rec.simulated_p95_days:.1f} d vs {runner_up.simulated_p95_days:.1f} d)"
            )

        return {
            "comparison_with": f"{r2.name} ({r2.route_id})",
            "key_factors": highlights,
        }

    @staticmethod
    def _build_alternatives_rationale(evaluations: List[RouteEvaluation]) -> List[Dict[str, str]]:
        notes = []
        for ev in evaluations[1:]:
            r = ev.route
            reasons = []

            if not ev.is_pareto_optimal:
                reasons.append("Mathematically dominated by faster, cheaper, or lower-risk options")

            if r.geopolitical_risk > 0.65:
                reasons.append(f"Elevated geopolitical hazard score ({r.geopolitical_risk:.2f})")

            if r.delay_probability > 0.45:
                reasons.append(f"High risk of multi-port dwell delay ({r.delay_probability*100:.0f}%)")

            if r.carbon_emissions_kg > 4000:
                reasons.append("Very high carbon footprint relative to sea/rail alternatives")

            if not reasons:
                reasons.append("Suboptimal balance across weighted profile criteria")

            notes.append({
                "route_id": r.route_id,
                "route_name": r.name,
                "rank": f"Rank #{ev.rank}",
                "primary_drawback": "; ".join(reasons),
            })

        return notes

    @staticmethod
    def format_markdown_report(result: RecommendationResult) -> str:
        """Formats the recommendation as a clean, ready-to-read markdown briefing."""
        expl = RouteExplainer.generate_explanation(result)
        rec = result.recommended.route

        lines = [
            f"### Shipment Route Recommendation: `{result.shipment_id}`",
            f"**Trade Corridor:** {result.corridor} ({result.origin} -> {result.destination})  ",
            f"**Decision Profile:** {result.profile_used.name}  ",
            "",
            f"#### Recommended Option: **{rec.name}** (`{rec.route_id}`)",
            f"- **Strategy:** {rec.strategy_type}",
            f"- **Freight Cost:** ${rec.total_cost_usd:,.2f}",
            f"- **Lead Time:** {rec.estimated_transit_time_days:.1f} days (P95 SLA: {result.recommended.simulated_p95_days:.1f} days)",
            f"- **Delay Probability:** {rec.delay_probability * 100:.1f}%",
            f"- **Geopolitical Risk:** {rec.geopolitical_risk:.2f} / 1.0",
            f"- **Carbon Footprint:** {rec.carbon_emissions_kg:,.1f} kg CO2",
            "",
            "#### Why this route was chosen:",
            f"> {expl['executive_summary']}",
            "",
            "**Key Trade-offs against Runner-Up:**",
        ]

        if expl["trade_off_breakdown"]:
            for f in expl["trade_off_breakdown"].get("key_factors", []):
                lines.append(f"- {f}")
        else:
            lines.append("- No viable runner-up available.")

        lines.extend([
            "",
            "**Simulation & Uncertainty Assurance:**",
            f"- {expl['uncertainty_and_reliability']}",
            "",
            "**Alternative Route Evaluations:**",
        ])

        for alt in expl["alternatives_reviewed"]:
            lines.append(f"- **{alt['route_name']}** ({alt['rank']}): {alt['primary_drawback']}")

        return "\n".join(lines)
