import os
import json
import sqlite3

# Global database configuration and flags
IS_POSTGRES = False
db_conn_error = None

# Retrieve database connection parameters from environment
# Supports standard PostgreSQL env vars and a fallback connection string (DATABASE_URL)
DATABASE_URL = os.getenv("DATABASE_URL")
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

# Check if PostgreSQL/Cloud SQL configuration is provided
if DATABASE_URL or POSTGRES_HOST or os.getenv("PGHOST"):
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        IS_POSTGRES = True
    except ImportError as e:
        db_conn_error = f"psycopg2 library not installed. Falling back to SQLite. Error: {e}"

def is_postgres_conn(conn):
    """Checks if the connection is a PostgreSQL/psycopg2 connection."""
    return type(conn).__module__.startswith("psycopg2")

def query_placeholder(sql, is_pg):
    """Replaces SQLite placeholder '?' with PostgreSQL placeholder '%s' if running on Postgres."""
    if is_pg:
        return sql.replace("?", "%s")
    return sql

def get_db_connection():
    """Establishes database connection.
    Attempts PostgreSQL if configured, otherwise falls back to local SQLite.
    """
    global IS_POSTGRES
    
    if IS_POSTGRES:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            if DATABASE_URL:
                conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
            else:
                conn = psycopg2.connect(
                    host=POSTGRES_HOST or os.getenv("PGHOST", "localhost"),
                    port=os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5432")),
                    user=POSTGRES_USER or os.getenv("PGUSER", "postgres"),
                    password=POSTGRES_PASSWORD or os.getenv("PGPASSWORD", "postgres"),
                    database=POSTGRES_DB or os.getenv("PGDATABASE", "postgres"),
                    cursor_factory=RealDictCursor
                )
            return conn
        except Exception as e:
            is_cloud = os.getenv("K_SERVICE") is not None or os.getenv("ENVIRONMENT") == "production"
            print(f"--> ERROR: PostgreSQL connection failed: {e}.")
            if is_cloud:
                print("--> CRITICAL: Running in a cloud environment (detected K_SERVICE or production). Falling back to SQLite is disabled to prevent silent data loss.")
                raise e
            else:
                print("--> Warning: Falling back to local SQLite for development.")
    
    # Fallback SQLite Connection
    is_cloud = os.getenv("K_SERVICE") is not None or os.getenv("ENVIRONMENT") == "production"
    if is_cloud:
        DB_PATH = "/tmp/carbon.db"
    else:
        DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carbon.db")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and seeds sample data."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    
    if is_pg:
        # 1. Create User/Account table for Postgres
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_summary (
            id SERIAL PRIMARY KEY,
            budget_limit REAL NOT NULL,
            current_usage REAL NOT NULL,
            points INTEGER NOT NULL
        )
        """)
        
        # 2. Create Transactions table for Postgres
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            date VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            type VARCHAR(50) NOT NULL,
            amount REAL NOT NULL,
            points_earned INTEGER NOT NULL,
            status VARCHAR(50) NOT NULL
        )
        """)
        
        # 3. Create Packages table for Postgres
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS travel_packages (
            id SERIAL PRIMARY KEY,
            destination VARCHAR(100) NOT NULL,
            duration_days INTEGER NOT NULL,
            flight_co2 REAL NOT NULL,
            car_co2 REAL NOT NULL,
            stay_co2 REAL NOT NULL,
            total_co2 REAL NOT NULL,
            price_usd REAL NOT NULL,
            details_json TEXT NOT NULL
        )
        """)
    else:
        # 1. Create User/Account table for SQLite
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            budget_limit REAL NOT NULL,
            current_usage REAL NOT NULL,
            points INTEGER NOT NULL
        )
        """)
        
        # 2. Create Transactions table for SQLite
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
        
        # 3. Create Packages table for SQLite
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
    count = cursor.fetchone()[0]
    if count == 0:
        if is_pg:
            cursor.execute("""
            INSERT INTO account_summary (budget_limit, current_usage, points)
            VALUES (%s, %s, %s)
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
            VALUES (%s, %s, %s, %s, %s, %s)
            """, seed_tx)
            
            # Seed travel packages for reference
            sample_details = {
                "flight": {"carrier": "Hawaiian Airlines (Biofuel flight)", "co2_kg": 420.0, "details": "Direct flight with carbon-neutral offset options"},
                "car": {"model": "Tesla Model Y", "co2_kg": 0.0, "details": "Electric vehicle rental, charging powered by local solar grid"},
                "stay": {"hotel": "Aloha Green Resort", "co2_kg": 35.0, "details": "LEED Gold Certified, solar-powered eco-resort"}
            }
            cursor.execute("""
            INSERT INTO travel_packages (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ("Hawaii", 3, 420.0, 0.0, 35.0, 455.0, 1250.0, json.dumps(sample_details)))
        else:
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
    """Gets the current user account summary."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM account_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"budget_limit": 5000.0, "current_usage": 0.0, "points": 0}

def update_summary(usage_change, points_change):
    """Updates the user carbon usage and reward points."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    # Get current summary
    cursor.execute("SELECT * FROM account_summary ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    if row:
        new_usage = max(0.0, row["current_usage"] + usage_change)
        new_points = max(0, row["points"] + points_change)
        sql = """
        UPDATE account_summary
        SET current_usage = ?, points = ?
        WHERE id = ?
        """
        cursor.execute(query_placeholder(sql, is_pg), (new_usage, new_points, row["id"]))
    conn.commit()
    conn.close()

def get_transactions():
    """Returns all transaction records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC, id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_transaction(date, description, tx_type, amount, points_earned, status):
    """Inserts a new transaction and updates account summary if completed."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO transactions (date, description, type, amount, points_earned, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    if is_pg:
        sql = query_placeholder(sql, is_pg) + " RETURNING id"
        cursor.execute(sql, (date, description, tx_type, amount, points_earned, status))
        tx_id = cursor.fetchone()["id"]
    else:
        cursor.execute(sql, (date, description, tx_type, amount, points_earned, status))
        tx_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    
    # If the transaction is completed, update the account summary automatically
    if status == "completed":
        update_summary(amount, points_earned)
        
    return tx_id

def update_transaction_status(tx_id, new_status):
    """Updates the status of a transaction and handles budget/points impact if transitioning to completed."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    
    # Check current status
    sql_check = "SELECT * FROM transactions WHERE id = ?"
    cursor.execute(query_placeholder(sql_check, is_pg), (tx_id,))
    row = cursor.fetchone()
    if row and row["status"] != new_status:
        sql_update = "UPDATE transactions SET status = ? WHERE id = ?"
        cursor.execute(query_placeholder(sql_update, is_pg), (new_status, tx_id))
        conn.commit()
        
        # If transitioning to completed, apply changes to summary
        if new_status == "completed":
            update_summary(row["amount"], row["points_earned"])
            
    conn.close()

def get_packages(destination, days):
    """Retrieves cached travel packages matching destination and duration."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    sql = """
    SELECT * FROM travel_packages
    WHERE LOWER(destination) = LOWER(?) AND duration_days = ?
    """
    cursor.execute(query_placeholder(sql, is_pg), (destination, days))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_package(destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details):
    """Caches a generated travel package in the database."""
    conn = get_db_connection()
    is_pg = is_postgres_conn(conn)
    cursor = conn.cursor()
    
    sql = """
    INSERT INTO travel_packages (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, details_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    if is_pg:
        sql = query_placeholder(sql, is_pg) + " RETURNING id"
        cursor.execute(sql, (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, json.dumps(details)))
        pkg_id = cursor.fetchone()["id"]
    else:
        cursor.execute(sql, (destination, duration_days, flight_co2, car_co2, stay_co2, total_co2, price_usd, json.dumps(details)))
        pkg_id = cursor.lastrowid
        
    conn.commit()
    conn.close()
    return pkg_id
