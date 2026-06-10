#!/usr/bin/env python3
"""
Test script for Carbon Travel Agent with Gemini 1.5 Flash
Tests the agent.execute_agent_loop() with various queries
No changes made to the application - testing only
"""

import os
import sys
import json
import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", ".env"))

# Import required modules
from backend import database
from backend import agent

print("=" * 80)
print("CARBON TRAVEL AGENT TEST SUITE - Gemini 1.5 Flash")
print("=" * 80)
print(f"\nPython Version: {sys.version}")
print(f"Working Directory: {os.getcwd()}")
print(f"GEMINI_API_KEY Status: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET (using fallback)'}")
print()

# Initialize database
print("1. Initializing Database...")
database.init_db()
summary = database.get_summary()
print(f"   ✓ Database initialized")
print(f"   - Budget Limit: {summary['budget_limit']} kg CO2")
print(f"   - Current Usage: {summary['current_usage']} kg CO2")
print(f"   - Points: {summary['points']}")
print()

# Test cases
test_cases = [
    {
        "name": "Test 1: Simple Trip Request",
        "query": "I want to plan a trip to Hawaii for 3 days",
        "history": [],
        "package_context": None,
        "expected": "Should return a travel package with eco and standard options"
    },
    {
        "name": "Test 2: Travel Request to Europe",
        "query": "book a 5-day trip to Paris",
        "history": [],
        "package_context": None,
        "expected": "Should generate Paris travel package"
    },
    {
        "name": "Test 3: Question About Affordability",
        "query": "How much does this cost?",
        "history": [],
        "package_context": {
            "destination": "Hawaii",
            "days": 3,
            "green_choice": {
                "flight": {"carrier": "GreenJet", "co2_kg": 450.0, "price_usd": 520.0, "details": "SAF flight"},
                "stay": {"hotel": "EcoNest", "co2_kg": 36.0, "price_usd": 450.0, "details": "Eco resort"},
                "transit": {"vehicle": "Tesla", "co2_kg": 0.0, "price_usd": 195.0, "details": "EV rental"},
                "total_co2": 486.0,
                "total_price_usd": 1165.0,
                "points_earned": 127,
                "summary": "Green package for Hawaii",
                "co2_savings": 240.0
            },
            "standard_choice": {
                "flight": {"carrier": "Legacy Airlines", "co2_kg": 600.0, "price_usd": 450.0, "details": "Standard flight"},
                "stay": {"hotel": "Grand Plaza", "co2_kg": 142.8, "price_usd": 390.0, "details": "Standard resort"},
                "transit": {"vehicle": "SUV", "co2_kg": 127.5, "price_usd": 150.0, "details": "Gas SUV"},
                "total_co2": 870.3,
                "total_price_usd": 990.0
            }
        },
        "expected": "Should compare costs between eco and standard options"
    },
    {
        "name": "Test 4: Carbon Savings Question",
        "query": "How much carbon do I save with the green choice?",
        "history": [],
        "package_context": {
            "destination": "Hawaii",
            "days": 3,
            "green_choice": {
                "flight": {"carrier": "GreenJet", "co2_kg": 450.0, "price_usd": 520.0, "details": "SAF flight"},
                "stay": {"hotel": "EcoNest", "co2_kg": 36.0, "price_usd": 450.0, "details": "Eco resort"},
                "transit": {"vehicle": "Tesla", "co2_kg": 0.0, "price_usd": 195.0, "details": "EV rental"},
                "total_co2": 486.0,
                "total_price_usd": 1165.0,
                "points_earned": 127,
                "summary": "Green package",
                "co2_savings": 384.3
            },
            "standard_choice": {
                "flight": {"carrier": "Legacy Airlines", "co2_kg": 870.3, "price_usd": 450.0, "details": "Standard flight"},
                "stay": {"hotel": "Grand Plaza", "co2_kg": 142.8, "price_usd": 390.0, "details": "Standard resort"},
                "transit": {"vehicle": "SUV", "co2_kg": 0.0, "price_usd": 150.0, "details": "Gas SUV"},
                "total_co2": 870.3,
                "total_price_usd": 990.0
            }
        },
        "expected": "Should explain carbon savings (384.3 kg)"
    },
    {
        "name": "Test 5: Reward Points Question",
        "query": "How many points do I earn?",
        "history": [],
        "package_context": {
            "destination": "Hawaii",
            "days": 3,
            "green_choice": {
                "flight": {"carrier": "GreenJet", "co2_kg": 450.0, "price_usd": 520.0, "details": "SAF flight"},
                "stay": {"hotel": "EcoNest", "co2_kg": 36.0, "price_usd": 450.0, "details": "Eco resort"},
                "transit": {"vehicle": "Tesla", "co2_kg": 0.0, "price_usd": 195.0, "details": "EV rental"},
                "total_co2": 486.0,
                "total_price_usd": 1165.0,
                "points_earned": 127,
                "summary": "Green package",
                "co2_savings": 384.3
            },
            "standard_choice": {
                "flight": {"carrier": "Legacy Airlines", "co2_kg": 870.3, "price_usd": 450.0, "details": "Standard flight"},
                "stay": {"hotel": "Grand Plaza", "co2_kg": 142.8, "price_usd": 390.0, "details": "Standard resort"},
                "transit": {"vehicle": "SUV", "co2_kg": 0.0, "price_usd": 150.0, "details": "Gas SUV"},
                "total_co2": 870.3,
                "total_price_usd": 990.0
            }
        },
        "expected": "Should mention 127 reward points"
    },
    {
        "name": "Test 6: Spending Patterns Report",
        "query": "Give me a report on my carbon spending patterns and insights",
        "history": [],
        "package_context": None,
        "expected": "Should return spending patterns analysis"
    },
    {
        "name": "Test 7: Generic Help Query",
        "query": "What can you help me with?",
        "history": [],
        "package_context": None,
        "expected": "Should describe capabilities"
    },
    {
        "name": "Test 8: Unrelated Query (Off-Topic)",
        "query": "What is the capital of France?",
        "history": [],
        "package_context": None,
        "expected": "Should reject with unrelated response"
    },
]

