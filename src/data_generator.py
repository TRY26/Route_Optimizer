"""
Realistic Synthetic Data Generator for Global Logistics Routing.
Models genuine international trade lanes, multi-leg journeys, and realistic
trade-offs between freight costs, transit times, delay probabilities, and risks.
"""

import json
import csv
import random
from typing import List, Dict, Any
from .models import RouteLeg, RouteOption, Shipment, CargoType, TransportMode


# Major global trade lane archetypes
TRADE_CORRIDORS = [
    {
        "name": "Asia - Northern Europe",
        "origin": "Shanghai (CNSHA)",
        "origin_country": "China",
        "destination": "Rotterdam (NLRTM)",
        "destination_country": "Netherlands",
        "distance_approx_km": 19500,
        "default_cargo": CargoType.GENERAL,
        "archetypes": [
            {
                "name": "Direct Ocean via Suez Canal",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (28.0, 33.0),
                "cost_base_teu": (2800, 3400),
                "delay_prob": 0.38,
                "congestion_risk": 0.45,
                "geopolitical_risk": 0.82,  # Red Sea / Bab-el-Mandeb unrest
                "weather_risk": 0.25,
                "carbon_factor": 1.0,
                "legs": [
                    ("Shanghai Port Terminal", "CNSHA", TransportMode.ROAD, 0.8, 150, 0.15, 0.30, 0.05, 0.10, 45),
                    ("CNSHA to Bab-el-Mandeb", "Red Sea Transit", TransportMode.OCEAN, 16.0, 1600, 0.40, 0.40, 0.85, 0.20, 750),
                    ("Suez Canal to NLRTM", "Rotterdam Port", TransportMode.OCEAN, 12.0, 1250, 0.30, 0.45, 0.40, 0.25, 620),
                    ("Rotterdam Hinterland Rail/Truck", "Distro Hub", TransportMode.ROAD, 1.2, 200, 0.10, 0.20, 0.05, 0.05, 60),
                ],
                "description": "Standard fast ocean route via Suez Canal. Prone to high geopolitical risk and security surcharges in the Red Sea.",
            },
            {
                "name": "Ocean via Cape of Good Hope Bypass",
                "strategy": "Geopolitical Bypass",
                "transit_time_days": (39.0, 45.0),
                "cost_base_teu": (3500, 4200),
                "delay_prob": 0.22,
                "congestion_risk": 0.30,
                "geopolitical_risk": 0.08,  # Bypasses Middle East choke point completely
                "weather_risk": 0.45,       # Rough South Atlantic weather
                "carbon_factor": 1.35,      # Longer distance
                "legs": [
                    ("Shanghai Port Terminal", "CNSHA", TransportMode.ROAD, 0.8, 150, 0.15, 0.30, 0.05, 0.10, 45),
                    ("CNSHA around Cape of Good Hope", "Cape Sea Route", TransportMode.OCEAN, 26.0, 2400, 0.20, 0.20, 0.05, 0.50, 1150),
                    ("West Africa to NLRTM", "Rotterdam Port", TransportMode.OCEAN, 14.0, 1250, 0.18, 0.35, 0.05, 0.35, 700),
                    ("Rotterdam Hinterland Rail/Truck", "Distro Hub", TransportMode.ROAD, 1.2, 200, 0.10, 0.20, 0.05, 0.05, 60),
                ],
                "description": "Circumnavigates Africa to avoid Red Sea geopolitical conflict. Higher transit time and bunker cost, but highly secure.",
            },
            {
                "name": "Ocean Transshipment via Singapore & Tangier",
                "strategy": "Transshipment Economy",
                "transit_time_days": (34.0, 41.0),
                "cost_base_teu": (2300, 2750),
                "delay_prob": 0.52,         # Multi-port dwell time risk
                "congestion_risk": 0.68,    # Transshipment berth congestion
                "geopolitical_risk": 0.50,
                "weather_risk": 0.30,
                "carbon_factor": 1.15,
                "legs": [
                    ("Shanghai Port Terminal", "CNSHA", TransportMode.ROAD, 0.8, 150, 0.15, 0.30, 0.05, 0.10, 45),
                    ("CNSHA to Singapore Hub (SGSIN)", "Singapore Strait", TransportMode.OCEAN, 6.0, 650, 0.45, 0.75, 0.15, 0.25, 290),
                    ("Singapore Hub Transshipment Dwell", "SGSIN Terminal", TransportMode.OCEAN, 4.0, 250, 0.60, 0.80, 0.10, 0.10, 50),
                    ("SGSIN to Tangier Med (MATNG)", "Mediterranean Leg", TransportMode.OCEAN, 18.0, 1100, 0.45, 0.55, 0.60, 0.30, 850),
                    ("Tangier Feeder to NLRTM", "Rotterdam Port", TransportMode.OCEAN, 6.0, 450, 0.35, 0.45, 0.10, 0.25, 280),
                    ("Rotterdam Hinterland Rail/Truck", "Distro Hub", TransportMode.ROAD, 1.2, 200, 0.10, 0.20, 0.05, 0.05, 60),
                ],
                "description": "Budget carrier route consolidating containers at mega-hubs. Lower cost but prone to vessel connection misses and terminal delays.",
            },
            {
                "name": "Eurasian Landbridge (Rail Express)",
                "strategy": "Rail Multimodal",
                "transit_time_days": (16.0, 20.0),
                "cost_base_teu": (5200, 6400),
                "delay_prob": 0.28,
                "congestion_risk": 0.35,
                "geopolitical_risk": 0.40,  # Border crossings / customs
                "weather_risk": 0.35,       # Continental winter freeze
                "carbon_factor": 0.40,      # Low carbon rail
                "legs": [
                    ("Shanghai Consolidation Yard", "Rail Depot", TransportMode.ROAD, 1.0, 220, 0.15, 0.25, 0.05, 0.05, 55),
                    ("Chongqing/Xi'an to Dostyk (Kazakhstan)", "China Rail", TransportMode.RAIL, 6.0, 2200, 0.25, 0.35, 0.20, 0.30, 190),
                    ("Dostyk Bogie Gauge Change & Transit to Poland", "CIS Rail", TransportMode.RAIL, 7.5, 2300, 0.35, 0.40, 0.45, 0.40, 240),
                    ("Malaszewicze to Duisburg/Rotterdam", "EU Rail", TransportMode.RAIL, 3.0, 950, 0.20, 0.25, 0.15, 0.20, 110),
                ],
                "description": "Multimodal rail through Central Asia. 2x faster than ocean freight at roughly 2x cost, with superior carbon footprint.",
            },
            {
                "name": "Direct Air Cargo Express",
                "strategy": "Air Urgent",
                "transit_time_days": (3.0, 5.0),
                "cost_base_teu": (16000, 22000),
                "delay_prob": 0.12,
                "congestion_risk": 0.20,
                "geopolitical_risk": 0.10,
                "weather_risk": 0.25,
                "carbon_factor": 8.50,      # High emissions
                "legs": [
                    ("Shanghai PVG Airport Pickup", "PVG Cargo Terminal", TransportMode.ROAD, 0.5, 300, 0.10, 0.25, 0.05, 0.05, 40),
                    ("PVG to Amsterdam Schiphol (AMS)", "Air Freight Flight", TransportMode.AIR, 1.5, 17500, 0.12, 0.20, 0.10, 0.25, 4200),
                    ("Schiphol Express Bonded Truck to NLRTM", "Final Delivery", TransportMode.ROAD, 1.0, 450, 0.08, 0.15, 0.02, 0.05, 80),
                ],
                "description": "Dedicated charter / freighter air service. Fastest possible transit with high reliability, but premium cost and carbon.",
            },
        ],
    },
    {
        "name": "Transpacific Eastbound (Asia to US West Coast)",
        "origin": "Shenzhen (CNSZX)",
        "origin_country": "China",
        "destination": "Los Angeles / Long Beach (USLAX)",
        "destination_country": "United States",
        "distance_approx_km": 11800,
        "default_cargo": CargoType.HIGH_VALUE,
        "archetypes": [
            {
                "name": "Direct Pacific Ocean to USLAX",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (15.0, 18.0),
                "cost_base_teu": (2400, 3100),
                "delay_prob": 0.42,
                "congestion_risk": 0.75,    # LA/LB port container dwell congestion
                "geopolitical_risk": 0.15,
                "weather_risk": 0.30,
                "carbon_factor": 1.0,
                "legs": [
                    ("Shenzhen Factory Drayage", "Yantian Terminal", TransportMode.ROAD, 0.5, 180, 0.10, 0.30, 0.05, 0.05, 35),
                    ("Yantian (CNYTN) to Long Beach (USLGB)", "Pacific Crossing", TransportMode.OCEAN, 13.5, 2300, 0.35, 0.70, 0.15, 0.35, 620),
                    ("USLGB Berth Discharge & Truck Out", "Inland Hub", TransportMode.ROAD, 2.0, 350, 0.55, 0.85, 0.05, 0.05, 90),
                ],
                "description": "Standard direct Pacific crossing. Highly cost-effective but vulnerable to California dock and terminal congestion.",
            },
            {
                "name": "Pacific Northwest Bypass (via Tacoma/Seattle)",
                "strategy": "Congestion Bypass",
                "transit_time_days": (17.0, 21.0),
                "cost_base_teu": (2900, 3500),
                "delay_prob": 0.25,
                "congestion_risk": 0.32,
                "geopolitical_risk": 0.12,
                "weather_risk": 0.40,       # North Pacific winter swells
                "carbon_factor": 1.15,
                "legs": [
                    ("Shenzhen Factory Drayage", "Yantian Terminal", TransportMode.ROAD, 0.5, 180, 0.10, 0.30, 0.05, 0.05, 35),
                    ("Yantian to Tacoma (USTIW)", "North Pacific Route", TransportMode.OCEAN, 14.5, 2400, 0.20, 0.30, 0.10, 0.45, 680),
                    ("Tacoma Rail/Intermodal to Southern CA", "BNSF Rail", TransportMode.RAIL, 3.5, 750, 0.22, 0.30, 0.05, 0.15, 180),
                ],
                "description": "Routes container into less congested Pacific Northwest terminal with rail transfer south, avoiding LA port queues.",
            },
            {
                "name": "Transpacific Transshipment via Busan (KRBUS)",
                "strategy": "Transshipment Economy",
                "transit_time_days": (21.0, 26.0),
                "cost_base_teu": (1950, 2400),
                "delay_prob": 0.45,
                "congestion_risk": 0.50,
                "geopolitical_risk": 0.20,
                "weather_risk": 0.35,
                "carbon_factor": 1.10,
                "legs": [
                    ("Shenzhen Drayage", "Shekou Terminal", TransportMode.ROAD, 0.5, 160, 0.10, 0.25, 0.05, 0.05, 30),
                    ("Shekou to Busan Feeder", "Korea Strait", TransportMode.OCEAN, 3.5, 450, 0.30, 0.40, 0.15, 0.30, 160),
                    ("Busan Hub Connection Dwell", "KRBUS Terminal", TransportMode.OCEAN, 3.0, 180, 0.45, 0.55, 0.10, 0.10, 40),
                    ("Busan to USLAX Linehaul", "Pacific Mainline", TransportMode.OCEAN, 13.0, 1300, 0.32, 0.55, 0.12, 0.30, 580),
                    ("USLAX Local Delivery", "Destination", TransportMode.ROAD, 1.0, 220, 0.25, 0.50, 0.02, 0.05, 50),
                ],
                "description": "Low-cost feeder transshipment through South Korea. Saves money but adds 5-8 days and connection risk.",
            },
            {
                "name": "Air Cargo Charter Express (SZX -> LAX)",
                "strategy": "Air Urgent",
                "transit_time_days": (2.5, 4.0),
                "cost_base_teu": (14500, 18500),
                "delay_prob": 0.10,
                "congestion_risk": 0.18,
                "geopolitical_risk": 0.08,
                "weather_risk": 0.20,
                "carbon_factor": 7.80,
                "legs": [
                    ("Shenzhen Bao'an Airport Prep", "SZX Cargo Hub", TransportMode.ROAD, 0.5, 250, 0.08, 0.20, 0.05, 0.05, 35),
                    ("SZX to LAX Direct Flight", "Transpacific Air Freight", TransportMode.AIR, 1.2, 15500, 0.10, 0.18, 0.08, 0.20, 3600),
                    ("LAX Cargo Terminal Customs & Courier", "Final Mile", TransportMode.ROAD, 0.8, 380, 0.10, 0.15, 0.02, 0.02, 60),
                ],
                "description": "Dedicated transpacific air cargo for urgent high-value electronics and emergency inventory replenishment.",
            },
        ],
    },
    {
        "name": "Asia to US East Coast (Transpacific/All-Water vs Intermodal)",
        "origin": "Ningbo (CNNGB)",
        "origin_country": "China",
        "destination": "New York / New Jersey (USNYC)",
        "destination_country": "United States",
        "distance_approx_km": 18200,
        "default_cargo": CargoType.BULK,
        "archetypes": [
            {
                "name": "All-Water Ocean via Panama Canal",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (27.0, 34.0),
                "cost_base_teu": (3600, 4400),
                "delay_prob": 0.55,
                "congestion_risk": 0.70,    # Panama Canal draft restrictions & slot auctions
                "geopolitical_risk": 0.20,
                "weather_risk": 0.35,       # Caribbean hurricane season
                "carbon_factor": 1.0,
                "legs": [
                    ("Ningbo Port Drayage", "CNNGB", TransportMode.ROAD, 0.6, 170, 0.10, 0.25, 0.05, 0.05, 35),
                    ("CNNGB to Panama Canal Locks", "Pacific Passage", TransportMode.OCEAN, 17.0, 2100, 0.25, 0.35, 0.15, 0.30, 850),
                    ("Panama Canal Wait & Transit", "Canal Zone", TransportMode.OCEAN, 4.0, 650, 0.70, 0.85, 0.20, 0.20, 120),
                    ("Canal to Port of NY/NJ", "Atlantic Coast", TransportMode.OCEAN, 7.0, 1100, 0.30, 0.45, 0.10, 0.40, 450),
                    ("NY/NJ Port Drayage", "NJ Warehouse", TransportMode.ROAD, 1.0, 280, 0.20, 0.35, 0.02, 0.05, 65),
                ],
                "description": "All-water container vessel passing through the Panama Canal. Subject to severe drought delays and booking queue surcharges.",
            },
            {
                "name": "Mini Landbridge (US West Coast Ocean + Cross-Continent Rail)",
                "strategy": "Rail Multimodal",
                "transit_time_days": (19.0, 24.0),
                "cost_base_teu": (4900, 5900),
                "delay_prob": 0.30,
                "congestion_risk": 0.40,
                "geopolitical_risk": 0.12,
                "weather_risk": 0.28,
                "carbon_factor": 0.85,
                "legs": [
                    ("Ningbo Drayage", "CNNGB Terminal", TransportMode.ROAD, 0.6, 170, 0.10, 0.25, 0.05, 0.05, 35),
                    ("CNNGB to Los Angeles (USLAX)", "Pacific Express Line", TransportMode.OCEAN, 13.5, 2200, 0.25, 0.50, 0.12, 0.25, 650),
                    ("USLAX On-Dock Rail Ramp Transfer", "Intermodal Yard", TransportMode.ROAD, 1.0, 300, 0.35, 0.60, 0.05, 0.05, 50),
                    ("Transcontinental Rail (LAX to Chicago to NY)", "Class 1 Rail", TransportMode.RAIL, 5.5, 2300, 0.22, 0.30, 0.05, 0.25, 290),
                    ("Kearny Intermodal Terminal to Receiver", "Local Dray", TransportMode.ROAD, 0.8, 260, 0.15, 0.25, 0.02, 0.02, 45),
                ],
                "description": "Discharges on the US West Coast and travels across the continental US by intermodal rail. 8-10 days faster than all-water canal route.",
            },
            {
                "name": "Ocean via Suez & Mediterranean to US East Coast",
                "strategy": "Geopolitical Bypass",
                "transit_time_days": (32.0, 38.0),
                "cost_base_teu": (3300, 4100),
                "delay_prob": 0.48,
                "congestion_risk": 0.50,
                "geopolitical_risk": 0.78,  # Red Sea / Middle East exposure
                "weather_risk": 0.30,
                "carbon_factor": 1.20,
                "legs": [
                    ("Ningbo Drayage", "CNNGB", TransportMode.ROAD, 0.6, 170, 0.10, 0.25, 0.05, 0.05, 35),
                    ("CNNGB across Indian Ocean to Suez", "Indian Ocean Leg", TransportMode.OCEAN, 18.0, 1700, 0.45, 0.45, 0.82, 0.25, 920),
                    ("Suez to Strait of Gibraltar", "Med Crossing", TransportMode.OCEAN, 6.0, 650, 0.35, 0.40, 0.35, 0.20, 380),
                    ("Gibraltar to New York (USNYC)", "North Atlantic", TransportMode.OCEAN, 9.0, 950, 0.25, 0.35, 0.05, 0.35, 550),
                    ("USNYC Local Delivery", "Receiver", TransportMode.ROAD, 0.8, 250, 0.15, 0.30, 0.02, 0.02, 50),
                ],
                "description": "Alternate westward route via Suez Canal. Economical for Southeast/East Asia origins, but heavily burdened by Red Sea threat levels.",
            },
            {
                "name": "Direct Air Cargo (NGB via ICN to JFK)",
                "strategy": "Air Urgent",
                "transit_time_days": (3.0, 5.0),
                "cost_base_teu": (16800, 21500),
                "delay_prob": 0.12,
                "congestion_risk": 0.22,
                "geopolitical_risk": 0.08,
                "weather_risk": 0.20,
                "carbon_factor": 8.90,
                "legs": [
                    ("Ningbo to Shanghai Pudong (PVG)", "Airport Feeder Truck", TransportMode.ROAD, 0.8, 320, 0.12, 0.25, 0.05, 0.05, 55),
                    ("PVG to Seoul Incheon (ICN)", "Air Transfer Leg", TransportMode.AIR, 1.0, 4200, 0.10, 0.18, 0.05, 0.15, 950),
                    ("ICN to New York (JFK)", "Longhaul Air", TransportMode.AIR, 1.5, 13500, 0.10, 0.20, 0.08, 0.20, 3200),
                    ("JFK Cargo Hub to Final Consignee", "Bonded Truck", TransportMode.ROAD, 0.7, 390, 0.10, 0.20, 0.02, 0.02, 60),
                ],
                "description": "Priority air cargo route connecting through Incheon air hub to JFK for mission-critical freight.",
            },
        ],
    },
    {
        "name": "Transatlantic (Northern Europe to US East Coast)",
        "origin": "Antwerp (BEANR)",
        "origin_country": "Belgium",
        "destination": "Charleston / Savannah (USCHS)",
        "destination_country": "United States",
        "distance_approx_km": 7200,
        "default_cargo": CargoType.PHARMA,
        "archetypes": [
            {
                "name": "Direct Transatlantic Ocean Express",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (10.0, 13.0),
                "cost_base_teu": (2100, 2650),
                "delay_prob": 0.18,
                "congestion_risk": 0.28,
                "geopolitical_risk": 0.05,  # Very stable political trade lane
                "weather_risk": 0.40,       # North Atlantic winter storms
                "carbon_factor": 1.0,
                "legs": [
                    ("Antwerp Warehouse Pickup", "Port of Antwerp", TransportMode.ROAD, 0.5, 120, 0.08, 0.20, 0.02, 0.05, 25),
                    ("BEANR to USCHS Direct Call", "North Atlantic", TransportMode.OCEAN, 9.5, 2150, 0.18, 0.25, 0.05, 0.42, 480),
                    ("Charleston Port Drayage", "Distro Center", TransportMode.ROAD, 0.8, 190, 0.10, 0.20, 0.02, 0.02, 35),
                ],
                "description": "Standard direct weekly liner service across the Atlantic with low geopolitical risk and moderate weather exposure.",
            },
            {
                "name": "Multi-Port Feeder (Antwerp -> Le Havre -> New York -> Charleston)",
                "strategy": "Transshipment Economy",
                "transit_time_days": (15.0, 19.0),
                "cost_base_teu": (1650, 2050),
                "delay_prob": 0.35,
                "congestion_risk": 0.48,
                "geopolitical_risk": 0.06,
                "weather_risk": 0.38,
                "carbon_factor": 1.15,
                "legs": [
                    ("Antwerp Drayage", "BEANR Terminal", TransportMode.ROAD, 0.5, 120, 0.08, 0.20, 0.02, 0.05, 25),
                    ("BEANR to Le Havre (FRLEH)", "English Channel Feeder", TransportMode.OCEAN, 2.5, 380, 0.25, 0.35, 0.02, 0.30, 95),
                    ("FRLEH to New York (USNYC)", "North Atlantic Crossing", TransportMode.OCEAN, 8.5, 1100, 0.22, 0.35, 0.05, 0.38, 420),
                    ("USNYC to Charleston Coastal Feeder", "US Coast", TransportMode.OCEAN, 3.5, 320, 0.28, 0.45, 0.02, 0.25, 140),
                    ("USCHS Terminal Exit", "Destination", TransportMode.ROAD, 0.8, 180, 0.10, 0.20, 0.02, 0.02, 35),
                ],
                "description": "Multi-stop economy ocean service. Slower due to port rotations, but ideal for non-perishable budget cargo.",
            },
            {
                "name": "Direct Air Cargo (BRU to ATL + Reefer Truck to CHS)",
                "strategy": "Air Urgent",
                "transit_time_days": (2.0, 3.5),
                "cost_base_teu": (9800, 13200),
                "delay_prob": 0.08,
                "congestion_risk": 0.15,
                "geopolitical_risk": 0.04,
                "weather_risk": 0.18,
                "carbon_factor": 6.50,
                "legs": [
                    ("Antwerp Pharma Facility to Brussels Airport (BRU)", "GDP Temp Truck", TransportMode.ROAD, 0.4, 280, 0.05, 0.15, 0.02, 0.05, 30),
                    ("BRU to Atlanta (ATL) Pharma Direct Flight", "Air Cargo Mainline", TransportMode.AIR, 1.2, 9200, 0.08, 0.15, 0.04, 0.18, 1950),
                    ("ATL to Charleston Cold-Chain Truck", "Dedicated Reefer Dray", TransportMode.ROAD, 0.8, 520, 0.08, 0.15, 0.02, 0.05, 75),
                ],
                "description": "Temperature-controlled air freight pipeline tailored for sensitive pharmaceutical and biomedical shipments.",
            },
        ],
    },
    {
        "name": "Indian Ocean & Middle East Hub",
        "origin": "Jawaharlal Nehru Port / Mumbai (INNSA)",
        "origin_country": "India",
        "destination": "Jebel Ali / Dubai (AEJEA)",
        "destination_country": "United Arab Emirates",
        "distance_approx_km": 2100,
        "default_cargo": CargoType.PERISHABLE,
        "archetypes": [
            {
                "name": "Direct Arabian Sea Short-Sea Feeder",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (4.0, 6.0),
                "cost_base_teu": (850, 1200),
                "delay_prob": 0.22,
                "congestion_risk": 0.35,
                "geopolitical_risk": 0.25,  # Strait of Hormuz gateway proximity
                "weather_risk": 0.30,       # Monsoon season swell
                "carbon_factor": 1.0,
                "legs": [
                    ("Mumbai Inland Container Depot", "Nhava Sheva Port", TransportMode.ROAD, 0.6, 120, 0.15, 0.40, 0.05, 0.05, 25),
                    ("INNSA to Jebel Ali (AEJEA)", "Arabian Sea Line", TransportMode.OCEAN, 3.8, 750, 0.22, 0.30, 0.25, 0.30, 140),
                    ("AEJEA Port Clearance", "Dubai Logistics City", TransportMode.ROAD, 0.5, 140, 0.10, 0.15, 0.02, 0.02, 20),
                ],
                "description": "Direct short-sea feeder service connecting Western India to the Dubai hub.",
            },
            {
                "name": "Coastal Relay via Mundra (INMUN)",
                "strategy": "Transshipment Economy",
                "transit_time_days": (6.5, 9.0),
                "cost_base_teu": (680, 950),
                "delay_prob": 0.38,
                "congestion_risk": 0.45,
                "geopolitical_risk": 0.22,
                "weather_risk": 0.28,
                "carbon_factor": 1.12,
                "legs": [
                    ("Mumbai Pickup", "Local Rail Siding", TransportMode.ROAD, 0.4, 90, 0.10, 0.30, 0.05, 0.02, 18),
                    ("Mumbai to Mundra Coastal Feeder", "Gujarat Coast", TransportMode.OCEAN, 2.0, 260, 0.25, 0.40, 0.10, 0.25, 60),
                    ("Mundra Hub Transshipment", "INMUN Yard", TransportMode.OCEAN, 1.8, 120, 0.35, 0.45, 0.08, 0.08, 25),
                    ("Mundra to Jebel Ali", "Gulf Crossing", TransportMode.OCEAN, 2.8, 380, 0.20, 0.30, 0.22, 0.25, 95),
                    ("Dubai Final Mile", "Receiver", TransportMode.ROAD, 0.5, 130, 0.10, 0.15, 0.02, 0.02, 20),
                ],
                "description": "Consolidated coastal feeder via Mundra port. Reduces ocean rate by 20% at the expense of an extra transshipment step.",
            },
            {
                "name": "Express Air Freight (BOM to DXB)",
                "strategy": "Air Urgent",
                "transit_time_days": (1.0, 2.0),
                "cost_base_teu": (3800, 5200),
                "delay_prob": 0.06,
                "congestion_risk": 0.12,
                "geopolitical_risk": 0.08,
                "weather_risk": 0.12,
                "carbon_factor": 4.80,
                "legs": [
                    ("Mumbai City to BOM Cargo Terminal", "Direct Truck", TransportMode.ROAD, 0.3, 140, 0.05, 0.30, 0.02, 0.02, 20),
                    ("BOM to DXB Freighter", "Gulf Air Route", TransportMode.AIR, 0.6, 3600, 0.06, 0.12, 0.08, 0.10, 680),
                    ("DXB Cargo Village Delivery", "Same-Day Courier", TransportMode.ROAD, 0.4, 180, 0.04, 0.10, 0.02, 0.02, 20),
                ],
                "description": "Fast bellyhold and freighter air service between Mumbai and Dubai for perishable food items and urgent medical supplies.",
            },
        ],
    },
    {
        "name": "Southeast Asia to Australia Corridor",
        "origin": "Singapore (SGSIN)",
        "origin_country": "Singapore",
        "destination": "Melbourne (AUMEL)",
        "destination_country": "Australia",
        "distance_approx_km": 6800,
        "default_cargo": CargoType.GENERAL,
        "archetypes": [
            {
                "name": "Direct Ocean Liner (Singapore -> Melbourne)",
                "strategy": "Direct Chokepoint Ocean",
                "transit_time_days": (11.0, 14.0),
                "cost_base_teu": (1750, 2250),
                "delay_prob": 0.20,
                "congestion_risk": 0.32,
                "geopolitical_risk": 0.06,
                "weather_risk": 0.32,
                "carbon_factor": 1.0,
                "legs": [
                    ("Tuas Port Delivery", "SGSIN", TransportMode.ROAD, 0.5, 110, 0.05, 0.20, 0.02, 0.02, 22),
                    ("SGSIN to Port of Melbourne", "Southern Ocean Passage", TransportMode.OCEAN, 11.5, 1800, 0.18, 0.30, 0.06, 0.35, 410),
                    ("Port of Melbourne Drayage", "Industrial Park", TransportMode.ROAD, 0.8, 170, 0.10, 0.25, 0.02, 0.02, 35),
                ],
                "description": "Standard liner direct connection between Southeast Asia hub and Melbourne with minimal geopolitical friction.",
            },
            {
                "name": "Ocean via Sydney Transshipment Hub",
                "strategy": "Transshipment Economy",
                "transit_time_days": (15.0, 19.0),
                "cost_base_teu": (1350, 1700),
                "delay_prob": 0.36,
                "congestion_risk": 0.52,
                "geopolitical_risk": 0.06,
                "weather_risk": 0.35,
                "carbon_factor": 1.15,
                "legs": [
                    ("Tuas Port Delivery", "SGSIN", TransportMode.ROAD, 0.5, 110, 0.05, 0.20, 0.02, 0.02, 22),
                    ("SGSIN to Port Botany / Sydney (AUSYD)", "East Coast Liner", TransportMode.OCEAN, 12.0, 1100, 0.25, 0.45, 0.06, 0.35, 380),
                    ("Port Botany Dwell & Transshipment", "AUSYD Terminal", TransportMode.OCEAN, 2.5, 160, 0.40, 0.60, 0.04, 0.08, 30),
                    ("AUSYD to Melbourne Feeder / Rail", "Coastal Intermodal", TransportMode.RAIL, 1.8, 320, 0.22, 0.35, 0.02, 0.12, 70),
                    ("Melbourne Local Dray", "Receiver", TransportMode.ROAD, 0.6, 150, 0.10, 0.20, 0.02, 0.02, 30),
                ],
                "description": "Lower freight rate achieved by consolidating via Port Botany, but exposes goods to inter-terminal transfer delays.",
            },
            {
                "name": "Express Air Freight (SIN to MEL)",
                "strategy": "Air Urgent",
                "transit_time_days": (1.5, 3.0),
                "cost_base_teu": (7900, 10500),
                "delay_prob": 0.07,
                "congestion_risk": 0.14,
                "geopolitical_risk": 0.04,
                "weather_risk": 0.15,
                "carbon_factor": 6.20,
                "legs": [
                    ("Singapore Changi Airfreight Centre", "SIN Cargo", TransportMode.ROAD, 0.4, 150, 0.05, 0.15, 0.02, 0.02, 25),
                    ("SIN to MEL Direct Flight", "Intercontinental Air", TransportMode.AIR, 0.8, 8500, 0.06, 0.12, 0.04, 0.15, 1600),
                    ("Tullamarine Airport Customs to Door", "Express Courier", TransportMode.ROAD, 0.6, 250, 0.08, 0.15, 0.02, 0.02, 40),
                ],
                "description": "Direct widebody passenger/cargo flight from Changi to Melbourne for time-critical goods.",
            },
        ],
    },
]


