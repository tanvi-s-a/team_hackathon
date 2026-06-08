import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Create User/Account table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS account_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        budget_limit REAL NOT NULL,
        current_usage REAL NOT NULL,
        points INTEGER NOT NULL
    )
    """)
    
    # 2. Create Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        points_earned INTEGER NOT NULL,
        status TEXT NOT NULL
    )
    """)
    
    # 3. Create Packages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS travel_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        destination TEXT NOT NULL,
        duration_days INTEGER NOT NULL,
        flight_co2 REAL NOT NULL,
        car_co2 REAL NOT NULL,
        stay_co2 REAL NOT NULL,
        total_co2 REAL NOT NULL,
        price_usd REAL NOT NULL,
        details_json TEXT NOT NULL
    )
    """)
    
    # Check if database is empty to insert seed data
    cursor.execute("SELECT COUNT(*) FROM account_summary")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO account_summary (budget_limit, current_usage, points)
        VALUES (?, ?, ?)
        """, (5000.0, 1840.0, 650))
        
        # Seed Transactions
        seed_tx = [
            ("2026-05-15", "NYC to London Flight (Economy)", "flight", 980.0, 10, "completed"),
            ("2026-05-20", "Uber Green Electric Ride", "car", 12.4, 30, "completed"),
            ("2026-05-25", "Monthly Home Electricity (100% Wind Power)", "energy", 45.0, 100, "completed"),
            ("2026-06-01", "Hybrid Car Rental (3 Days)", "car", 28.5, 40, "completed"),
            ("2026-06-05", "Carbon Offset - Mossy Earth Reforestation", "offset", -150.0, 150, "completed"),
            ("2026-06-07", "Hawaii 3-Day Eco-Package (Pending confirmation)", "flight", 420.0, 80, "pending")
        ]
        cursor.executemany("""
        INSERT INTO transactions (date, description, type, amount, points_earned, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """, seed_tx)
        
        # Seed travel packages for reference
        sample_details = {
            "flight": {"carrier": "Hawaiian Airlines (Biofuel flight)", "co2_kg": 420.0, "details": "Direct flight with carbon-neutral offset options"},
            "car": {"model": "Tesla Model Y", "co2_kg": 0.0, "details": "Electric vehicle rental, charging powered by local solar grid"},
            "stay": {"hotel": "Aloha Green Resort", "co2_kg": 35.0, "details": "LEED Gold Certified, solar-powered eco-resort"}
        }
        cursor.execute("""
        INSERT INTO travel_packages (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("Hawaii", 3, 420.0, 0.0, 35.0, 455.0, 1250.0, json.dumps(sample_details)))
        
    conn.commit()
    conn.close()

def get_summary():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"budget_limit": 5000.0, "current_usage": 0.0, "points": 0}

def update_summary(usage_change, points_change):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Get current summary
    cursor.execute("SELECT * FROM account_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        new_usage = max(0.0, row["current_usage"] + usage_change)
        new_points = max(0, row["points"] + points_change)
        cursor.execute("""
        UPDATE account_summary
        SET current_usage = ?, points = ?
        WHERE id = ?
        """, (new_usage, new_points, row["id"]))
    conn.commit()
    conn.close()

def get_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_transaction(date, description, tx_type, amount, points_earned, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO transactions (date, description, type, amount, points_earned, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (date, description, tx_type, amount, points_earned, status))
    tx_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # If the transaction is completed, update the account summary automatically
    if status == "completed":
        update_summary(amount, points_earned)
        
    return tx_id

def update_transaction_status(tx_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    # Check current status
    cursor.execute("SELECT * FROM transactions WHERE id = ?", (tx_id,))
    row = cursor.fetchone()
    if row and row["status"] != new_status:
        cursor.execute("UPDATE transactions SET status = ? WHERE id = ?", (new_status, tx_id))
        conn.commit()
        
        # If transitioning to completed, apply changes to summary
        if new_status == "completed":
            update_summary(row["amount"], row["points_earned"])
            
    conn.close()

def get_packages(destination, days):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM travel_packages
    WHERE LOWER(destination) = LOWER(?) AND duration_days = ?
    """, (destination, days))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_package(destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO travel_packages (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, json.dumps(details)))
    pkg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return pkg_id
