import os
import re
import json
import datetime
from opentelemetry import trace
from backend.arize_integration import get_tracer
from backend import database

# Define span kinds for OpenInference
SPAN_KIND_KEY = "openinference.span.kind"
SPAN_KIND_AGENT = "AGENT"
SPAN_KIND_LLM = "LLM"
SPAN_KIND_TOOL = "TOOL"
SPAN_KIND_CHAIN = "CHAIN"

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

def run_flight_lookup(destination):
    tracer = get_tracer()
    with tracer.start_as_current_span("flight_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "flight_lookup_tool")
        span.set_attribute("tool.description", "Lookup eco-efficient and standard flight options for a destination")
        span.set_attribute("input.value", json.dumps({"destination": destination}))
        
        # Base carbon calculations (rough estimates based on distance)
        # We can seed different values based on destination
        hash_val = sum(ord(c) for c in destination) % 5 + 1
        base_co2 = hash_val * 150.0  # kg CO2
        
        flights = {
            "eco": {
                "carrier": "GreenJet Airways (Sustainable Aviation Fuel - SAF)",
                "co2_kg": round(base_co2 * 0.45, 1),
                "price_usd": round(300 + (hash_val * 80), 2),
                "description": "Utilizes 50% Sustainable Aviation Fuel (SAF) blend and optimized flight pathing, reducing carbon footprint by 55%."
            },
            "standard": {
                "carrier": "Legacy Trans-Continental Airlines",
                "co2_kg": round(base_co2, 1),
                "price_usd": round(250 + (hash_val * 70), 2),
                "description": "Standard direct economy flight using standard kerosene jet fuel."
            }
        }
        
        span.set_attribute("output.value", json.dumps(flights))
        return flights

def run_stay_lookup(destination, days):
    tracer = get_tracer()
    with tracer.start_as_current_span("stay_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "stay_lookup_tool")
        span.set_attribute("tool.description", "Lookup eco-friendly hotels and standard stays")
        span.set_attribute("input.value", json.dumps({"destination": destination, "days": days}))
        
        eco_rate = 12.0  # kg CO2 / night
        std_rate = 45.0  # kg CO2 / night
        
        stays = {
            "eco": {
                "hotel": "EcoNest Certified Retreat",
                "co2_kg": round(eco_rate * days, 1),
                "price_usd": round(150 * days, 2),
                "description": "LEED Gold certified eco-resort. Runs on 100% solar power, practices strict zero-waste dining, and uses greywater systems."
            },
            "standard": {
                "hotel": "Grand Plaza Palms Resort",
                "co2_kg": round(std_rate * days, 1),
                "price_usd": round(130 * days, 2),
                "description": "Full-service conventional luxury resort."
            }
        }
        
        span.set_attribute("output.value", json.dumps(stays))
        return stays

def run_transit_lookup(destination, days):
    tracer = get_tracer()
    with tracer.start_as_current_span("transit_lookup_tool") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_TOOL)
        span.set_attribute("tool.name", "transit_lookup_tool")
        span.set_attribute("tool.description", "Lookup green transit and standard vehicle rentals")
        span.set_attribute("input.value", json.dumps({"destination": destination, "days": days}))
        
        transits = {
            "eco": {
                "vehicle": "Tesla Model 3 (EV Rental)",
                "co2_kg": 0.0,
                "price_usd": round(65 * days, 2),
                "description": "All-electric vehicle rental. Powered entirely by the island's geothermal and solar charging network."
            },
            "standard": {
                "vehicle": "Full-Size Gas SUV Rental",
                "co2_kg": round(42.5 * days, 1),
                "price_usd": round(50 * days, 2),
                "description": "Standard gasoline internal combustion engine SUV."
            }
        }
        
        span.set_attribute("output.value", json.dumps(transits))
        return transits

def generate_packages_with_gemini(query, destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("gemini_package_generator") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_LLM)
        span.set_attribute("llm.model_name", "gemini-1.5-pro")
        
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
            import google.generativeai as genai
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel("gemini-1.5-pro")
            
            response = model.generate_content(
                [system_prompt, "\n\n", user_prompt],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=2000,
                )
            )
            
            result_content = response.text
            span.set_attribute("output.value", result_content)
            
            try:
                return json.loads(result_content)
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                return None
        except Exception as e:
            print(f"Gemini LLM error: {e}")
            return None

def generate_packages_with_claude(query, destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("claude_package_generator") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_LLM)
        span.set_attribute("llm.model_name", "claude-3-sonnet")
        
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
            from anthropic import Anthropic
            client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            response = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": user_prompt}
                ],
                system=system_prompt
            )
            
            result_content = response.content[0].text
            span.set_attribute("output.value", result_content)
            
            try:
                return json.loads(result_content)
            except Exception as e:
                print(f"Error parsing Claude response: {e}")
                return None
        except Exception as e:
            print(f"Claude LLM error: {e}")
            return None

def generate_packages_real_llm(query, destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("openai_package_generator") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_LLM)
        span.set_attribute("llm.model_name", "gpt-4o")
        
        # System prompt and instruction
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
        Points earned should be: Math.round(savings_kg * 0.2) + 50 (bonus for choosing green).
        
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
        
        # Call OpenAI if key is present
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2
        )
        
        result_content = response.choices[0].message.content
        span.set_attribute("output.value", result_content)
        
        # Try to parse the result as JSON
        try:
            return json.loads(result_content)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return None

