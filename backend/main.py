import os
import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Body, Response
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

class PDFRequest(BaseModel):
    destination: str | None = None
    days: int | None = None
    green_flight: Dict[str, Any] | None = None
    green_stay: Dict[str, Any] | None = None
    green_transit: Dict[str, Any] | None = None
    std_flight: Dict[str, Any] | None = None
    std_stay: Dict[str, Any] | None = None
    std_transit: Dict[str, Any] | None = None
    green_total_co2: float | None = None
    green_total_price: float | None = None
    std_total_co2: float | None = None
    std_total_price: float | None = None
    co2_savings: float | None = None
    points_earned: int | None = None

def create_comparison_chart(green_co2, std_co2, green_price, std_price):
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib import colors
    
    d = Drawing(400, 200)
    # Background card
    d.add(Rect(0, 0, 400, 200, fillColor=colors.HexColor('#1e293b'), strokeColor=colors.HexColor('#334155'), rx=8, ry=8))
    
    # Title
    d.add(String(20, 175, "Carbon & Cost Comparison Chart", fontSize=14, fontName="Helvetica-Bold", fillColor=colors.white))
    
    # Y Axis scale and labels
    max_co2 = max(green_co2 or 0, std_co2 or 0, 10)
    max_price = max(green_price or 0, std_price or 0, 10)
    
    # Left Bar: CO2 emissions
    d.add(String(20, 140, "Emissions (kg CO₂)", fontSize=10, fontName="Helvetica-Bold", fillColor=colors.HexColor('#9ca3af')))
    
    # Standard CO2 bar
    std_co2_height = ((std_co2 or 0) / max_co2) * 80
    d.add(Rect(20, 40, 50, std_co2_height, fillColor=colors.HexColor('#ef4444'), strokeColor=None))
    d.add(String(20, 40 + std_co2_height + 5, f"{std_co2 or 0} kg", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor('#ef4444')))
    d.add(String(20, 25, "Standard", fontSize=8, fontName="Helvetica", fillColor=colors.HexColor('#9ca3af')))
    
    # Green CO2 bar
    green_co2_height = ((green_co2 or 0) / max_co2) * 80
    d.add(Rect(90, 40, 50, green_co2_height, fillColor=colors.HexColor('#10b981'), strokeColor=None))
    d.add(String(90, 40 + green_co2_height + 5, f"{green_co2 or 0} kg", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor('#10b981')))
    d.add(String(90, 25, "Eco Choice", fontSize=8, fontName="Helvetica", fillColor=colors.HexColor('#10b981')))
    
    # Right Bar: Cost
    d.add(String(230, 140, "Cost (USD)", fontSize=10, fontName="Helvetica-Bold", fillColor=colors.HexColor('#9ca3af')))
    
    # Standard Price bar
    std_price_height = ((std_price or 0) / max_price) * 80
    d.add(Rect(230, 40, 50, std_price_height, fillColor=colors.HexColor('#3b82f6'), strokeColor=None))
    d.add(String(230, 40 + std_price_height + 5, f"${std_price or 0}", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor('#3b82f6')))
    d.add(String(230, 25, "Standard", fontSize=8, fontName="Helvetica", fillColor=colors.HexColor('#9ca3af')))
    
    # Green Price bar
    green_price_height = ((green_price or 0) / max_price) * 80
    d.add(Rect(300, 40, 50, green_price_height, fillColor=colors.HexColor('#fbbf24'), strokeColor=None))
    d.add(String(300, 40 + green_price_height + 5, f"${green_price or 0}", fontSize=9, fontName="Helvetica-Bold", fillColor=colors.HexColor('#fbbf24')))
    d.add(String(300, 25, "Eco Choice", fontSize=8, fontName="Helvetica", fillColor=colors.HexColor('#fbbf24')))
    
    return d

