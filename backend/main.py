import os
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Local imports
from backend import database
from backend import agent
from backend import arize_integration

app = FastAPI(title="Carbon Account API")

# Configure CORS so our React frontend can access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatMessage(BaseModel):
    sender: str
    text: str
    timestamp: str
    type: str = 'text'

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []
    package_context: Dict[str, Any] | None = None

class BookRequest(BaseModel):
    destination: str
    days: int
    package_type: str  # "green" or "standard"
    description: str
    co2_amount: float
    price_usd: float
    points_earned: int

class ConfirmRequest(BaseModel):
    tx_id: int

@app.on_event("startup")
def startup_event():
    # 1. Initialize SQLite Database and seed data
    database.init_db()
    print("--> Database initialized and seeded.")
    
    # 2. Start Arize Phoenix Server and setup OTel tracing
    try:
        arize_integration.init_arize()
        print("--> Arize Phoenix initialized.")
    except Exception as e:
        print(f"--> Warning: Could not initialize Arize Phoenix: {e}")

@app.get("/api/summary")
def get_summary():
    try:
        return database.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transactions")
def get_transactions():
    try:
        return database.get_transactions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/agent")
def run_agent(payload: ChatRequest):
    try:
        if not payload.query or len(payload.query.strip()) < 3:
            raise HTTPException(status_code=400, detail="Query must be at least 3 characters long")

        response = agent.execute_agent_loop(
            payload.query,
            history=[msg.dict() for msg in payload.history] if payload.history else [],
            package_context=payload.package_context
        )
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/book")
def book_trip(payload: BookRequest):
    try:
        # Save booking as pending
        date_str = datetime.date.today().isoformat()
        status = "pending"
        
        # Determine transaction type and details
        tx_type = "flight"
        description = f"Trip to {payload.destination} ({payload.days} Days) - {payload.description}"
        
        # If standard, no points earned
        points = payload.points_earned if payload.package_type == "green" else 0
        
        tx_id = database.add_transaction(
            date=date_str,
            description=description,
            tx_type=tx_type,
            amount=payload.co2_amount,
            points_earned=points,
            status=status
        )
        
        return {"tx_id": tx_id, "status": status, "message": "Booking is now pending confirmation."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/confirm-booking")
def confirm_booking(payload: ConfirmRequest):
    try:
        database.update_transaction_status(payload.tx_id, "completed")
        return {"status": "completed", "message": "Booking confirmed! Carbon budget updated and points awarded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cancel-booking")
def cancel_booking(payload: ConfirmRequest):
    try:
        # We can just remove the transaction or mark it as cancelled
        # For simplicity, let's update status to cancelled
        database.update_transaction_status(payload.tx_id, "cancelled")
        return {"status": "cancelled", "message": "Booking cancelled."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trajectory")
def get_trajectory():
    try:
        summary = database.get_summary()
        current_usage = summary["current_usage"]
        limit = summary["budget_limit"]
        
        # We assume we are in month 6 (June) out of 12
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_month_idx = 5  # June (0-indexed)
        
        # Cumulative actuals (hardcoded historical progression leading up to current database value)
        actuals_baseline = [310, 640, 990, 1310, 1620, current_usage]
        
        # Calculate monthly budget slice
        monthly_limit = limit / 12
        
        data = []
        for i, m in enumerate(months):
            month_limit = round(monthly_limit * (i + 1), 1)
            
            # Baseline is if the user makes no green adjustments (approx 420 kg / month)
            baseline = round(420 * (i + 1), 1)
            
            actual = None
            projected = None
            
            if i <= current_month_idx:
                # Historical
                actual = round(actuals_baseline[i], 1)
                projected = actual
            else:
                # Future projections
                # Under green choices, average monthly consumption drops to 290 kg / month
                past_usage = actuals_baseline[current_month_idx]
                months_remaining = i - current_month_idx
                projected = round(past_usage + (months_remaining * 290), 1)
                
            data.append({
                "month": m,
                "limit": month_limit,
                "actual": actual,
                "projected": projected,
                "baseline": baseline
            })
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/carbon-patterns")
def get_carbon_patterns():
    """
    Analyze carbon spending patterns with Arize observability.
    Sends detailed spans to Phoenix showing emission trends, breakdowns, and insights.
    """
    try:
        from opentelemetry import trace
        tracer = trace.get_tracer("carbon-patterns-analyzer")
        
        with tracer.start_as_current_span("carbon_spending_analysis") as span:
            span.set_attribute("analysis.type", "carbon_emissions_patterns")
            
            # Get summary and transactions
            summary = database.get_summary()
            transactions = database.get_transactions()
            
            # Analyze spending patterns
            patterns = {
                "total_emissions": summary["current_usage"],
                "budget_limit": summary["budget_limit"],
                "budget_used_percent": round((summary["current_usage"] / summary["budget_limit"]) * 100, 1),
                "points_earned": summary["points"],
                "breakdown_by_type": {},
                "green_vs_standard": {"green": 0, "standard": 0},
                "high_emission_activities": [],
                "trends": {}
            }
            
            # Break down by transaction type
            for tx in transactions:
                tx_type = tx.get("type", "unknown")
                amount = tx.get("amount", 0)
                
                if tx_type not in patterns["breakdown_by_type"]:
                    patterns["breakdown_by_type"][tx_type] = {"total": 0, "count": 0, "avg": 0}
                
                patterns["breakdown_by_type"][tx_type]["total"] += amount
                patterns["breakdown_by_type"][tx_type]["count"] += 1
            
            # Calculate averages
            for tx_type, data in patterns["breakdown_by_type"].items():
                if data["count"] > 0:
                    data["avg"] = round(data["total"] / data["count"], 1)
            
            # Identify high-emission activities (top 3)
            sorted_txs = sorted(transactions, key=lambda x: x.get("amount", 0), reverse=True)
            patterns["high_emission_activities"] = [
                {
                    "description": tx.get("description", ""),
                    "amount": tx.get("amount", 0),
                    "date": tx.get("date", ""),
                    "status": tx.get("status", "")
                }
                for tx in sorted_txs[:3]
            ]
            
            # Count green vs standard (approximation based on points)
            patterns["green_vs_standard"]["green"] = sum(1 for tx in transactions if tx.get("points_earned", 0) > 0)
            patterns["green_vs_standard"]["standard"] = len(transactions) - patterns["green_vs_standard"]["green"]
            
            # Calculate monthly trend
            monthly_breakdown = {}
            for tx in transactions:
                date = tx.get("date", "")
                if date:
                    month = date[:7]  # YYYY-MM format
                    if month not in monthly_breakdown:
                        monthly_breakdown[month] = 0
                    monthly_breakdown[month] += tx.get("amount", 0)
            
            patterns["trends"] = {
                "monthly": monthly_breakdown,
                "average_per_transaction": round(summary["current_usage"] / max(len(transactions), 1), 1),
                "trajectory": "increasing" if len(transactions) > 0 and transactions[-1].get("amount", 0) > (summary["current_usage"] / len(transactions)) else "stable"
            }
            
            # Add comprehensive span attributes for Arize observability
            span.set_attribute("emissions.total_kg", summary["current_usage"])
            span.set_attribute("emissions.budget_limit_kg", summary["budget_limit"])
            span.set_attribute("emissions.budget_utilization_percent", patterns["budget_used_percent"])
            span.set_attribute("emissions.points_earned", summary["points"])
            span.set_attribute("emissions.breakdown_types", len(patterns["breakdown_by_type"]))
            span.set_attribute("emissions.green_count", patterns["green_vs_standard"]["green"])
            span.set_attribute("emissions.standard_count", patterns["green_vs_standard"]["standard"])
            span.set_attribute("emissions.trend", patterns["trends"]["trajectory"])
            span.set_attribute("emissions.avg_per_transaction", patterns["trends"]["average_per_transaction"])
            span.set_attribute("analysis.transaction_count", len(transactions))
            
            # Add type breakdown as span attributes
            for tx_type, data in patterns["breakdown_by_type"].items():
                span.set_attribute(f"emissions.breakdown.{tx_type}.total", data["total"])
                span.set_attribute(f"emissions.breakdown.{tx_type}.count", data["count"])
                span.set_attribute(f"emissions.breakdown.{tx_type}.average", data["avg"])
            
            return patterns
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    # Dynamically select module path depending on if run from root or backend directory
    module_path = "backend.main:app" if os.path.exists("backend") else "main:app"
    uvicorn.run(module_path, host="127.0.0.1", port=8000, reload=True)