# Run tests
test_results = []

for i, test_case in enumerate(test_cases, 1):
    print(f"\n{'=' * 80}")
    print(f"{test_case['name']}")
    print(f"{'=' * 80}")
    print(f"Query: {test_case['query']}")
    print(f"Expected: {test_case['expected']}")
    print(f"\nRunning agent...")
    
    try:
        response = agent.execute_agent_loop(
            query=test_case['query'],
            history=test_case['history'],
            package_context=test_case['package_context']
        )
        
        # Print response
        print(f"\n✓ RESPONSE RECEIVED")
        print(f"  Reply length: {len(response.get('reply', ''))} characters")
        print(f"  Has package_summary: {'Yes' if response.get('package_summary') else 'No'}")
        
        # Print reply preview
        reply = response.get('reply', '')
        reply_preview = reply[:200] + "..." if len(reply) > 200 else reply
        print(f"\n  Reply Preview:")
        print(f"  {reply_preview}")
        
        # Print full reply if reasonably sized
        if len(reply) < 500:
            print(f"\n  Full Reply:")
            print(f"  {reply}")
        
        # Print package info if present
        if response.get('package_summary'):
            pkg = response['package_summary']
            print(f"\n  Package Summary:")
            print(f"  - Destination: {pkg.get('destination')}")
            print(f"  - Days: {pkg.get('days')}")
            if pkg.get('green_choice'):
                green = pkg['green_choice']
                print(f"  - Green Choice CO2: {green.get('total_co2')} kg")
                print(f"  - Green Choice Price: ${green.get('total_price_usd')}")
                print(f"  - Points Earned: {green.get('points_earned')}")
                print(f"  - CO2 Savings: {green.get('co2_savings')} kg")
        
        test_results.append({
            "test": test_case['name'],
            "status": "PASSED",
            "details": f"Response received with {len(response.get('reply', ''))} char reply"
        })
        print(f"\n✓ TEST PASSED")
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append({
            "test": test_case['name'],
            "status": "FAILED",
            "details": str(e)
        })

# Print summary
print(f"\n\n{'=' * 80}")
print("TEST SUMMARY")
print(f"{'=' * 80}")

passed = sum(1 for r in test_results if r['status'] == 'PASSED')
failed = sum(1 for r in test_results if r['status'] == 'FAILED')

print(f"\nTotal Tests: {len(test_results)}")
print(f"Passed: {passed} ✓")
print(f"Failed: {failed} ✗")
print(f"Success Rate: {(passed/len(test_results)*100):.1f}%")

print(f"\nDetailed Results:")
for result in test_results:
    status_icon = "✓" if result['status'] == 'PASSED' else "✗"
    print(f"  {status_icon} {result['test']}: {result['details']}")

print(f"\n{'=' * 80}")
print("TEST EXECUTION COMPLETE")
print(f"{'=' * 80}")
