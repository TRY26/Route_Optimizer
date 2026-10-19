"""
Domain models for the Multi-Objective Logistics Route Optimization System.
Designed for Aiqon Take-Home Assignment.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum


class CargoType(str, Enum):
    GENERAL = "General Merchandise"
    HIGH_VALUE = "High-Value Electronics"
    PERISHABLE = "Perishables / Cold Chain"
    BULK = "Bulk Industrial Materials"
    PHARMA = "Pharmaceuticals / Medical"


class TransportMode(str, Enum):
    OCEAN = "Ocean"
    AIR = "Air Freight"
    RAIL = "Rail Multimodal"
    ROAD = "Road Feeder"


@dataclass
class RouteLeg:
    leg_id: str
    origin: str
    destination: str
    mode: str
    carrier_type: str
    transit_time_days: float
    cost_usd: float
    delay_prob: float
    congestion_risk: float   # 0.0 to 1.0 scale
    geopolitical_risk: float # 0.0 to 1.0 scale
    weather_risk: float      # 0.0 to 1.0 scale
    carbon_kg: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RouteOption:
    route_id: str
    name: str
    strategy_type: str  # e.g., "Direct Express", "Transshipment Hub", "Geopolitical Bypass", "Air Urgent", "Rail Hybrid"
    legs: List[RouteLeg]
    total_cost_usd: float
    estimated_transit_time_days: float
    delay_probability: float
    congestion_risk: float     # aggregated leg-level congestion
    geopolitical_risk: float   # max/aggregated geopolitical exposure
    weather_risk: float        # aggregated weather volatility
    carbon_emissions_kg: float
    composite_risk_score: float # calculated weighted composite risk
    intermediate_nodes: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["legs"] = [leg.to_dict() if hasattr(leg, "to_dict") else leg for leg in self.legs]
        return d


@dataclass
class Shipment:
    shipment_id: str
    origin: str
    origin_country: str
    destination: str
    destination_country: str
    corridor: str
    cargo_type: CargoType
    cargo_weight_kg: float
    cargo_value_usd: float
    priority_level: str  # "Standard", "High", "Critical"
    max_budget_usd: Optional[float] = None
    target_delivery_days: Optional[float] = None
    routes: List[RouteOption] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["cargo_type"] = self.cargo_type.value if hasattr(self.cargo_type, "value") else str(self.cargo_type)
        d["routes"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in self.routes]
        return d


@dataclass
class PriorityProfile:
    name: str
    description: str
    weight_cost: float
    weight_time: float
    weight_delay_risk: float
    weight_geopolitical_risk: float
    weight_carbon: float = 0.0

    def normalized_weights(self) -> Dict[str, float]:
        total = (
            self.weight_cost
            + self.weight_time
            + self.weight_delay_risk
            + self.weight_geopolitical_risk
            + self.weight_carbon
        )
        if total <= 0:
            raise ValueError("Sum of weights must be positive")
        return {
            "cost": self.weight_cost / total,
            "time": self.weight_time / total,
            "delay_risk": self.weight_delay_risk / total,
            "geopolitical_risk": self.weight_geopolitical_risk / total,
            "carbon": self.weight_carbon / total,
        }


# Standard pre-configured business profiles
DEFAULT_PROFILES = {
    "balanced": PriorityProfile(
        name="Balanced Logistics",
        description="Standard supply chain equilibrium balancing cost, transit speed, and operational risk.",
        weight_cost=0.30,
        weight_time=0.30,
        weight_delay_risk=0.20,
        weight_geopolitical_risk=0.15,
        weight_carbon=0.05,
    ),
    "cost_saver": PriorityProfile(
        name="Cost Saver (Economic)",
        description="Prioritizes freight cost minimization for low-margin, non-urgent, or high-volume goods.",
        weight_cost=0.60,
        weight_time=0.15,
        weight_delay_risk=0.15,
        weight_geopolitical_risk=0.08,
        weight_carbon=0.02,
    ),
    "speed_first": PriorityProfile(
        name="Speed First (Urgent/Perishable)",
        description="Prioritizes fastest delivery time for perishables, critical assembly components, and tight SLA shipments.",
        weight_cost=0.10,
        weight_time=0.60,
        weight_delay_risk=0.15,
        weight_geopolitical_risk=0.10,
        weight_carbon=0.05,
    ),
    "risk_averse": PriorityProfile(
        name="Risk Averse (High Reliability)",
        description="Avoids choke points, congested transshipment hubs, and geopolitical flashpoints for high-value cargo.",
        weight_cost=0.15,
        weight_time=0.15,
        weight_delay_risk=0.35,
        weight_geopolitical_risk=0.30,
        weight_carbon=0.05,
    ),
    "eco_conscious": PriorityProfile(
        name="Eco-Conscious (Green Supply Chain)",
        description="Prioritizes environmental sustainability and lower scope 3 carbon emissions.",
        weight_cost=0.25,
        weight_time=0.20,
        weight_delay_risk=0.15,
        weight_geopolitical_risk=0.10,
        weight_carbon=0.30,
    ),
}
