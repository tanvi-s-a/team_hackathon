import json

# Load the debug response
with open("debug_gemini_raw.json", "r", encoding="utf-8") as f:
    data = json.load(f)

reply = data["reply"]
words = reply.split()
word_count = len(words)

print(f"Original word count: {word_count}")

if word_count > 160:
    truncated = " ".join(words[:150]) + "..."
    print(f"\nTruncated to 150 words:\n")
    print(truncated)
    print(f"\nNew word count: {len(truncated.split())}")
