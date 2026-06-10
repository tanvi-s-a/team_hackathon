import os
from dotenv import load_dotenv
from google import genai

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

models_to_test = ['gemini-1.5-flash', 'gemini-2.5-flash', 'gemini-2.5-flash-lite']

for model in models_to_test:
    print(f"Testing model: {model}...")
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say hello in one word."
        )
        print(f"  {model} response: {response.text.strip()}")
    except Exception as e:
        print(f"  {model} failed: {e}")
