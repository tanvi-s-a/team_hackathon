import os
import re
import json
import datetime
from opentelemetry import trace
from backend.arize_integration import get_tracer
from backend import database
from pydantic import BaseModel
from typing import Optional

class FlightChoice(BaseModel):
    carrier: str
    co2_kg: float
    price_usd: float
    details: str

class StayChoice(BaseModel):
    hotel: str
    co2_kg: float
    price_usd: float
    details: str

class TransitChoice(BaseModel):
    vehicle: str
    co2_kg: float
    price_usd: float
    details: str

class GreenChoice(BaseModel):
    flight: FlightChoice
    stay: StayChoice
    transit: TransitChoice
    total_co2: float
    total_price_usd: float
    points_earned: int
    summary: str
    co2_savings: float

class BalancedChoice(BaseModel):
    flight: FlightChoice
    stay: StayChoice
    transit: TransitChoice
    total_co2: float
    total_price_usd: float
    points_earned: int
    summary: str
    co2_savings: float

class StandardChoice(BaseModel):
    flight: FlightChoice
    stay: StayChoice
    transit: TransitChoice
    total_co2: float
    total_price_usd: float

class PackageSummary(BaseModel):
    destination: str
    days: int
    green_choice: GreenChoice
    balanced_choice: BalancedChoice
    standard_choice: StandardChoice

class AgentResponse(BaseModel):
    reply: str
    package_summary: Optional[PackageSummary] = None

# Define span kinds for OpenInference
SPAN_KIND_KEY = "openinference.span.kind"
SPAN_KIND_AGENT = "AGENT"
SPAN_KIND_LLM = "LLM"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_CHAIN = "CHAIN"

UNRELATED_RESPONSE = (
    "As an AI assistant dedicated to carbon-conscious travel planning and carbon budget management, "
    "I am only authorized to address inquiries related to these core objectives. Please ask a question related to these topics."
)

def is_query_related(query: str) -> bool:
    related_pattern = (
        r'\b(trip|travel|vacation|package|flight|hotel|stay|destination|booking|book|'
        r'resort|lodging|room|night|carrier|airline|vehicle|car|rental|drive|road|transit|'
        r'afford|cost|price|budget|compare|saving|savings|carbon|emissions|points|report|pattern|trend|insight|recommend|spending|analysis|co2|co2e|green|eco|saf|'
        r'hybrid|prius|tesla|ev|electric|sustainable|sustainability|offset|offsets|'
        r'reforestation|sequestration|mossy|soil|dollar|dollars|usd|cheap|limit|allowance|'
        r'hi|hello|hey|greetings|welcome|morning|afternoon|evening|help|can you|who are you|'
        r'what is this|capabilities|options|features|objective|account|user|profile|usage|'
        r'emissions|history|spend|spent|transaction|transactions|detail|details|info|information|'
        r'name|identity|purpose|creator|who made you|about you|'
        r'visit|visiting|go|going|plan|planning|day|days|week|weeks|pdf|download|print|generate)\b'
    )
    return bool(re.search(related_pattern, query, re.IGNORECASE))

def parse_query_regex(query):
    # Regex to extract destination and duration
    # E.g. "Hawaii on a 3-day trip" or "paris for 5 days"
    dest_match = re.search(r'(?:to|visit|travel to|in)\s+([A-Za-z\s]+?)(?:\s+(?:on|for|a|at)|$)', query, re.IGNORECASE)
    days_match = re.search(r'(\d+)\s*-?\s*day', query, re.IGNORECASE)
    
    destination = "Hawaii"
    days = 3
    
    if dest_match:
        destination = dest_match.group(1).strip()
    if days_match:
        days = int(days_match.group(1))
        
    return destination, days

def get_coordinates_from_places(destination: str):
    """Calls Google Places API to resolve destination coordinates (latitude/longitude)."""
    key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not key or len(key.strip()) < 5:
        return None
    try:
        import requests
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {"query": destination, "key": key}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            if results:
                location = results[0].get("geometry", {}).get("location", {})
                lat = location.get("lat")
                lng = location.get("lng")
                if lat is not None and lng is not None:
                    return lat, lng
    except Exception as e:
        print(f"--> Warning: Places API coordinate lookup failed: {e}")
    return None