def generate_synthetic_dataset(num_shipments: int = 35, seed: int = 42) -> List[Shipment]:
    """
    Generates realistic shipments with 3 to 5 multi-leg route options each.
    Ensures mathematical realism:
      - Air routes are fast, expensive, low congestion risk, high carbon.
      - Cape of Good Hope routes bypass Red Sea geopolitical risk, but take more time and fuel.
      - Transshipment routes are cheaper, but incur higher dwell time, delay probabilities, and port congestion.
    """
    random.seed(seed)
    shipments: List[Shipment] = []

    cargo_types = list(CargoType)

    for i in range(1, num_shipments + 1):
        corridor_info = TRADE_CORRIDORS[(i - 1) % len(TRADE_CORRIDORS)]
        shipment_id = f"SHP-{i:03d}"

        # Contextual cargo selection
        if corridor_info["name"].startswith("Transatlantic") and i % 3 == 0:
            cargo = CargoType.PHARMA
        elif corridor_info["name"].startswith("Transpacific") and i % 2 == 0:
            cargo = CargoType.HIGH_VALUE
        elif "Middle East" in corridor_info["name"] and i % 2 == 1:
            cargo = CargoType.PERISHABLE
        else:
            cargo = random.choice(cargo_types)

        # Realistic container load / weight / value
        container_count = random.choice([1, 2, 4, 10])
        cargo_weight_kg = container_count * random.uniform(14000, 22000)

        if cargo == CargoType.HIGH_VALUE:
            cargo_value_usd = container_count * random.uniform(250000, 950000)
            priority = random.choice(["High", "Critical"])
        elif cargo == CargoType.PHARMA:
            cargo_value_usd = container_count * random.uniform(180000, 600000)
            priority = random.choice(["High", "Critical"])
        elif cargo == CargoType.PERISHABLE:
            cargo_value_usd = container_count * random.uniform(40000, 110000)
            priority = "High"
        else:
            cargo_value_usd = container_count * random.uniform(25000, 85000)
            priority = random.choice(["Standard", "Standard", "High"])

        # Construct 3 to 5 route options for this shipment
        routes: List[RouteOption] = []
        archetypes = corridor_info["archetypes"]

        # Maybe select 3, 4, or all 5 archetypes depending on corridor
        selected_archetypes = archetypes

        for idx, arch in enumerate(selected_archetypes, start=1):
            route_id = f"R-{shipment_id}-{idx:02d}"

            # Add minor operational variability per shipment
            jitter_factor = random.uniform(0.95, 1.06)

            min_time, max_time = arch["transit_time_days"]
            transit_time = round(random.uniform(min_time, max_time) * jitter_factor, 1)

            min_cost, max_cost = arch["cost_base_teu"]
            base_teu_cost = random.uniform(min_cost, max_cost) * jitter_factor
            total_cost = round(base_teu_cost * container_count, 2)

            delay_prob = round(min(0.95, max(0.05, arch["delay_prob"] * random.uniform(0.92, 1.08))), 3)
            congestion_risk = round(min(0.98, max(0.05, arch["congestion_risk"] * random.uniform(0.92, 1.08))), 3)
            geopolitical_risk = round(min(0.98, max(0.02, arch["geopolitical_risk"] * random.uniform(0.95, 1.05))), 3)
            weather_risk = round(min(0.95, max(0.05, arch["weather_risk"] * random.uniform(0.92, 1.08))), 3)

            # Carbon emission calculation (kg CO2)
            base_ocean_co2_per_teu = corridor_info["distance_approx_km"] * 0.035
            carbon_emissions = round(
                base_ocean_co2_per_teu * arch["carbon_factor"] * container_count * random.uniform(0.95, 1.05),
                1,
            )

            # Composite operational risk: 40% delay, 35% geopolitical, 25% congestion
            composite_risk = round(
                (0.40 * delay_prob) + (0.35 * geopolitical_risk) + (0.25 * congestion_risk),
                3,
            )

            # Generate concrete legs with realistic jitter
            legs: List[RouteLeg] = []
            for l_idx, leg_tpl in enumerate(arch["legs"], start=1):
                (l_orig, l_dest, l_mode, l_days, l_cost, l_dprob, l_cong, l_geo, l_weath, l_carb) = leg_tpl
                leg_obj = RouteLeg(
                    leg_id=f"{route_id}-L{l_idx}",
                    origin=l_orig,
                    destination=l_dest,
                    mode=l_mode.value if hasattr(l_mode, "value") else str(l_mode),
                    carrier_type="Contracted Freight Partner",
                    transit_time_days=round(l_days * random.uniform(0.94, 1.06), 1),
                    cost_usd=round(l_cost * container_count * random.uniform(0.94, 1.06), 2),
                    delay_prob=round(min(0.95, max(0.02, l_dprob * random.uniform(0.90, 1.10))), 3),
                    congestion_risk=round(min(0.95, max(0.02, l_cong * random.uniform(0.90, 1.10))), 3),
                    geopolitical_risk=round(min(0.95, max(0.01, l_geo * random.uniform(0.95, 1.05))), 3),
                    weather_risk=round(min(0.95, max(0.02, l_weath * random.uniform(0.90, 1.10))), 3),
                    carbon_kg=round(l_carb * container_count * random.uniform(0.95, 1.05), 1),
                )
                legs.append(leg_obj)

            intermediate_nodes = [leg.origin for leg in legs[1:]]

            route_obj = RouteOption(
                route_id=route_id,
                name=arch["name"],
                strategy_type=arch["strategy"],
                legs=legs,
                total_cost_usd=total_cost,
                estimated_transit_time_days=transit_time,
                delay_probability=delay_prob,
                congestion_risk=congestion_risk,
                geopolitical_risk=geopolitical_risk,
                weather_risk=weather_risk,
                carbon_emissions_kg=carbon_emissions,
                composite_risk_score=composite_risk,
                intermediate_nodes=intermediate_nodes,
                description=arch["description"],
            )
            routes.append(route_obj)

        # Baseline budget and target days heuristic
        avg_cost = sum(r.total_cost_usd for r in routes) / len(routes)
        min_time = min(r.estimated_transit_time_days for r in routes)
        max_time = max(r.estimated_transit_time_days for r in routes)

        target_delivery = round(min_time + (max_time - min_time) * (0.35 if priority != "Standard" else 0.65), 1)
        budget = round(avg_cost * 1.35, 2)

        shipment = Shipment(
            shipment_id=shipment_id,
            origin=corridor_info["origin"],
            origin_country=corridor_info["origin_country"],
            destination=corridor_info["destination"],
            destination_country=corridor_info["destination_country"],
            corridor=corridor_info["name"],
            cargo_type=cargo,
            cargo_weight_kg=round(cargo_weight_kg, 1),
            cargo_value_usd=round(cargo_value_usd, 2),
            priority_level=priority,
            max_budget_usd=budget,
            target_delivery_days=target_delivery,
            routes=routes,
        )
        shipments.append(shipment)

    return shipments


