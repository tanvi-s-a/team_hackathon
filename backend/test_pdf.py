import os
from backend import main
from backend import database

database.init_db()

# Test 1: Empty / Null context
null_data = {
    "destination": None,
    "days": None,
    "green_flight": None,
    "green_stay": None,
    "green_transit": None,
    "std_flight": None,
    "std_stay": None,
    "std_transit": None,
    "green_total_co2": None,
    "green_total_price": None,
    "std_total_co2": None,
    "std_total_price": None,
    "co2_savings": None,
    "points_earned": None,
    "bal_flight": None,
    "bal_stay": None,
    "bal_transit": None,
    "bal_total_co2": None,
    "bal_total_price": None,
    "bal_co2_savings": None,
    "bal_points_earned": None,
}

print("Testing PDF generation with null/empty payload...")
try:
    pdf_bytes = main.generate_pdf_report(null_data)
    print(f"Success! Generated {len(pdf_bytes)} bytes.")
except Exception as e:
    import traceback
    traceback.print_exc()

# Test 2: Full context
full_data = {
    "destination": "Hawaii",
    "days": 3,
    "green_flight": {"carrier": "Hawaiian Airlines", "co2_kg": 350.0, "price_usd": 450.0, "details": "Flight HA12"},
    "green_stay": {"hotel": "EcoNest Certified Retreat", "co2_kg": 25.5, "price_usd": 450.0, "details": "Solar power"},
    "green_transit": {"vehicle": "Tesla Model 3", "co2_kg": 23.7, "price_usd": 195.0, "details": "Electric"},
    "std_flight": {"carrier": "Delta Air Lines", "co2_kg": 800.0, "price_usd": 400.0, "details": "Flight DL34"},
    "std_stay": {"hotel": "Grand Plaza Palms Resort", "co2_kg": 142.8, "price_usd": 390.0, "details": "Conventional"},
    "std_transit": {"vehicle": "Petrol SUV", "co2_kg": 84.6, "price_usd": 150.0, "details": "Petrol"},
    "green_total_co2": 399.2,
    "green_total_price": 1095.0,
    "std_total_co2": 1027.4,
    "std_total_price": 940.0,
    "co2_savings": 628.2,
    "points_earned": 176,
    "bal_flight": {"carrier": "Hawaiian Airlines", "co2_kg": 350.0, "price_usd": 450.0, "details": "Flight HA12"},
    "bal_stay": {"hotel": "Grand Plaza Palms Resort", "co2_kg": 142.8, "price_usd": 390.0, "details": "Conventional"},
    "bal_transit": {"vehicle": "Tesla Model 3", "co2_kg": 23.7, "price_usd": 195.0, "details": "Electric"},
    "bal_total_co2": 516.5,
    "bal_total_price": 1035.0,
    "bal_co2_savings": 510.9,
    "bal_points_earned": 152,
}

print("\nTesting PDF generation with full payload...")
try:
    pdf_bytes = main.generate_pdf_report(full_data)
    print(f"Success! Generated {len(pdf_bytes)} bytes.")
except Exception as e:
    import traceback
    traceback.print_exc()