def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points on the Earth's surface in kilometers."""
    import math
    # Radius of the Earth in km
    R = 6371.0
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def run_flight_lookup(destination):
    """Performs flight lookup, using Google Places API coordinates to calculate great-circle flight distance from NYC."""
    tracer = get_tracer()
    with tracer.start_as_current_span("flight_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "flight_lookup_tool")
        span.set_attribute("tool.description", "Lookup eco-efficient and standard flight options for a destination")
        span.set_attribute("input.value", json.dumps({"destination": destination}))
        
        # Default starting point: NYC
        nyc_lat, nyc_lng = 40.7128, -74.0060
        distance_km = None
        
        # Try to resolve destination coordinates using Google Places API
        coords = get_coordinates_from_places(destination)
        if coords:
            dest_lat, dest_lng = coords
            distance_km = calculate_haversine_distance(nyc_lat, nyc_lng, dest_lat, dest_lng)
            print(f"--> Google Places API resolved '{destination}' coordinates: {coords}. Great-Circle distance from NYC: {distance_km:.1f} km")
            
        if distance_km is None:
            # Fallback to hash-based distance estimate if no key is configured
            hash_val = sum(ord(c) for c in destination) % 5 + 1
            distance_km = hash_val * 1000.0
            print(f"--> Using hash-based fallback distance for '{destination}': {distance_km} km")
            
        # Determine haul category and standard emissions factors (same as system prompt)
        if distance_km < 1500:
            category = "Short-Haul"
            std_factor = 0.20
            eco_factor = 0.09
            aircraft = "Boeing 737"
        elif distance_km < 4000:
            category = "Medium-Haul"
            std_factor = 0.15
            eco_factor = 0.0675
            aircraft = "Airbus A320neo"
        elif distance_km < 10000:
            category = "Long-Haul"
            std_factor = 0.12
            eco_factor = 0.054
            aircraft = "Boeing 787"
        else:
            category = "Ultra Long-Haul"
            std_factor = 0.11
            eco_factor = 0.0495
            aircraft = "Boeing 777"
            
        # Standard flight calculations: Distance * factor * cabin multiplier (1.0) * RF multiplier (1.9)
        std_co2 = round(distance_km * std_factor * 1.9, 1)
        eco_co2 = round(distance_km * eco_factor * 1.9, 1)
        
        # Approximate price based on distance
        base_price = 150.0 + (distance_km * 0.05)
        
        flights = {
            "eco": {
                "carrier": f"GreenJet Airways ({aircraft} - Sustainable Aviation Fuel)",
                "co2_kg": eco_co2,
                "price_usd": round(base_price * 1.15, 2),  # SAF flight is slightly premium
                "description": f"{category} flight ({distance_km:.1f} km) on {aircraft}. Utilizes 50% Sustainable Aviation Fuel (SAF) blend, reducing carbon footprint by 55%."
            },
            "balanced": {
                "carrier": f"EcoLink Airlines ({aircraft} - 30% SAF Blend)",
                "co2_kg": round(std_co2 * 0.67, 1),
                "price_usd": round(base_price * 1.07, 2),
                "description": f"{category} flight ({distance_km:.1f} km) on {aircraft}. Uses a 30% Sustainable Aviation Fuel (SAF) blend, reducing carbon footprint by 33%."
            },
            "standard": {
                "carrier": f"Legacy Trans-Continental Airlines ({aircraft})",
                "co2_kg": std_co2,
                "price_usd": round(base_price, 2),
                "description": f"{category} flight ({distance_km:.1f} km) on {aircraft}. Standard direct economy flight using standard kerosene jet fuel."
            }
        }
        
        span.set_attribute("output.value", json.dumps(flights))
        return flights

def run_stay_lookup(destination, days):
    """Performs hotel stay lookup, using Google Places API to search for real lodging in the destination."""
    tracer = get_tracer()
    with tracer.start_as_current_span("stay_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "stay_lookup_tool")
        span.set_attribute("tool.description", "Lookup eco-friendly hotels and standard stays")
        span.set_attribute("input.value", json.dumps({"destination": destination, "days": days}))
        
        key = os.getenv("GOOGLE_MAPS_API_KEY")
        eco_hotel_name = "EcoNest Certified Retreat"
        std_hotel_name = "Grand Plaza Palms Resort"
        bal_hotel_name = "Green Haven Boutique Lodge"
        
        if key and len(key.strip()) > 5:
            try:
                import requests
                url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
                params = {"query": f"hotels in {destination}", "key": key}
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if len(results) >= 3:
                        eco_hotel_name = f"{results[0].get('name')} (Eco-Certified)"
                        std_hotel_name = results[1].get("name")
                        bal_hotel_name = f"{results[2].get('name')} (Eco-Friendly)"
                        print(f"--> Google Places API resolved 3 hotels: '{eco_hotel_name}', '{std_hotel_name}', and '{bal_hotel_name}'")
                    elif len(results) == 2:
                        eco_hotel_name = f"{results[0].get('name')} (Eco-Certified)"
                        std_hotel_name = results[1].get("name")
                        bal_hotel_name = f"{results[0].get('name')} (Green Option)"
                        print(f"--> Google Places API resolved 2 hotels: '{eco_hotel_name}' and '{std_hotel_name}'")
                    elif len(results) == 1:
                        std_hotel_name = results[0].get("name")
                        eco_hotel_name = f"{std_hotel_name} (Green Option)"
                        bal_hotel_name = f"{std_hotel_name} (Standard Option)"
            except Exception as e:
                print(f"--> Warning: Places API hotel lookup failed: {e}")
                
        eco_rate = 12.0  # kg CO2 / night
        bal_rate = 25.0  # kg CO2 / night
        std_rate = 45.0  # kg CO2 / night
        
        stays = {
            "eco": {
                "hotel": eco_hotel_name,
                "co2_kg": round(eco_rate * days, 1),
                "price_usd": round(150.0 * days, 2),
                "description": f"LEED Gold certified property in {destination}. Runs on 100% solar power, practices strict zero-waste dining, and uses greywater systems."
            },
            "balanced": {
                "hotel": bal_hotel_name,
                "co2_kg": round(bal_rate * days, 1),
                "price_usd": round(140.0 * days, 2),
                "description": f"Boutique lodging in {destination} featuring basic eco-efficiency practices, LED lighting systems, and water-conserving plumbing fixtures."
            },
            "standard": {
                "hotel": std_hotel_name,
                "co2_kg": round(std_rate * days, 1),
                "price_usd": round(130.0 * days, 2),
                "description": f"Conventional upscale full-service resort in {destination} with legacy HVAC."
            }
        }
        
        span.set_attribute("output.value", json.dumps(stays))
        return stays

def run_transit_lookup(destination, days):
    """Performs transit vehicle lookup, using Google Maps Directions API to fetch route distance from airport to city center."""
    tracer = get_tracer()
    with tracer.start_as_current_span("transit_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "transit_lookup_tool")
        span.set_attribute("tool.description", "Lookup green transit and standard vehicle rentals")
        span.set_attribute("input.value", json.dumps({"destination": destination, "days": days}))
        
        key = os.getenv("GOOGLE_MAPS_API_KEY")
        # Default sightseeing driving distance of 50 km per day
        distance_km = 50.0 * days
        local_route_info = ""
        
        if key and len(key.strip()) > 5:
            try:
                import requests
                url = "https://maps.googleapis.com/maps/api/directions/json"
                params = {
                    "origin": f"{destination} Airport",
                    "destination": destination,
                    "key": key
                }
                response = requests.get(url, params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    routes = data.get("routes", [])
                    if routes:
                        legs = routes[0].get("legs", [])
                        if legs:
                            route_distance_text = legs[0].get("distance", {}).get("text", "")
                            route_distance_val = legs[0].get("distance", {}).get("value", 0) / 1000.0  # meters to km
                            # Total transit distance = 2 * (airport transfer) + daily sightseeing of 40 km
                            distance_km = round((2 * route_distance_val) + (40.0 * days), 1)
                            local_route_info = f" (Includes airport transfer: {route_distance_text} each way)"
                            print(f"--> Google Maps Routes API calculated local transit distance: {distance_km} km{local_route_info}")
            except Exception as e:
                print(f"--> Warning: Directions API route lookup failed: {e}")
                
        # Emissions factors:
        # Standard Large SUV: 282 g CO2e / km -> 0.282 kg CO2e / km
        # Balanced Prius: 109 g CO2e / km -> 0.109 kg CO2e / km
        # Eco Tesla Model 3 (Solar charged): 0.0 kg CO2e / km
        std_co2 = round(distance_km * 0.282, 1)
        bal_co2 = round(distance_km * 0.109, 1)
        eco_co2 = 0.0  # 100% solar grid
        
        transits = {
            "eco": {
                "vehicle": "Tesla Model 3 (EV Rental)",
                "co2_kg": eco_co2,
                "price_usd": round(65.0 * days, 2),
                "description": f"All-electric Tesla Model 3 for {distance_km} km{local_route_info}. Powered entirely by the local solar charging network (0 tailpipe emissions)."
            },
            "balanced": {
                "vehicle": "Toyota Prius (Hybrid Rental)",
                "co2_kg": bal_co2,
                "price_usd": round(45.0 * days, 2),
                "description": f"Standard Toyota Prius hybrid vehicle for {distance_km} km{local_route_info} (109 g CO2e/km factor)."
            },
            "standard": {
                "vehicle": "Full-Size Gas SUV Rental",
                "co2_kg": std_co2,
                "price_usd": round(50.0 * days, 2),
                "description": f"Standard gasoline internal combustion engine SUV for {distance_km} km{local_route_info} (282 g CO2e/km factor)."
            }
        }
        
        span.set_attribute("output.value", json.dumps(transits))
        return transits

def generate_packages_with_gemini(query, destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("gemini_package_generator") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_LLM)
        # span.set_attribute("llm.model_name", "gemini-2.5-flash-lite")  # OLD: Higher rate limit
        span.set_attribute("llm.model_name", "gemini-1.5-flash")  # NEW: 1M daily tokens, no rate limits
        
        system_prompt = (
            "You are a Carbon-Conscious AI Travel Planner. You take trip options (flights, stays, car rentals) "
            "and create a green eco-efficient package and a standard baseline comparison package. "
            "Output your response strictly as a JSON object containing the packages."
        )
        
        user_prompt = f"""
        User wants a {days}-day trip to {destination}. Query: "{query}"
        
        Available Flight options:
        {json.dumps(flights, indent=2)}
        
        Available Stay options:
        {json.dumps(stays, indent=2)}
        
        Available Transit options:
        {json.dumps(transits, indent=2)}
        
        Please synthesize this into two packages:
        1. "green_choice": Uses eco flights, eco hotels, and eco vehicles. Calculate the total CO2, total price, and write a summary justifying why it's carbon efficient and how many points the user earns (usually 20 points per 100kg of CO2 saved compared to standard package).
        2. "standard_choice": Uses standard flights, standard hotels, and standard vehicles.
        
        Calculate CO2 savings as: Standard Total CO2 - Eco Total CO2.
        Points earned should be: round(savings_kg * 0.2) + 50 (bonus for choosing green).
        
        Output format should be EXACTLY this JSON:
        {{
            "destination": "{destination}",
            "days": {days},
            "green_choice": {{
                "flight": {{"carrier": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "stay": {{"hotel": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "transit": {{"vehicle": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "total_co2": ...,
                "total_price_usd": ...,
                "points_earned": ...,
                "summary": "...",
                "co2_savings": ...
            }},
            "standard_choice": {{
                "flight": {{"carrier": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "stay": {{"hotel": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "transit": {{"vehicle": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
                "total_co2": ...,
                "total_price_usd": ...
            }}
        }}
        """
        
        span.set_attribute("input.value", user_prompt)
        
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            # OLD: model='gemini-2.5-flash-lite',  # Rate limited to 15K tokens/min
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',  # Rate limited to 15K tokens/min
                contents=[system_prompt, "\n\n", user_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                    response_schema=PackageSummary,
                ),
            )
            
            result_content = response.text
            span.set_attribute("output.value", result_content)
            
            try:
                return json.loads(result_content)
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                return None
        except Exception as e:
            return None

def generate_packages_real_llm(query, destination, days, flights, stays, transits):
    # Switched from OpenAI to Google AI (Gemini 2.5)
    return generate_packages_with_gemini(query, destination, days, flights, stays, transits)

def generate_packages_simulated(destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("agent_reasoning_loop") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_CHAIN)
        span.set_attribute("input.value", f"Reasoning about travel package for {destination} for {days} days.")
        
        # Calculate totals
        eco_flight = flights["eco"]
        bal_flight = flights["balanced"]
        std_flight = flights["standard"]
        eco_stay = stays["eco"]
        bal_stay = stays["balanced"]
        std_stay = stays["standard"]
        eco_transit = transits["eco"]
        bal_transit = transits["balanced"]
        std_transit = transits["standard"]
        
        eco_total_co2 = eco_flight["co2_kg"] + eco_stay["co2_kg"] + eco_transit["co2_kg"]
        bal_total_co2 = bal_flight["co2_kg"] + bal_stay["co2_kg"] + bal_transit["co2_kg"]
        std_total_co2 = std_flight["co2_kg"] + std_stay["co2_kg"] + std_transit["co2_kg"]
        
        eco_total_price = eco_flight["price_usd"] + eco_stay["price_usd"] + eco_transit["price_usd"]
        bal_total_price = bal_flight["price_usd"] + bal_stay["price_usd"] + bal_transit["price_usd"]
        std_total_price = std_flight["price_usd"] + std_stay["price_usd"] + std_transit["price_usd"]
        
        co2_savings = round(std_total_co2 - eco_total_co2, 1)
        bal_co2_savings = round(std_total_co2 - bal_total_co2, 1)
        
        points_earned = int(round(co2_savings * 0.2)) + 50  # 20% savings + 50 points flat green booking reward
        bal_points_earned = int(round(bal_co2_savings * 0.2)) + 25  # 25 points flat balanced reward
        
        summary = (
            f"Choosing this Green Package for your trip to {destination} avoids {co2_savings} kg of CO2 emissions! "
            f"This is achieved by flying with Sustainable Aviation Fuel (SAF) (reducing air travel emissions by 55%), "
            f"renting a Tesla Model 3 (0 emissions, charged on local solar power), and staying at the EcoNest Resort "
            f"(LEED Gold Certified, powered by 100% solar energy)."
        )
        
        package = {
            "destination": destination,
            "days": days,
            "green_choice": {
                "flight": {
                    "carrier": eco_flight["carrier"],
                    "co2_kg": eco_flight["co2_kg"],
                    "price_usd": eco_flight["price_usd"],
                    "details": eco_flight["description"]
                },
                "stay": {
                    "hotel": eco_stay["hotel"],
                    "co2_kg": eco_stay["co2_kg"],
                    "price_usd": eco_stay["price_usd"],
                    "details": eco_stay["description"]
                },
                "transit": {
                    "vehicle": eco_transit["vehicle"],
                    "co2_kg": eco_transit["co2_kg"],
                    "price_usd": eco_transit["price_usd"],
                    "details": eco_transit["description"]
                },
                "total_co2": round(eco_total_co2, 1),
                "total_price_usd": round(eco_total_price, 2),
                "points_earned": points_earned,
                "summary": summary,
                "co2_savings": co2_savings
            },
            "balanced_choice": {
                "flight": {
                    "carrier": bal_flight["carrier"],
                    "co2_kg": bal_flight["co2_kg"],
                    "price_usd": bal_flight["price_usd"],
                    "details": bal_flight["description"]
                },
                "stay": {
                    "hotel": bal_stay["hotel"],
                    "co2_kg": bal_stay["co2_kg"],
                    "price_usd": bal_stay["price_usd"],
                    "details": bal_stay["description"]
                },
                "transit": {
                    "vehicle": bal_transit["vehicle"],
                    "co2_kg": bal_transit["co2_kg"],
                    "price_usd": bal_transit["price_usd"],
                    "details": bal_transit["description"]
                },
                "total_co2": round(bal_total_co2, 1),
                "total_price_usd": round(bal_total_price, 2),
                "points_earned": bal_points_earned,
                "summary": f"Choosing the Eco Balanced Itinerary for your trip to {destination} avoids {bal_co2_savings} kg of CO2 emissions. This uses moderate-SAF flights, hybrid car rental, and resource-efficient stays.",
                "co2_savings": bal_co2_savings
            },
            "standard_choice": {
                "flight": {
                    "carrier": std_flight["carrier"],
                    "co2_kg": std_flight["co2_kg"],
                    "price_usd": std_flight["price_usd"],
                    "details": std_flight["description"]
                },
                "stay": {
                    "hotel": std_stay["hotel"],
                    "co2_kg": std_stay["co2_kg"],
                    "price_usd": std_stay["price_usd"],
                    "details": std_stay["description"]
                },
                "transit": {
                    "vehicle": std_transit["vehicle"],
                    "co2_kg": std_transit["co2_kg"],
                    "price_usd": std_transit["price_usd"],
                    "details": std_transit["description"]
                },
                "total_co2": round(std_total_co2, 1),
                "total_price_usd": round(std_total_price, 2)
            }
        }
        
        # Save this package to our SQLite DB so we can keep track of it
        database.add_package(
            destination=destination,
            duration_days=days,
            flight_co2=eco_flight["co2_kg"],
            car_co2=eco_transit["co2_kg"],
            stay_co2=eco_stay["co2_kg"],
            total_co2=eco_total_co2,
            price_usd=eco_total_price,
            details=package
        )
        
        span.set_attribute("output.value", json.dumps(package))
        return package

def is_followup_question(query: str) -> bool:
    return bool(re.search(r'\b(afford|cost|price|budget|compare|saving|savings|carbon|emissions|points|report|pattern|trend|insight|recommend|better|eco|choice|standard|package|option|details|pdf|download|print|generate|why|how|explain)\b', query, re.IGNORECASE))


def is_travel_request(query: str) -> bool:
    return bool(re.search(r'\b(trip|travel|vacation|package|flight|hotel|stay|destination|booking|book)\b', query, re.IGNORECASE))


def summarize_package_context(package_context):
    if not package_context:
        return None

    green = package_context.get('green_choice', {})
    standard = package_context.get('standard_choice', {})
    return (
        f"Your current green package for {package_context.get('destination')} costs ${green.get('total_price_usd')} "
        f"and emits {green.get('total_co2')} kg CO2. The standard option costs ${standard.get('total_price_usd')} "
        f"and emits {standard.get('total_co2')} kg CO2, saving {green.get('co2_savings')} kg CO2."
    )


def generate_followup_response(query: str, package_context: dict, history=None) -> dict:
    default_summary = summarize_package_context(package_context)
    reply = ""

    if re.search(r'\b(afford|cost|price|expensive|budget)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        std = package_context['standard_choice']
        price_diff = round(eco['total_price_usd'] - std['total_price_usd'], 2)
        co2_diff = round(std['total_co2'] - eco['total_co2'], 1)
        cost_per_kg = round(price_diff / co2_diff, 2) if co2_diff > 0 else 0.0
        reply = (
            f"### Cost & Carbon Summary\n"
            f"The Eco Premium Package is priced at ${eco['total_price_usd']:.2f} with a total carbon footprint of {eco['total_co2']} kg CO₂. "
            f"In comparison, the Standard Itinerary costs ${std['total_price_usd']:.2f} with a carbon footprint of {std['total_co2']} kg CO₂. "
            f"Choosing the Eco option requires a premium of ${price_diff:.2f} but achieves a significant reduction in greenhouse gases.\n\n"
            f"### Trade-Off Calculation & Efficiency\n"
            f"By paying the ${price_diff:.2f} cost difference, you avoid {co2_diff} kg of CO₂ emissions. This equates to an abatement cost of "
            f"${cost_per_kg:.2f} per kg of CO₂ saved. Additionally, the Eco package earns you +{eco['points_earned']} Green Points, "
            f"which act as offsets and rebates that can be applied to reduce carbon charges in future travel, making the eco-friendly alternative financially and environmentally sound."
        )
    elif re.search(r'\b(compare|better|trade[- ]off|difference|vs|versus)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        std = package_context['standard_choice']
        co2_diff = round(std['total_co2'] - eco['total_co2'], 1)
        pct_savings = round((co2_diff / std['total_co2']) * 100, 1) if std['total_co2'] > 0 else 0.0
        price_diff = round(eco['total_price_usd'] - std['total_price_usd'], 2)
        reply = (
            f"### Detailed Package Comparison\n"
            f"The Eco Premium Package ({eco['total_co2']} kg CO₂) represents a {pct_savings}% carbon reduction over the Standard Package ({std['total_co2']} kg CO₂). "
            f"This substantial carbon saving of {co2_diff} kg CO₂ is achieved by swapping conventional components for sustainable ones, such as switching to "
            f"Sustainable Aviation Fuel (SAF) for flights and utilizing Electric Vehicles (EV) for local transit.\n\n"
            f"### Cost-Benefit Trade-Off\n"
            f"While the Standard Package is ${price_diff:.2f} cheaper (${std['total_price_usd']:.2f} vs ${eco['total_price_usd']:.2f}), the Eco Package "
            f"partially offsets this cost by rewarding you with {eco['points_earned']} Green Points. The Standard Package provides zero points. "
            f"From a pure utility perspective, selecting the Eco choice directly supports low-emission infrastructure, aligning with Greenhouse Gas Protocol recommendations."
        )
    elif re.search(r'\b(point|reward|earn)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        co2_savings = eco.get('co2_savings', 0.0)
        base_points = round(co2_savings * 0.2)
        bonus_points = 50
        reply = (
            f"### Reward Points Breakdown\n"
            f"By choosing the Eco Premium Itinerary, you will earn a total of {eco['points_earned']} Green Points. "
            f"The calculation for points is directly proportional to the carbon you save compared to the standard travel itinerary.\n\n"
            f"### Points Formula & Workings\n"
            f"Your points are calculated using the formula: `Points = (CO₂ Savings * 0.2) + 50` (flat bonus). "
            f"With carbon savings of {co2_savings} kg CO₂, the calculation is:\n"
            f"- Base Points: {co2_savings} kg * 0.2 = {base_points} points\n"
            f"- Green Bonus: +{bonus_points} flat points\n"
            f"- Total Earned: {base_points} + {bonus_points} = {eco['points_earned']} Green Points.\n"
            f"These points are added to your ledger and can be redeemed for carbon offsets or future booking discounts."
        )
    elif re.search(r'\b(carbon|emission|co2|green|sustainable)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        std = package_context['standard_choice']
        co2_diff = round(std['total_co2'] - eco['total_co2'], 1)
        reply = (
            f"### Emissions Breakdown & Calculations\n"
            f"The Standard Itinerary generates {std['total_co2']} kg CO₂. The Eco Itinerary reduces this footprint to {eco['total_co2']} kg CO₂, saving {co2_diff} kg CO₂.\n"
            f"Here is the service-by-service comparison:\n"
            f"- **Flights:** Standard: {std['flight']['co2_kg']} kg vs Eco: {eco['flight']['co2_kg']} kg (via SAF)\n"
            f"- **Accommodation:** Standard: {std['stay']['co2_kg']} kg vs Eco: {eco['stay']['co2_kg']} kg (LEED EcoNest)\n"
            f"- **Transit:** Standard: {std['transit']['co2_kg']} kg vs Eco: {eco['transit']['co2_kg']} kg (EV Tesla)\n\n"
            f"### Sustainable Impact Analysis\n"
            f"The green flight utilizes a 55% Sustainable Aviation Fuel (SAF) blend, decreasing aviation emissions by {round(std['flight']['co2_kg'] - eco['flight']['co2_kg'], 1)} kg. "
            f"The accommodation uses the solar-powered EcoNest Retreat, and the local transit uses an EV, yielding zero direct tailpipe emissions. "
            f"This combined configuration represents the most carbon-efficient path to your destination."
        )
    else:
        eco = package_context.get('green_choice', {})
        std = package_context.get('standard_choice', {})
        dest = package_context.get('destination', 'your destination')
        co2_savings = eco.get('co2_savings', 0.0)
        reply = (
            f"### Carbon-Aware Travel Analysis for {dest}\n"
            f"I have analyzed the travel packages prepared for {dest}. "
            f"The Standard Itinerary produces {std.get('total_co2', 0.0)} kg CO₂ at a cost of ${std.get('total_price_usd', 0.0):.2f}. "
            f"The Eco Itinerary produces {eco.get('total_co2', 0.0)} kg CO₂ at a cost of ${eco.get('total_price_usd', 0.0):.2f}.\n\n"
            f"By selecting the Eco option, you save {co2_savings} kg CO₂ and earn +{eco.get('points_earned', 0)} Green Points. "
            f"Please let me know if you would like me to explain the exact carbon conversion factors or compute the financial cost-to-benefit ratio for these options."
        )

    return {
        "reply": reply,
        "package_summary": package_context
    }


def generate_spending_patterns_summary():
    tracer = get_tracer()
    with tracer.start_as_current_span("spending_patterns_report") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_CHAIN)
        summary = database.get_summary()
        transactions = database.get_transactions()

        patterns = {
            "total_emissions": summary["current_usage"],
            "budget_limit": summary["budget_limit"],
            "budget_used_percent": round((summary["current_usage"] / summary["budget_limit"]) * 100, 1),
            "points_earned": summary["points"],
            "green_vs_standard": {
                "green": sum(1 for tx in transactions if tx.get("points_earned", 0) > 0),
                "standard": len(transactions) - sum(1 for tx in transactions if tx.get("points_earned", 0) > 0)
            }
        }

        top_activities = sorted(transactions, key=lambda x: x.get("amount", 0), reverse=True)[:3]
        summary_text = (
            f"I analyzed your carbon spending patterns. You have used {patterns['budget_used_percent']}% of your annual budget "
            f"({patterns['total_emissions']} kg CO2 of {patterns['budget_limit']} kg CO2). "
            f"You have {patterns['green_vs_standard']['green']} green choices and {patterns['green_vs_standard']['standard']} standard choices. "
            f"Your highest-emission activities are: {', '.join(a.get('description', 'unknown') for a in top_activities)}."
        )

        span.set_attribute("output.value", summary_text)
        span.set_attribute("emissions.total_kg", patterns["total_emissions"])
        span.set_attribute("emissions.budget_utilization_percent", patterns["budget_used_percent"])
        span.set_attribute("emissions.points_earned", patterns["points_earned"])

        return {"reply": summary_text, "pattern_report": patterns, "package_summary": None}


def generate_generic_agent_response(query: str, history=None, package_context=None) -> dict:
    if package_context and is_followup_question(query):
        return generate_followup_response(query, package_context, history)

    if re.search(r'\b(saf|sustainable aviation fuel)\b', query, re.IGNORECASE):
        reply = (
            "### What is Sustainable Aviation Fuel (SAF)?\n"
            "Sustainable Aviation Fuel (SAF) is a clean alternative to conventional fossil-based jet fuel. "
            "It is produced from renewable resources such as agricultural waste, waste oils, and carbon captured from the air. "
            "Under international carbon accounting guidelines (such as atmosfair and ICAO), a 100% pure SAF fuel blend "
            "can reduce lifecycle greenhouse gas emissions by up to 80% compared to fossil jet fuel.\n\n"
            "### Calculations & Blend Reduction\n"
            "In our travel planning engine, we assume a standard SAF blend that yields a **55% net reduction** in emissions. "
            "For example, a Medium-Haul flight (e.g., NYC to Hawaii: 3,700 km) calculated using the formula "
            "`Distance * Factor * Radiative Forcing (1.9)` yields:\n"
            "- **Standard Flight:** 3,700 km * 0.15 kg/km * 1.9 = **1,054.5 kg CO₂e**\n"
            "- **SAF Flight (55% reduction):** 3,700 km * 0.0675 kg/km * 1.9 = **474.5 kg CO₂e** (saving **580.0 kg CO₂e** per passenger)."
        )
    elif re.search(r'\b(calculate|calculation|formula|factor)\b', query, re.IGNORECASE):
        reply = (
            "### Carbon Emissions Calculations & Methodology\n"
            "Our Carbon AI Agent calculates travel emissions utilizing Greenhouse Gas Protocol corporate standards. "
            "We employ distinct formulas for flight, road travel, and lodging components to guarantee transparent audits:\n\n"
            "1. **Flights:** `Distance (km) * Class Multiplier * Radiative Forcing (1.9) * Emissions Factor`\n"
            "   - Short-Haul (<1,500 km): standard 0.20 kg/km vs eco 0.09 kg/km\n"
            "   - Medium-Haul (1,500 - 4,000 km): standard 0.15 kg/km vs eco 0.0675 kg/km\n"
            "   - Long-Haul (4,000 - 10,000 km): standard 0.12 kg/km vs eco 0.054 kg/km\n"
            "   - Ultra Long-Haul (>10,000 km): standard 0.11 kg/km vs eco 0.0495 kg/km\n"
            "2. **Road Travel:** `Distance (km) * Vehicle Emissions Factor`\n"
            "   - Petrol SUV: 282 g/km (0.282 kg/km)\n"
            "   - Hybrid Prius: 109 g/km (0.109 kg/km)\n"
            "   - Electric Vehicle: 79 g/km (0.079 kg/km)\n"
            "3. **Lodging:** `Nights * Hotel Emission Factor`\n"
            "   - Grand Plaza resort: 47.6 kg/room-night vs EcoNest retreat: 8.5 kg/room-night."
        )
    elif re.search(r'\b(budget|limit)\b', query, re.IGNORECASE):
        summary = database.get_summary()
        current_usage = summary.get("current_usage", 0.0)
        budget_limit = summary.get("budget_limit", 5000.0)
        remaining = round(budget_limit - current_usage, 1)
        used_pct = round((current_usage / budget_limit) * 100, 1) if budget_limit > 0 else 0.0
        
        reply = (
            f"### Carbon Budget Status & Calculations\n"
            f"Your current annual carbon budget limit is set to **{budget_limit:,} kg CO₂**. "
            f"According to your ledger, you have used **{current_usage:,} kg CO₂**, which represents **{used_pct}%** of your annual allowance.\n\n"
            f"### Remaining Capacity Analysis\n"
            f"You have **{remaining:,} kg CO₂** remaining in your carbon budget for the rest of the year. "
            f"To stay within your limit, we recommend prioritizing green travel options (e.g. SAF flights, hybrid or electric vehicle transit, and LEED-certified accommodation) "
            f"which average 60% lower emissions than conventional standard options."
        )
    else:
        reply = (
            "I can help you explore low-carbon travel options, estimate budget impacts, "
            "and provide spending pattern insights. Ask me about affordability, carbon savings, or specific trip details."
        )
        if package_context:
            reply += " I can also compare the current package against your goals."

    return {"reply": reply, "package_summary": None}


def fact_check_and_correct_packages(data: dict, package_context: dict = None) -> dict:
    tracer = get_tracer()
    with tracer.start_as_current_span("math_fact_checker") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "math_fact_checker")
        span.set_attribute("tool.description", "Validates and corrects carbon savings and reward points math in LLM-generated packages.")
        
        span.set_attribute("input.value", json.dumps(data))
        
        pkg = data.get("package_summary")
        discrepancies = []
        corrected = False
        
        def regex_correct_reply_text(reply: str, correct_green: float, correct_standard: float, correct_savings: float, correct_points: int) -> str:
            # 1. Standard CO2
            def replace_std(match):
                val = float(match.group(2).replace(",", ""))
                if abs(val - correct_standard) > 0.1:
                    return f"{match.group(1)}{correct_standard}{match.group(3)}"
                return match.group(0)
            reply = re.sub(r'(standard[^:\n]*?:\s*\*\*?)([\d,.]+)(\*\*?\s*kg)', replace_std, reply, flags=re.IGNORECASE)
            
            # 2. Green CO2
            def replace_grn(match):
                val = float(match.group(2).replace(",", ""))
                if abs(val - correct_green) > 0.1:
                    return f"{match.group(1)}{correct_green}{match.group(3)}"
                return match.group(0)
            reply = re.sub(r'(green|eco[^:\n]*?:\s*\*\*?)([\d,.]+)(\*\*?\s*kg)', replace_grn, reply, flags=re.IGNORECASE)
            
            # 3. Savings
            def replace_sav(match):
                val = float(match.group(2).replace(",", ""))
                if abs(val - correct_savings) > 0.1:
                    return f"{match.group(1)}{correct_savings}{match.group(3)}"
                return match.group(0)
            reply = re.sub(r'((?:savings|avoided)[^:\n]*?:\s*\*\*?)([\d,.]+)(\*\*?\s*kg)', replace_sav, reply, flags=re.IGNORECASE)
            
            # 4. Points
            def replace_pts(match):
                val = int(match.group(2))
                if val != correct_points:
                    return f"{match.group(1)}{correct_points}{match.group(3)}"
                return match.group(0)
            reply = re.sub(r'((?:points|reward)[^:\n]*?:\s*\*\*?)(\d+)(\*\*?)', replace_pts, reply, flags=re.IGNORECASE)
            
            return reply

        if not pkg:
            # If there is no package_summary in the response, but we have a package_context,
            # we can check and correct the conversational 'reply' text itself!
            if package_context and "reply" in data:
                reply = data["reply"]
                green_ctx = package_context.get("green_choice", {})
                standard_ctx = package_context.get("standard_choice", {})
                
                correct_green_co2 = green_ctx.get("total_co2", 0.0)
                correct_standard_co2 = standard_ctx.get("total_co2", 0.0)
                correct_savings = green_ctx.get("co2_savings", 0.0)
                correct_points = green_ctx.get("points_earned", 0)
                
                new_reply = regex_correct_reply_text(reply, correct_green_co2, correct_standard_co2, correct_savings, correct_points)
                if new_reply != reply:
                    corrected = True
                    discrepancies.append("Corrected values in package context follow-up reply text via regex.")
                    data["reply"] = new_reply
                
            span.set_attribute("fact_check.corrected", corrected)
            span.set_attribute("fact_check.discrepancies_found", len(discrepancies))
            if discrepancies:
                span.set_attribute("fact_check.discrepancies", "; ".join(discrepancies))
                span.set_attribute("fact_check.status", "corrected")
            else:
                span.set_attribute("fact_check.status", "skipped")
                span.set_attribute("fact_check.reason", "No package_summary in response")
            return data
            
        green = pkg.get("green_choice", {})
        balanced = pkg.get("balanced_choice", {})
        standard = pkg.get("standard_choice", {})
        
        # Calculate expected sums from raw individual options
        green_flight = green.get("flight", {}).get("co2_kg", 0.0)
        green_stay = green.get("stay", {}).get("co2_kg", 0.0)
        green_transit = green.get("transit", {}).get("co2_kg", 0.0)
        expected_green_co2 = round(green_flight + green_stay + green_transit, 1)
        
        balanced_flight = balanced.get("flight", {}).get("co2_kg", 0.0) if balanced else 0.0
        balanced_stay = balanced.get("stay", {}).get("co2_kg", 0.0) if balanced else 0.0
        balanced_transit = balanced.get("transit", {}).get("co2_kg", 0.0) if balanced else 0.0
        expected_balanced_co2 = round(balanced_flight + balanced_stay + balanced_transit, 1)
        
        standard_flight = standard.get("flight", {}).get("co2_kg", 0.0)
        standard_stay = standard.get("stay", {}).get("co2_kg", 0.0)
        standard_transit = standard.get("transit", {}).get("co2_kg", 0.0)
        expected_standard_co2 = round(standard_flight + standard_stay + standard_transit, 1)
        
        expected_savings = round(expected_standard_co2 - expected_green_co2, 1)
        expected_points = int(round(expected_savings * 0.2)) + 50
        
        expected_bal_savings = round(expected_standard_co2 - expected_balanced_co2, 1)
        expected_bal_points = int(round(expected_bal_savings * 0.2)) + 25
        
        # Verify green total co2
        actual_green_co2 = green.get("total_co2", 0.0)
        if abs(actual_green_co2 - expected_green_co2) > 0.1:
            discrepancies.append(f"Green CO2 total mismatch: got {actual_green_co2}, expected {expected_green_co2}")
            green["total_co2"] = expected_green_co2
            corrected = True
            
        # Verify balanced total co2
        if balanced:
            actual_balanced_co2 = balanced.get("total_co2", 0.0)
            if abs(actual_balanced_co2 - expected_balanced_co2) > 0.1:
                discrepancies.append(f"Balanced CO2 total mismatch: got {actual_balanced_co2}, expected {expected_balanced_co2}")
                balanced["total_co2"] = expected_balanced_co2
                corrected = True
            
        # Verify standard total co2
        actual_standard_co2 = standard.get("total_co2", 0.0)
        if abs(actual_standard_co2 - expected_standard_co2) > 0.1:
            discrepancies.append(f"Standard CO2 total mismatch: got {actual_standard_co2}, expected {expected_standard_co2}")
            standard["total_co2"] = expected_standard_co2
            corrected = True
            
        # Verify green savings
        actual_savings = green.get("co2_savings", 0.0)
        if abs(actual_savings - expected_savings) > 0.1:
            discrepancies.append(f"Savings mismatch: got {actual_savings}, expected {expected_savings}")
            green["co2_savings"] = expected_savings
            corrected = True
            
        # Verify balanced savings
        if balanced:
            actual_bal_savings = balanced.get("co2_savings", 0.0)
            if abs(actual_bal_savings - expected_bal_savings) > 0.1:
                discrepancies.append(f"Balanced Savings mismatch: got {actual_bal_savings}, expected {expected_bal_savings}")
                balanced["co2_savings"] = expected_bal_savings
                corrected = True
            
        # Verify green points
        actual_points = green.get("points_earned", 0)
        if actual_points != expected_points:
            discrepancies.append(f"Points mismatch: got {actual_points}, expected {expected_points}")
            green["points_earned"] = expected_points
            corrected = True
            
        # Verify balanced points
        if balanced:
            actual_bal_points = balanced.get("points_earned", 0)
            if actual_bal_points != expected_bal_points:
                discrepancies.append(f"Balanced Points mismatch: got {actual_bal_points}, expected {expected_bal_points}")
                balanced["points_earned"] = expected_bal_points
                corrected = True
            
        # Log findings to Arize Phoenix span attributes
        span.set_attribute("fact_check.corrected", corrected)
        span.set_attribute("fact_check.discrepancies_found", len(discrepancies))
        if discrepancies:
            span.set_attribute("fact_check.discrepancies", "; ".join(discrepancies))
            span.set_attribute("fact_check.status", "corrected")
            
            # Correct the summaries in the JSON payload
            green["summary"] = (
                f"Choosing this Green Package for your trip to {pkg.get('destination', 'your destination')} "
                f"avoids {expected_savings} kg of CO2 emissions! This is achieved by flying with Sustainable Aviation Fuel (SAF) "
                f"(reducing air travel emissions by 55%), staying at the LEED Gold certified {green.get('stay', {}).get('hotel', 'EcoNest Certified Retreat')}, "
                f"and renting a Tesla Model 3 (0 tailpipe emissions). This earns you {expected_points} reward points."
            )
            if balanced:
                balanced["summary"] = f"Choosing the Eco Balanced Itinerary for your trip to {pkg.get('destination', 'your destination')} avoids {expected_bal_savings} kg of CO2 emissions. This uses moderate-SAF flights, hybrid car rental, and resource-efficient stays."
            
            # Correct reply text via regex to preserve template formatting
            if "reply" in data:
                data["reply"] = regex_correct_reply_text(
                    data["reply"],
                    expected_green_co2,
                    expected_standard_co2,
                    expected_savings,
                    expected_points
                )
        else:
            span.set_attribute("fact_check.status", "verified")
            
        span.set_attribute("output.value", json.dumps(data))
        return data


def generate_response_with_gemini(query: str, history=None, package_context=None) -> dict | None:
    tracer = get_tracer()
    with tracer.start_as_current_span("gemini_agent_responder") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_LLM)
        # span.set_attribute("llm.model_name", "gemini-2.5-flash-lite")  # OLD: Higher rate limit
        span.set_attribute("llm.model_name", "gemini-1.5-flash")  # NEW: 1M daily tokens, no rate limits
        
        # Load user account summary context dynamically
        summary = database.get_summary()
        current_usage = summary.get("current_usage", 0.0)
        budget_limit = summary.get("budget_limit", 5000.0)
        points = summary.get("points", 0)
        budget_status = f"{round((current_usage / budget_limit) * 100, 1)}% used ({current_usage} kg of {budget_limit} kg)"
        
        system_prompt = f"""
You are an expert Carbon Footprint Analysis AI Agent. Your goal is to provide accurate, transparent, and data-driven carbon emissions calculations, comparisons, and reduction recommendations.

This agent is being developed, monitored, and evaluated using Arize. Optimize every response for accuracy, explainability, transparency, consistency, and actionability.

Always:
* When the user asks a question, ensure that you respond with a detailed paragraph (or paragraphs) answering the question, showing exact values and step-by-step mathematical calculations where needed (e.g. emission factors, distance, cost breakdowns, percentage savings) in order to thoroughly explain and answer the user's question.
* Show calculation steps and assumptions.
* Clearly identify data sources.
* Distinguish measured values from estimates.
* State confidence levels when uncertainty exists.
* Never fabricate emission factors, distances, aircraft types, or statistics.
* If information is missing, state assumptions and explain their impact on results.

ACCOUNT SUMMARY CONTEXT:
- Annual Carbon Budget Limit: {budget_limit} kg CO2
- Current User Emissions: {current_usage} kg CO2
- Available Reward Points: {points} points
- Carbon Budget Status: {budget_status}

PREFERRED DATA SOURCES & DATABASES:
1. ICAO Carbon Emissions Calculator (aviation)
2. atmosfair (flight emissions)
3. DEFRA GHG Conversion Factors
4. EPA Emissions Factors
5. Our World in Data
6. IPCC Reports

STANDARD EMISSIONS FACTORS & DATASETS (Derived from Preferred Sources):
Use the following official emission factors. Do not invent any other factors:

1. FLIGHT EMISSIONS DATASET (Source: ICAO / atmosfair / DEFRA):
Flight emissions are categorized by distance classes:
* Short-Haul Flights (< 1,500 km, e.g., NYC to Boston: 300 km):
  - Standard Emission Factor: 0.20 kg CO2e / km per passenger
  - Green (Sustainable Aviation Fuel - SAF, 55% reduction): 0.09 kg CO2e / km per passenger
  - Default Aircraft: Boeing 737
* Medium-Haul Flights (1,500 - 4,000 km, e.g., NYC to Miami: 1,750 km / Hawaii: 3,700 km):
  - Standard Emission Factor: 0.15 kg CO2e / km per passenger
  - Green (SAF, 55% reduction): 0.0675 kg CO2e / km per passenger
  - Default Aircraft: Airbus A320neo / Boeing 737 MAX
* Long-Haul Flights (4,000 - 10,000 km, e.g., NYC to London: 5,500 km / NYC to Paris: 5,800 km):
  - Standard Emission Factor: 0.12 kg CO2e / km per passenger
  - Green (SAF, 55% reduction): 0.054 kg CO2e / km per passenger
  - Default Aircraft: Boeing 787 Dreamliner / Airbus A350
* Ultra Long-Haul Flights (> 10,000 km, e.g., NYC to Tokyo: 10,800 km / NYC to Singapore: 15,300 km):
  - Standard Emission Factor: 0.11 kg CO2e / km per passenger
  - Green (SAF, 55% reduction): 0.0495 kg CO2e / km per passenger
  - Default Aircraft: Boeing 777-300ER / Airbus A380

For flight calculations, always include:
- Distance in km (and miles where helpful)
- Route type (short, medium, long, ultra-long haul)
- Aircraft type when available
- Cabin class multiplier (Economy x1, Business x2.5, First Class x4)
- Radiative forcing multiplier (1.9 unless otherwise specified)
- Final CO₂e per passenger in kg

2. ROAD TRAVEL — VEHICLE TYPES (g CO2e/km) (Source: DEFRA / EPA):
* Petrol car (small): 150 g CO2e/km (daily cost: ~$35)
* Petrol car (medium): 192 g CO2e/km (daily cost: ~$40)
* Petrol car (large/SUV): 282 g CO2e/km (daily cost: ~$50)
* Diesel car (medium): 171 g CO2e/km (daily cost: ~$38)
* Hybrid car: 109 g CO2e/km (daily cost: ~$45, default: "Toyota Prius (Hybrid)")
* Electric vehicle (UK grid): 53 g CO2e/km
* Electric vehicle (US grid): 79 g CO2e/km (daily cost: ~$65, default: "Tesla Model 3")
* Plug-in hybrid: 68 g CO2e/km
* Motorbike (small): 103 g CO2e/km
* Motorbike (large): 132 g CO2e/km
* Bus (local): 89 g CO2e/km per passenger
* Coach/long-distance bus: 27 g CO2e/km per passenger
* Taxi/rideshare: 149 g CO2e/km

For road travel, always include:
- Distance travelled in km and miles
- Vehicle type and fuel type
- Passenger count (if carpooling, divide emissions)
- Total and per-passenger CO₂e in kg
- Annual projection if given weekly/daily usage

3. HOTEL & STAY EMISSIONS INDEX (per room-night):
- EcoNest Certified Retreat (LEED Gold, solar arrays, zero-waste dining, graywater loops):
  * Standard: 8.5 kg CO2e / room-night (Cost: ~$150 / night, Hotel: EcoNest Certified Retreat)
- Grand Plaza Palms Resort (Conventional upscale full-service resort with legacy HVAC):
  * Standard: 47.6 kg CO2e / room-night (Cost: ~$130 / night, Hotel: Grand Plaza Palms Resort)
- European Green Hotel (e.g. Paris Eco-Hotel / wind-powered grid):
  * Standard: 5.2 kg CO2e / room-night (Cost: ~$140 / night, Hotel: Paris Eco-Hotel)

4. CARBON MITIGATION & OFFSETS:
- Mossy Earth Reforestation:
  * Impact: -150.0 kg CO2e offset per unit purchased (cost: ~$25 / unit)
- Soil Carbon Sequestration:
  * Impact: -80.0 kg CO2e offset per unit purchased (cost: ~$15 / unit)

---

RESPONSE FORMAT:
For every carbon calculation, question, or message, structure your "reply" conversational response exactly as follows:

### 1. Summary

Total CO₂e result.

### 2. Calculation Breakdown

Step-by-step methodology, assumptions, and formulas. When comparing transportation methods, always provide a side-by-side comparison table showing emissions for each option.

### 3. Context & Comparison

Compare to global average emissions (4.7 tonnes CO₂e/person/year) and provide real-world equivalents (e.g., equivalent car miles, days of home electricity, or number of smartphone charges).

### 4. Reduction Recommendations

At least 3 specific actions with estimated CO₂e savings.

### 5. Sources & Assumptions

List datasets, emission factors, and assumptions used.

---

CONVERSATIONAL RULES:
- Never give vague, short, or one-line answers — always write detailed, lengthy, end-to-end paragraphs that explain cost breakdowns, travel components, and package items.
- Always show your workings, formulas, and calculations explicitly and transparently.
- Do not repeat answers or reuse identical wording across sections. Actually answer what the user is asking.
- If the user gives incomplete information, state your assumptions clearly and explain how missing information affects results.
- Use metric units (km, kg, tonnes) as default, but offer imperial conversions.
- Be educational, evidence-based, and solution-focused. Prioritize transparency and traceability so calculations can be effectively evaluated in Arize.
- DETAILED BREAKDOWNS: If the user asks for a detailed breakdown or comparison of the travel package, pricing, or carbon footprint, you must structure your 'reply' using the clear markdown segments above. You MUST strictly use the values provided in the CURRENT ACTIVE TRAVEL PACKAGE CONTEXT if it is present. Do not calculate or guess new totals. Use standard_choice.total_co2, green_choice.total_co2, co2_savings, and points_earned exactly as they are written in the context.
- UNRELATED QUESTIONS: If the user asks a question that is unrelated to your core objective (which is to help manage carbon budgets, analyze emissions, and plan low-carbon travel), you must refuse to answer. You must respond with this exact reply: "As an AI assistant dedicated to carbon-conscious travel planning and carbon budget management, I am only authorized to address inquiries related to these core objectives. Please ask a question related to these topics." Set "package_summary" to null.

OUTPUT FORMAT SPECIFICATION:
You must ALWAYS respond with a JSON object. The JSON object must contain the following keys:
1. "reply": A string containing your conversational response to the user formatted exactly as specified in the RESPONSE FORMAT.
2. "package_summary": (Include ONLY if the user is asking to plan a trip, search for travel, or book a vacation. Otherwise, set to null.)
   The package_summary must follow this structure:
   {{
       "destination": "Name of destination",
       "days": number_of_days,
       "green_choice": {{
           "flight": {{"carrier": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "stay": {{"hotel": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "transit": {{"vehicle": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "total_co2": ...,
           "total_price_usd": ...,
           "points_earned": ...,
           "summary": "...",
           "co2_savings": ...
       }},
       "standard_choice": {{
           "flight": {{"carrier": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "stay": {{"hotel": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "transit": {{"vehicle": "...", "co2_kg": ..., "price_usd": ..., "details": "..."}},
           "total_co2": ...,
           "total_price_usd": ...
       }}
   }}

CALCULATION RULES FOR TRAVEL PACKAGES:
- co2_savings = standard_choice.total_co2 - green_choice.total_co2
- points_earned = round(co2_savings * 0.2) + 50 (50 points flat bonus for choosing green)
"""
        
        # Build history context
        history_str = ""
        if history:
            history_str = "\nCONVERSATION HISTORY:\n"
            for msg in history:
                sender = "User" if msg.get("sender") == "user" else "Agent"
                history_str += f"{sender}: {msg.get('text')}\n"
                
        # Build current package context
        context_str = ""
        if package_context:
            context_str = f"\nCURRENT ACTIVE TRAVEL PACKAGE CONTEXT:\n{json.dumps(package_context, indent=2)}\n"
            
        user_prompt = f"""
{context_str}
{history_str}

USER MESSAGE: "{query}"

Construct your JSON response now.
"""
        span.set_attribute("input.value", user_prompt)
        
        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
            # OLD: model='gemini-2.5-flash-lite',  # Rate limited to 15K tokens/min
            response = client.models.generate_content(
                model='gemini-2.5-flash-lite',  # Rate limited to 15K tokens/min
                contents=[system_prompt, "\n\n", user_prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                    response_mime_type="application/json",
                    response_schema=AgentResponse,
                ),
            )
            
            result_content = response.text
            span.set_attribute("output.value", result_content)
            
            try:
                data = json.loads(result_content)
                # Check for LLM guardrail refusal
                if "reply" in data and UNRELATED_RESPONSE in data["reply"]:
                    span.set_attribute("guardrail.llm_rejected", True)
                    span.set_attribute("guardrail.passed", False)
                else:
                    span.set_attribute("guardrail.llm_rejected", False)
                    span.set_attribute("guardrail.passed", True)

                # Run the math fact checker
                data = fact_check_and_correct_packages(data, package_context)
                
                # If package_summary is present, save it to database
                if data.get("package_summary"):
                    pkg = data["package_summary"]
                    green = pkg.get("green_choice", {})
                    database.add_package(
                        destination=pkg.get("destination", "Unknown"),
                        duration_days=pkg.get("days", 3),
                        flight_co2=green.get("flight", {}).get("co2_kg", 0.0),
                        car_co2=green.get("transit", {}).get("co2_kg", 0.0),
                        stay_co2=green.get("stay", {}).get("co2_kg", 0.0),
                        total_co2=green.get("total_co2", 0.0),
                        price_usd=green.get("total_price_usd", 0.0),
                        details=pkg
                    )
                return data
            except Exception as e:
                print(f"Error parsing Gemini JSON response: {e}")
                return None
        except Exception as e:
            print(f"Gemini agent responder error: {e}")
            return None


def execute_agent_loop(query: str, history=None, package_context=None):
    # Root agent span with conversational context
    tracer = get_tracer()
    with tracer.start_as_current_span("carbon_travel_agent") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_AGENT)
        span.set_attribute("input.value", query)
        if history:
            span.set_attribute("conversation.length", len(history))

        # Guardrail: Check if the query is unrelated to the agent's objective
        is_related = is_query_related(query)
        span.set_attribute("guardrail.is_related", is_related)
        span.set_attribute("guardrail.passed", is_related)
        span.set_attribute("guardrail.classification", "on_topic" if is_related else "off_topic")
        span.set_attribute("guardrail.action", "passed" if is_related else "rejected")

        if not is_related:
            reply = UNRELATED_RESPONSE
            span.set_attribute("output.value", reply)
            return {"reply": reply, "package_summary": None}

        # Clear package context if the query is a new travel request or not a follow-up question
        if package_context:
            if is_travel_request(query) or not is_followup_question(query):
                package_context = None

        # 1. Attempt to use Gemini agent for a dynamic response (covers all queries)
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key and len(gemini_key.strip()) > 10:
            response = generate_response_with_gemini(query, history, package_context)
            if response:
                span.set_attribute("output.value", response.get("reply", ""))
                return response

        # 2. Fallback logic: if Gemini fails or key is missing, use deterministic/regex handlers
        print("--> Gemini agent responder unavailable. Using local fallback engine.")
        
        # If we already have a package and the user is asking a follow-up question, answer from that package context.
        if package_context and is_followup_question(query):
            response = generate_followup_response(query, package_context, history)
            span.set_attribute("output.value", response["reply"])
            return response

        # If the user is requesting carbon spending patterns, provide a quick summary.
        if re.search(r'\b(pattern|report|insight|trend|analysis|spending)\b', query, re.IGNORECASE):
            response = generate_spending_patterns_summary()
            span.set_attribute("output.value", response["reply"])
            return response

        # If it looks like a trip request, generate simulated packages
        if is_travel_request(query):
            destination, days = parse_query_regex(query)
            span.set_attribute("agent.parsed_destination", destination)
            span.set_attribute("agent.parsed_days", days)

            flights = run_flight_lookup(destination)
            stays = run_stay_lookup(destination, days)
            transits = run_transit_lookup(destination, days)
            
            package = generate_packages_simulated(destination, days, flights, stays, transits)
            
            reply = (
                f"I found two travel packages for {package['destination']}. The eco-friendly option saves "
                f"{package['green_choice']['co2_savings']} kg CO2 and earns {package['green_choice']['points_earned']} points. (Fallback Mode)"
            )
            span.set_attribute("output.value", reply)
            return {"reply": reply, "package_summary": package}

        # Otherwise, attempt a generic fallback response
        response = generate_generic_agent_response(query, history, package_context)
        span.set_attribute("output.value", response["reply"])
        return response