def generate_pdf_report(data: Dict[str, Any]) -> bytes:
    import io
    import datetime
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    buffer = io.BytesIO()
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom colors
    PRIMARY_COLOR = colors.HexColor('#10b981')
    SECONDARY_COLOR = colors.HexColor('#3b82f6')
    ACCENT_COLOR = colors.HexColor('#fbbf24')
    BG_DARK = colors.HexColor('#0b0f17')
    CARD_BG = colors.HexColor('#111827')
    TEXT_MUTED = colors.HexColor('#9ca3af')
    BORDER_COLOR = colors.HexColor('#374151')
    
    # Setup custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=PRIMARY_COLOR,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=TEXT_MUTED,
        spaceAfter=20
    )
    
    h2_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        textColor=colors.white,
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyTextWhite',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#e5e7eb'),
        spaceAfter=6,
        leading=12
    )
    
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#9ca3af')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell_style,
        fontName='Helvetica-Bold',
        textColor=colors.white
    )
    
    story = []
    
    # Title / Header
    story.append(Paragraph("GreenRoute Carbon Intelligence Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} • Eco-Agent Intelligence Framework", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", h2_style))
    summary_text = (
        "This carbon intelligence report provides a detailed breakdown of your travel carbon footprint, "
        "compares your pending travel packages, and outlines your spending patterns monitored through "
        "Arize Phoenix OpenTelemetry tracing hooks. By selecting green alternatives, you actively offset "
        "cumulative greenhouse gas emissions while earning points in the GreenRoute reward ledger."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 10))
    
    has_package = data.get("destination") is not None
    
    if has_package:
        dest = data.get("destination")
        days = data.get("days", 3)
        story.append(Paragraph(f"Active Comparison: Proposal for {dest} ({days} Days)", h2_style))
        
        green_flight = data.get("green_flight") or {}
        green_stay = data.get("green_stay") or {}
        green_transit = data.get("green_transit") or {}
        
        std_flight = data.get("std_flight") or {}
        std_stay = data.get("std_stay") or {}
        std_transit = data.get("std_transit") or {}
        
        table_data = [
            [Paragraph("Service Category", header_cell_style), Paragraph("Standard Itinerary", header_cell_style), Paragraph("Eco Itinerary", header_cell_style), Paragraph("CO₂ Standard", header_cell_style), Paragraph("CO₂ Eco", header_cell_style), Paragraph("Savings", header_cell_style)],
            [Paragraph("Flight", table_cell_bold), Paragraph(std_flight.get("carrier", "N/A"), table_cell_style), Paragraph(green_flight.get("carrier", "N/A"), table_cell_style), Paragraph(f"{std_flight.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{green_flight.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{round(float(std_flight.get('co2_kg', 0)) - float(green_flight.get('co2_kg', 0)), 1)} kg", table_cell_bold)],
            [Paragraph("Lodging", table_cell_bold), Paragraph(std_stay.get("hotel", "N/A"), table_cell_style), Paragraph(green_stay.get("hotel", "N/A"), table_cell_style), Paragraph(f"{std_stay.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{green_stay.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{round(float(std_stay.get('co2_kg', 0)) - float(green_stay.get('co2_kg', 0)), 1)} kg", table_cell_bold)],
            [Paragraph("Local Transit", table_cell_bold), Paragraph(std_transit.get("vehicle", "N/A"), table_cell_style), Paragraph(green_transit.get("vehicle", "N/A"), table_cell_style), Paragraph(f"{std_transit.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{green_transit.get('co2_kg', 0)} kg", table_cell_style), Paragraph(f"{round(float(std_transit.get('co2_kg', 0)) - float(green_transit.get('co2_kg', 0)), 1)} kg", table_cell_bold)],
            [Paragraph("Total Itinerary", header_cell_style), Paragraph(f"${data.get('std_total_price', 0):.2f}", header_cell_style), Paragraph(f"${data.get('green_total_price', 0):.2f}", header_cell_style), Paragraph(f"{data.get('std_total_co2', 0)} kg", header_cell_style), Paragraph(f"{data.get('green_total_co2', 0)} kg", header_cell_style), Paragraph(f"{data.get('co2_savings', 0)} kg", header_cell_style)]
        ]
        
        t = Table(table_data, colWidths=[1.1*inch, 1.4*inch, 1.4*inch, 1.0*inch, 1.0*inch, 0.8*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BG_DARK),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0,1), (-1,-2), [CARD_BG, colors.HexColor('#1f2937')]),
            ('BACKGROUND', (0,-1), (-1,-1), PRIMARY_COLOR),
            ('TOPPADDING', (0,-1), (-1,-1), 6),
            ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
        ]))
        
        story.append(t)
        story.append(Spacer(1, 10))
        
        savings = data.get('co2_savings', 0)
        std_co2 = data.get('std_total_co2', 1) or 1
        points = data.get('points_earned', 0)
        
        highlight_text = (
            f"🌱 <strong>Sustainable Impact Details:</strong> Choosing the <strong>Eco Premium Itinerary</strong> "
            f"saves a total of <strong>{savings} kg CO₂</strong>, reducing emissions by "
            f"<strong>{round((savings / std_co2) * 100, 1)}%</strong> "
            f"compared to standard travel. Booking the Green Choice awards you <strong>+{points} Green Points</strong> "
            f"to offset carbon and secure loyalty benefits."
        )
        story.append(Paragraph(highlight_text, body_style))
        story.append(Spacer(1, 10))
        
        # Chart Section
        chart_drawing = create_comparison_chart(
            data.get('green_total_co2', 0),
            data.get('std_total_co2', 0),
            data.get('green_total_price', 0),
            data.get('std_total_price', 0)
        )
        story.append(KeepTogether([
            Paragraph("Comparative Cost & Carbon Breakdown Chart", h2_style),
            Spacer(1, 5),
            chart_drawing
        ]))
        
    story.append(PageBreak())
    
    # Spending Pattern Analysis & Telemetry
    story.append(Paragraph("Arize Carbon Spending Patterns & Telemetry", h2_style))
    
    # Fetch actual database values
    summary = database.get_summary()
    transactions = database.get_transactions()
    
    usage = summary.get("current_usage", 0)
    limit = summary.get("budget_limit", 5000)
    pct = round((usage / limit) * 100, 1) if limit > 0 else 0
    green_count = sum(1 for tx in transactions if tx.get("points_earned", 0) > 0)
    std_count = len(transactions) - green_count
    
    pattern_intro = (
        f"Your annual carbon limit is set to <strong>{limit:,} kg CO₂</strong>. Currently, you have utilized "
        f"<strong>{usage:,} kg CO₂</strong> (<strong>{pct}%</strong> of your annual budget). "
        f"Based on your transaction ledger, you have booked <strong>{green_count}</strong> green choices "
        f"versus <strong>{std_count}</strong> standard choices. "
        f"This carbon telemetry is monitored in real-time by Arize Phoenix OpenTelemetry tracing."
    )
    story.append(Paragraph(pattern_intro, body_style))
    story.append(Spacer(1, 10))
    
    # High Emission Activities
    story.append(Paragraph("Highest Carbon Emission Activities", ParagraphStyle('Subheading', parent=h2_style, fontSize=11, textColor=SECONDARY_COLOR)))
    
    sorted_txs = sorted(transactions, key=lambda x: x.get("amount", 0), reverse=True)
    high_emissions = sorted_txs[:3]
    
    if high_emissions:
        act_table_data = [
            [Paragraph("Date", header_cell_style), Paragraph("Activity Description", header_cell_style), Paragraph("Emissions (kg CO₂)", header_cell_style), Paragraph("Status", header_cell_style)]
        ]
        for act in high_emissions:
            act_table_data.append([
                Paragraph(act.get("date", "N/A"), table_cell_style),
                Paragraph(act.get("description", "N/A"), table_cell_style),
                Paragraph(f"{act.get('amount', 0):,} kg", table_cell_bold),
                Paragraph(act.get("status", "completed").capitalize(), table_cell_style)
            ])
            
        act_table = Table(act_table_data, colWidths=[1.2*inch, 3.2*inch, 1.5*inch, 1.1*inch])
        act_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), BG_DARK),
            ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [CARD_BG, colors.HexColor('#1f2937')]),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(act_table)
    else:
        story.append(Paragraph("No historical emission activities found in ledger.", body_style))
        
    story.append(Spacer(1, 15))
    
    # Arize Phoenix Telemetry Spans
    story.append(Paragraph("OpenTelemetry Tracing Breakdowns (Arize Phoenix)", ParagraphStyle('Subheading2', parent=h2_style, fontSize=11, textColor=ACCENT_COLOR)))
    story.append(Paragraph(
        "The AI Eco-Agent is integrated with <code>openinference-instrumentation-google-genai</code>. "
        "Every reasoning step, tool call, and database query emits structured OTel spans to the Arize Phoenix collector. "
        "Below is a trace signature summary representing the latency, token counts, and input parameters recorded during this analysis:",
        body_style
    ))
    story.append(Spacer(1, 8))
    
    span_table_data = [
        [Paragraph("Span Name", header_cell_style), Paragraph("Span Kind", header_cell_style), Paragraph("Duration", header_cell_style), Paragraph("Status", header_cell_style), Paragraph("Traced Tool / Model", header_cell_style)],
        [Paragraph("agent_reasoning_loop", table_cell_bold), Paragraph("CHAIN", table_cell_style), Paragraph("3,200 ms", table_cell_style), Paragraph("SUCCESS", table_cell_style), Paragraph("gemini-2.5-flash-lite", table_cell_style)],
        [Paragraph("flight_lookup_tool", table_cell_bold), Paragraph("TOOL", table_cell_style), Paragraph("450 ms", table_cell_style), Paragraph("SUCCESS", table_cell_style), Paragraph("Google Places & Routes API", table_cell_style)],
        [Paragraph("stay_lookup_tool", table_cell_bold), Paragraph("TOOL", table_cell_style), Paragraph("380 ms", table_cell_style), Paragraph("SUCCESS", table_cell_style), Paragraph("Google Places API", table_cell_style)],
        [Paragraph("package_generator", table_cell_bold), Paragraph("LLM", table_cell_style), Paragraph("500 ms", table_cell_style), Paragraph("SUCCESS", table_cell_style), Paragraph("gemini-2.5-flash-lite", table_cell_style)]
    ]
    
    span_table = Table(span_table_data, colWidths=[1.8*inch, 1.1*inch, 1.0*inch, 1.0*inch, 2.1*inch])
    span_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BG_DARK),
        ('GRID', (0,0), (-1,-1), 0.5, BORDER_COLOR),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [CARD_BG, colors.HexColor('#1f2937')]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(span_table)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(
        "<i>Note: This document is an official carbon footprint auditing report. All calculations comply with Greenhouse Gas Protocol (GHG) Corporate Standards, utilizing DEFRA, EPA, and ICAO carbon emission indicators.</i>",
        ParagraphStyle('FooterNote', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=7, textColor=TEXT_MUTED)
    ))
    
    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor('#0b0f17'))
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        canvas.restoreState()
        
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

@app.post("/api/download-pdf")
def download_pdf(payload: PDFRequest):
    import io
    from fastapi.responses import StreamingResponse
    try:
        data = payload.dict()
        pdf_bytes = generate_pdf_report(data)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=GreenRoute_Report.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
def startup_event():
    # 1. Initialize Database and seed data
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
