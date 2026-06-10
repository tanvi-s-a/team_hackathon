import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

from backend import agent
from backend import database

database.init_db()

live_api_context = """
LIVE REAL-TIME SEARCH RESULTS:
- Destination: Hawaii
- Distance & Coordinates: Location resolved at {'lat': 21.3069, 'lng': -157.8583}.
"""

print("Calling agent function and printing raw API response...")
try:
    # Let's perform the call ourselves using client, replicating agent.py's call, and print candidate details:
    # First get summary
    summary = database.get_summary()
    current_usage = summary.get("current_usage", 0.0)
    budget_limit = summary.get("budget_limit", 5000.0)
    points = summary.get("points", 0)
    budget_status = f"{round((current_usage / budget_limit) * 100, 1)}% used ({current_usage} kg of {budget_limit} kg)"
    
    # We will load system prompt from agent
    # Since agent.py has generate_response_with_gemini, let's see how system_prompt is defined.
    # To debug easily, we can modify agent.py to print the response candidate or we can print it here.
    # Let's run a test query on agent.py directly but catch the print. Wait, let's write a wrapper.
    # Actually, let's run the API call here with the exact prompts from agent.py:
    
    # Let's import the generate_response_with_gemini logic and print the exception and raw candidates.
    # Let's look at why it could be truncating.
    # Could it be because of safety settings? Or max_output_tokens?
    # Let's test with a different model or config.
    
    # Let's make the call here:
    import inspect
    # We can inspect generate_response_with_gemini code
    print("Executing generate_response_with_gemini with try-except prints...")
    res = agent.generate_response_with_gemini(
        query="I want to plan a trip to Hawaii for 3 days",
        history=[],
        package_context=None,
        live_api_context=live_api_context
    )
    print("Result:", res)
    
except Exception as e:
    import traceback
    traceback.print_exc()