def save_dataset_to_files(shipments: List[Shipment], json_path: str, csv_path: str) -> None:
    """Saves generated dataset to JSON and CSV formats."""
    # 1. JSON
    data_dict = [s.to_dict() for s in shipments]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=2)

    # 2. Flat CSV for tabular inspection & reporting
    fieldnames = [
        "shipment_id",
        "corridor",
        "origin",
        "destination",
        "cargo_type",
        "cargo_weight_kg",
        "cargo_value_usd",
        "priority_level",
        "target_delivery_days",
        "max_budget_usd",
        "route_id",
        "route_name",
        "strategy_type",
        "total_cost_usd",
        "transit_time_days",
        "delay_probability",
        "congestion_risk",
        "geopolitical_risk",
        "weather_risk",
        "carbon_emissions_kg",
        "composite_risk_score",
        "num_legs",
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in shipments:
            for r in s.routes:
                writer.writerow({
                    "shipment_id": s.shipment_id,
                    "corridor": s.corridor,
                    "origin": s.origin,
                    "destination": s.destination,
                    "cargo_type": s.cargo_type.value if hasattr(s.cargo_type, "value") else str(s.cargo_type),
                    "cargo_weight_kg": s.cargo_weight_kg,
                    "cargo_value_usd": s.cargo_value_usd,
                    "priority_level": s.priority_level,
                    "target_delivery_days": s.target_delivery_days,
                    "max_budget_usd": s.max_budget_usd,
                    "route_id": r.route_id,
                    "route_name": r.name,
                    "strategy_type": r.strategy_type,
                    "total_cost_usd": r.total_cost_usd,
                    "transit_time_days": r.estimated_transit_time_days,
                    "delay_probability": r.delay_probability,
                    "congestion_risk": r.congestion_risk,
                    "geopolitical_risk": r.geopolitical_risk,
                    "weather_risk": r.weather_risk,
                    "carbon_emissions_kg": r.carbon_emissions_kg,
                    "composite_risk_score": r.composite_risk_score,
                    "num_legs": len(r.legs),
                })


if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)
    generated = generate_synthetic_dataset(num_shipments=35, seed=42)
    save_dataset_to_files(generated, "data/shipments.json", "data/routes_flat.csv")
    print(f"Generated {len(generated)} shipments with {sum(len(s.routes) for s in generated)} total route options.")