def generate_packages_simulated(destination, days, flights, stays, transits):
    tracer = get_tracer()
    
    with tracer.start_as_current_span("agent_reasoning_loop") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_CHAIN)
        span.set_attribute("input.value", f"Reasoning about travel package for {destination} for {days} days.")
        
        # Calculate totals
        eco_flight = flights["eco"]
        std_flight = flights["standard"]
        eco_stay = stays["eco"]
        std_stay = stays["standard"]
        eco_transit = transits["eco"]
        std_transit = transits["standard"]
        
        eco_total_co2 = eco_flight["co2_kg"] + eco_stay["co2_kg"] + eco_transit["co2_kg"]
        std_total_co2 = std_flight["co2_kg"] + std_stay["co2_kg"] + std_transit["co2_kg"]
        
        eco_total_price = eco_flight["price_usd"] + eco_stay["price_usd"] + eco_transit["price_usd"]
        std_total_price = std_flight["price_usd"] + std_stay["price_usd"] + std_transit["price_usd"]
        
        co2_savings = round(std_total_co2 - eco_total_co2, 1)
        points_earned = int(co2_savings * 0.2) + 50  # 20% savings + 50 points flat green booking reward
        
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
    return bool(re.search(r'\b(afford|cost|price|budget|compare|saving|savings|carbon|emissions|points|report|pattern|trend|insight|recommend)\b', query, re.IGNORECASE))


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
        reply = (
            f"The green package is ${eco['total_price_usd']} with {eco['total_co2']} kg CO2, while the standard package is ${std['total_price_usd']} "
            f"with {std['total_co2']} kg CO2. The eco option is slightly more expensive, but it earns {eco['points_earned']} points and saves {eco['co2_savings']} kg CO2."
        )
    elif re.search(r'\b(compare|better|trade[- ]off|difference|vs|versus)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        std = package_context['standard_choice']
        reply = (
            f"Compared to the standard package, the eco package saves {eco['co2_savings']} kg CO2 and earns {eco['points_earned']} points. "
            f"It offers cleaner transport and renewable-energy lodging, while the standard choice is lower cost but higher emissions."
        )
    elif re.search(r'\b(point|reward|earn)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        reply = f"By choosing the green package, you earn {eco['points_earned']} reward points. These points are earned by reducing emissions and choosing sustainable travel options."
    elif re.search(r'\b(carbon|emission|co2|green|sustainable)\b', query, re.IGNORECASE):
        eco = package_context['green_choice']
        reply = (
            f"Your eco package uses a SAF flight, LEED-certified lodging, and an EV rental to keep emissions at {eco['total_co2']} kg CO2. "
            f"This is {eco['co2_savings']} kg CO2 lower than the standard package."
        )
    else:
        reply = default_summary or "I can help you compare the earlier packages, explain the carbon savings, or recommend the best choice for your budget."

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

        return {"reply": summary_text, "pattern_report": patterns}


def generate_generic_agent_response(query: str, history=None, package_context=None) -> dict:
    if package_context and is_followup_question(query):
        return generate_followup_response(query, package_context, history)

    reply = (
        "I can help you explore low-carbon travel options, estimate budget impacts, "
        "and provide spending pattern insights. Ask me about affordability, carbon savings, or specific trip details."
    )
    if package_context:
        reply += " I can also compare the current package against your goals."

    return {"reply": reply}


def execute_agent_loop(query: str, history=None, package_context=None):
    # Root agent span with conversational context
    tracer = get_tracer()
    with tracer.start_as_current_span("carbon_travel_agent") as span:
        span.set_attribute(SPAN_KIND_KEY, SPAN_KIND_AGENT)
        span.set_attribute("input.value", query)
        if history:
            span.set_attribute("conversation.length", len(history))

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

        # Otherwise, attempt to create a travel package if the query looks like a trip request.
        if not is_travel_request(query):
            response = generate_generic_agent_response(query, history, package_context)
            span.set_attribute("output.value", response["reply"])
            return response

        destination, days = parse_query_regex(query)
        span.set_attribute("agent.parsed_destination", destination)
        span.set_attribute("agent.parsed_days", days)

        flights = run_flight_lookup(destination)
        stays = run_stay_lookup(destination, days)
        transits = run_transit_lookup(destination, days)

        gemini_key = os.getenv("GEMINI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        # Try generating a package using any LLM available.
        package = None
        if gemini_key and len(gemini_key.strip()) > 10:
            package = generate_packages_with_gemini(query, destination, days, flights, stays, transits)
        if not package and anthropic_key and len(anthropic_key.strip()) > 10:
            package = generate_packages_with_claude(query, destination, days, flights, stays, transits)
        if not package and openai_key and len(openai_key.strip()) > 10:
            package = generate_packages_real_llm(query, destination, days, flights, stays, transits)
        if not package:
            package = generate_packages_simulated(destination, days, flights, stays, transits)

        reply = (
            f"I found two travel packages for {package['destination']}. The eco-friendly option saves "
            f"{package['green_choice']['co2_savings']} kg CO2 and earns {package['green_choice']['points_earned']} points."
        )
        span.set_attribute("output.value", reply)
        return {"reply": reply, "package_summary": package}
