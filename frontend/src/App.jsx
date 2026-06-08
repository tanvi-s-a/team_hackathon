import React, { useState, useEffect } from 'react';
import {
  Leaf,
  Plane,
  Car,
  Hotel,
  TrendingUp,
  Award,
  History,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Database,
  Calendar,
  DollarSign,
  Check,
  X,
  ExternalLink,
  ShieldCheck,
  ArrowRight,
  Clock,
  Gauge
} from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [summary, setSummary] = useState({ budget_limit: 5000, current_usage: 1840, points: 650 });
  const [transactions, setTransactions] = useState([]);
  const [trajectory, setTrajectory] = useState([]);
  const [toastMessage, setToastMessage] = useState('');
  const [pointsAnimate, setPointsAnimate] = useState(false);

  // Agent State
  const [prompt, setPrompt] = useState('i want to travel to hawaii on a 3-day trip, give me carbon-efficient package for flights, car trips, and places for 3 days');
  const [loading, setLoading] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [currentPackages, setCurrentPackages] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const showToast = (message) => {
    setToastMessage(message);
    setTimeout(() => {
      setToastMessage('');
    }, 4000);
  };

  const fetchData = async () => {
    try {
      const summaryRes = await fetch(`${API_URL}/api/summary`);
      const summaryData = await summaryRes.json();
      setSummary(summaryData);

      const txRes = await fetch(`${API_URL}/api/transactions`);
      const txData = await txRes.json();
      setTransactions(txData);

      const trajRes = await fetch(`${API_URL}/api/trajectory`);
      const trajData = await trajRes.json();
      setTrajectory(trajData);
    } catch (err) {
      console.error("Error fetching data:", err);
    }
  };

  const runAgent = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setCurrentPackages(null);
    setThinkingSteps([]);

    // Simulated thinking steps to mimic reasoning loop
    const steps = [
      { id: 1, text: "Initializing Carbon account travel agent..." },
      { id: 2, text: "Parsing destination and duration from your query..." },
      { id: 3, text: "Querying green flights database (Sustainable Aviation Fuel records)..." },
      { id: 4, text: "Looking up EV rentals & solar charging availability..." },
      { id: 5, text: "Retrieving eco-resorts with LEED ratings in destination..." },
      { id: 6, text: "Synthesizing packages & compiling carbon/points savings..." }
    ];

    for (let i = 0; i < steps.length; i++) {
      setThinkingSteps(prev => [...prev.map(s => ({ ...s, active: false })), { ...steps[i], active: true }]);
      await new Promise(r => setTimeout(r, 900));
      setThinkingSteps(prev => prev.map(s => s.id === steps[i].id ? { ...s, active: false, completed: true } : s));
    }

    try {
      const res = await fetch(`${API_URL}/api/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: prompt })
      });
      if (!res.ok) throw new Error("Agent request failed");
      const data = await res.json();
      setCurrentPackages(data);
      showToast("Agent packages synthesized successfully!");
    } catch (err) {
      console.error(err);
      showToast("Error executing agent loop. Make sure backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const bookTrip = async (packageType) => {
    if (!currentPackages) return;

    const isGreen = packageType === 'green';
    const pkg = isGreen ? currentPackages.green_choice : currentPackages.standard_choice;

    try {
      const res = await fetch(`${API_URL}/api/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: currentPackages.destination,
          days: currentPackages.days,
          package_type: packageType,
          description: isGreen ? "Eco Premium Package" : "Standard Package",
          co2_amount: pkg.total_co2,
          price_usd: pkg.total_price_usd,
          points_earned: isGreen ? pkg.points_earned : 0
        })
      });
      
      const data = await res.json();
      showToast(`Package booked! Status: ${data.status.toUpperCase()}. Go to transactions page to confirm.`);
      fetchData();
      setActiveTab('transactions');
    } catch (err) {
      console.error(err);
      showToast("Failed to book trip.");
    }
  };

  const confirmBooking = async (txId) => {
    try {
      const res = await fetch(`${API_URL}/api/confirm-booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tx_id: txId })
      });
      const data = await res.json();
      showToast(data.message);
      
      // Points animation trigger
      setPointsAnimate(true);
      setTimeout(() => setPointsAnimate(false), 1000);

      fetchData();
    } catch (err) {
      console.error(err);
      showToast("Error confirming transaction.");
    }
  };

  const cancelBooking = async (txId) => {
    try {
      const res = await fetch(`${API_URL}/api/cancel-booking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tx_id: txId })
      });
      const data = await res.json();
      showToast(data.message);
      fetchData();
    } catch (err) {
      console.error(err);
      showToast("Error cancelling booking.");
    }
  };

  // Render budget ratio and progress fill color
  const budgetRatio = summary.current_usage / summary.budget_limit;
  const progressPercent = Math.min(100, budgetRatio * 100);
  let progressColor = 'green';
  if (budgetRatio > 0.85) progressColor = 'danger';
  else if (budgetRatio > 0.65) progressColor = 'warning';

  // Custom SVG Chart parameters
  const chartWidth = 700;
  const chartHeight = 220;
  const padding = { top: 20, right: 30, bottom: 30, left: 50 };

  const getCoordinates = (index, val) => {
    const x = padding.left + (index * (chartWidth - padding.left - padding.right) / 11);
    // scale y based on max value (~6000 kg CO2)
    const y = chartHeight - padding.bottom - (val * (chartHeight - padding.top - padding.bottom) / 6000);
    return { x, y };
  };

  // Build SVG Paths
  let limitPath = '';
  let baselinePath = '';
  let projectedPath = '';

  trajectory.forEach((d, i) => {
    const limitCoord = getCoordinates(i, d.limit);
    const baselineCoord = getCoordinates(i, d.baseline);
    const projectedCoord = getCoordinates(i, d.projected);

    if (i === 0) {
      limitPath = `M ${limitCoord.x} ${limitCoord.y}`;
      baselinePath = `M ${baselineCoord.x} ${baselineCoord.y}`;
      projectedPath = `M ${projectedCoord.x} ${projectedCoord.y}`;
    } else {
      limitPath += ` L ${limitCoord.x} ${limitCoord.y}`;
      baselinePath += ` L ${baselineCoord.x} ${baselineCoord.y}`;
      projectedPath += ` L ${projectedCoord.x} ${projectedCoord.y}`;
    }
  });

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <div className="sidebar">
        <div className="logo-container">
          <Leaf className="logo-icon" size={26} />
          <span>CarbonAccount</span>
        </div>
        <ul className="nav-links">
          <li>
            <a 
              className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
              onClick={() => setActiveTab('overview')}
            >
              <Gauge className="nav-item-icon" size={18} />
              <span>Overview</span>
            </a>
          </li>
          <li>
            <a 
              className={`nav-item ${activeTab === 'agent' ? 'active' : ''}`}
              onClick={() => setActiveTab('agent')}
            >
              <Sparkles className="nav-item-icon" size={18} />
              <span>AI Eco-Agent</span>
            </a>
          </li>
          <li>
            <a 
              className={`nav-item ${activeTab === 'transactions' ? 'active' : ''}`}
              onClick={() => setActiveTab('transactions')}
            >
              <History className="nav-item-icon" size={18} />
              <span>Ledger & Status</span>
            </a>
          </li>
        </ul>

        {/* Sidebar footer showing live tracing status */}
        <div style={{ marginTop: 'auto', fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', display: 'inline-block', boxShadow: '0 0 8px #10b981' }}></span>
            <span style={{ fontWeight: 600, color: 'var(--text-secondary)' }}>Arize Phoenix Server</span>
          </div>
          <p style={{ lineHeight: 1.4 }}>OpenInference Agent Tracing Active on <span style={{ fontFamily: 'monospace', color: 'var(--primary)' }}>http://localhost:6006</span></p>
          <a href="http://localhost:6006" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', color: 'var(--secondary)', textDecoration: 'none', marginTop: '0.5rem', fontWeight: 600 }}>
            Open Dashboard <ExternalLink size={12} />
          </a>
        </div>
      </div>

      {/* Main Panel */}
      <div className="main-content">
        {/* Header */}
        <div className="header">
          <div>
            <h1 style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '2rem', marginBottom: '0.25rem' }}>
              {activeTab === 'overview' && "Carbon Portfolio Overview"}
              {activeTab === 'agent' && "Book Eco Travel Packages"}
              {activeTab === 'transactions' && "Carbon Account Statement"}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {activeTab === 'overview' && "Track your budget, points ledger, and carbon trajectory."}
              {activeTab === 'agent' && "Consult the AI Agent to draft and book carbon-efficient travel itineraries."}
              {activeTab === 'transactions' && "Review past expenditures, pending bookings, and offsets."}
            </p>
          </div>

          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <div className={`glass-card ${pointsAnimate ? 'points-animate' : ''}`} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.5rem 1.25rem', borderRadius: '12px' }}>
              <Award className="points-icon" size={20} style={{ color: 'var(--accent)' }} />
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Green Points</div>
                <div style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: '1.2rem', color: 'var(--accent)' }}>{summary.points}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Arize Info Alert Box */}
        <div className="arize-alert">
          <Database className="arize-alert-icon" size={18} />
          <div>
            <strong>Observability Active:</strong> This application is instrumented using <strong>Arize Phoenix</strong> and <strong>OpenTelemetry</strong> standards. All agent plans, tool calls, and LLM completions are tracked live. You can view agent workflows, latencies, and span variables by opening the <a href="http://localhost:6006" target="_blank" rel="noopener noreferrer" className="arize-link">Arize Phoenix console (localhost:6006)</a>.
          </div>
        </div>

        {/* ==================== TAB: OVERVIEW ==================== */}
        {activeTab === 'overview' && (
          <div>
            {/* Top Cards Row */}
            <div className="summary-container">
              <div className="glass-card summary-card">
                <div className="summary-icon-wrapper primary">
                  <Leaf size={24} />
                </div>
                <div className="summary-info">
                  <h3>Cumulative Footprint</h3>
                  <p>{summary.current_usage.toLocaleString()} kg CO₂</p>
                </div>
              </div>

              <div className="glass-card summary-card">
                <div className="summary-icon-wrapper secondary">
                  <TrendingUp size={24} />
                </div>
                <div className="summary-info">
                  <h3>Annual Carbon Budget</h3>
                  <p>{summary.budget_limit.toLocaleString()} kg CO₂</p>
                </div>
              </div>

              <div className="glass-card summary-card">
                <div className="summary-icon-wrapper accent">
                  <Award size={24} />
                </div>
                <div className="summary-info">
                  <h3>Budget Remaining</h3>
                  <p>{Math.max(0, summary.budget_limit - summary.current_usage).toLocaleString()} kg CO₂</p>
                </div>
              </div>
            </div>

            {/* Budget Progress Meter */}
            <div className="glass-card" style={{ marginBottom: '2rem' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 600, marginBottom: '1.25rem' }}>Carbon Budget Utilization</h2>
              <div className="progress-container">
                <div className="progress-header">
                  <span>{progressPercent.toFixed(1)}% of Annual Limit Used</span>
                  <span>{summary.current_usage.toLocaleString()} / {summary.budget_limit.toLocaleString()} kg CO₂</span>
                </div>
                <div className="progress-track">
                  <div className={`progress-fill ${progressColor}`} style={{ width: `${progressPercent}%` }}></div>
                </div>
                <p style={{ marginTop: '0.75rem', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <ShieldCheck size={14} style={{ color: 'var(--primary)' }} />
                  {budgetRatio <= 0.85 ? "Excellent work! Your carbon spending is well within standard limits." : "Caution: Carbon budget limits approaching. We suggest using green offset packages."}
                </p>
              </div>
            </div>

            {/* Chart Section */}
            <div className="glass-card chart-container">
              <div className="chart-header">
                <h2 className="chart-title">Carbon Emission Trajectory Prediction</h2>
                <div className="chart-legends">
                  <div className="legend-item">
                    <span className="legend-color limit"></span>
                    <span>Annual Budget Limit</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color baseline"></span>
                    <span>Baseline Trajectory (Business As Usual)</span>
                  </div>
                  <div className="legend-item">
                    <span className="legend-color projected"></span>
                    <span>Projected Trajectory (With Eco-Agent)</span>
                  </div>
                </div>
              </div>

              {trajectory.length > 0 ? (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <svg className="svg-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} preserveAspectRatio="xMidYMid meet">
                    {/* Grid Lines */}
                    {[1000, 2000, 3000, 4000, 5000, 6000].map((val, idx) => {
                      const coord = getCoordinates(0, val);
                      return (
                        <g key={val}>
                          <line 
                            x1={padding.left} 
                            y1={coord.y} 
                            x2={chartWidth - padding.right} 
                            y2={coord.y} 
                            className="chart-grid-line" 
                          />
                          <text 
                            x={padding.left - 10} 
                            y={coord.y + 4} 
                            textAnchor="end" 
                            className="chart-text"
                          >
                            {val} kg
                          </text>
                        </g>
                      );
                    })}

                    {/* Horizontal Axis Grid line (X-Axis) */}
                    <line 
                      x1={padding.left} 
                      y1={chartHeight - padding.bottom} 
                      x2={chartWidth - padding.right} 
                      y2={chartHeight - padding.bottom} 
                      className="chart-axis-line" 
                    />

                    {/* X-Axis labels */}
                    {trajectory.map((d, idx) => {
                      const coord = getCoordinates(idx, 0);
                      return (
                        <text 
                          key={idx}
                          x={coord.x} 
                          y={chartHeight - padding.bottom + 18} 
                          textAnchor="middle" 
                          className="chart-text"
                        >
                          {d.month}
                        </text>
                      );
                    })}

                    {/* Paths */}
                    <path d={limitPath} className="chart-line limit" />
                    <path d={baselinePath} className="chart-line baseline" />
                    <path d={projectedPath} className="chart-line projected" />

                    {/* Data Points */}
                    {trajectory.map((d, idx) => {
                      const basePt = getCoordinates(idx, d.baseline);
                      const projPt = getCoordinates(idx, d.projected);
                      
                      return (
                        <g key={idx}>
                          <circle cx={basePt.x} cy={basePt.y} className="chart-dot baseline" />
                          <circle cx={projPt.x} cy={projPt.y} className="chart-dot projected" />
                        </g>
                      );
                    })}
                  </svg>
                </div>
              ) : (
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                  Loading trajectory predictions...
                </div>
              )}

              <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '12px' }}>
                <p>💡 <strong>Predictive Model Insight:</strong> By scheduling and booking travels via the <strong>AI Eco-Agent</strong>, your carbon output is projected to flatten to <strong>3,880 kg CO₂</strong> by December (saving 1,640 kg CO₂ over the baseline trend), allowing you to stay comfortably under your 5,000 kg budget and secure additional reward points.</p>
              </div>
            </div>
          </div>
        )}

        {/* ==================== TAB: AI BOOKING AGENT ==================== */}
        {activeTab === 'agent' && (
          <div className="agent-container">
            <div className="glass-card">
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} style={{ color: 'var(--primary)' }} />
                Consult Carbon-Conscious Travel Agent
              </h2>
              
              <form onSubmit={runAgent}>
                <div className="agent-prompt-wrapper">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Enter trip details (e.g. Hawaii on a 3-day trip, eco package...)"
                    className="agent-input"
                    disabled={loading}
                  />
                  <button type="submit" className="agent-btn" disabled={loading}>
                    <ArrowRight size={20} />
                  </button>
                </div>
              </form>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                Try: <em>"i want to travel to hawaii on a 3-day trip, give me carbon-efficient package for flights, car trips, and places for 3 days"</em> or <em>"trip to London for 5 days with low emissions"</em>.
              </p>
            </div>

            {/* Thinking / Running agent steps */}
            {loading && (
              <div className="agent-thinking">
                <div className="thinking-header">
                  <div className="spinner"></div>
                  <span>Agent running reasoning loop... (Sending OTel traces to Phoenix)</span>
                </div>
                <div className="thinking-steps">
                  {thinkingSteps.map((step) => (
                    <div 
                      key={step.id} 
                      className={`thinking-step ${step.active ? 'active' : ''} ${step.completed ? 'completed' : ''}`}
                    >
                      <span className="step-bullet"></span>
                      <span>{step.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Synthesized packages results */}
            {currentPackages && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                {/* Comparison Title Card */}
                <div className="glass-card" style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(21, 28, 44, 0.6) 100%)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)' }}>
                      Travel Packages for {currentPackages.destination} ({currentPackages.days} Days)
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
                      Choosing the Eco package saves <strong>{currentPackages.green_choice.co2_savings} kg CO₂</strong>.
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Points Reward</div>
                    <div style={{ color: 'var(--accent)', fontFamily: 'var(--font-heading)', fontSize: '1.8rem', fontWeight: 800 }}>+{currentPackages.green_choice.points_earned} PTS</div>
                  </div>
                </div>

                {/* Side by side cards */}
                <div className="packages-wrapper">
                  {/* Eco-Green Package */}
                  <div className="glass-card package-card recommended">
                    <span className="badge-recommended">Eco Choice</span>
                    <div className="package-header">
                      <h3 className="package-title">Eco Premium Itinerary</h3>
                      <span className="package-co2-badge eco">
                        <Leaf size={14} />
                        {currentPackages.green_choice.total_co2} kg CO₂ Total
                      </span>
                    </div>

                    <div className="package-body">
                      <div className="package-item eco">
                        <div className="package-item-icon">
                          <Plane size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Flight Option</h4>
                          <p>{currentPackages.green_choice.flight.carrier}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.green_choice.flight.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.green_choice.flight.co2_kg} kg</div>
                      </div>

                      <div className="package-item eco">
                        <div className="package-item-icon">
                          <Hotel size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Accommodation</h4>
                          <p>{currentPackages.green_choice.stay.hotel}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.green_choice.stay.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.green_choice.stay.co2_kg} kg</div>
                      </div>

                      <div className="package-item eco">
                        <div className="package-item-icon">
                          <Car size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Local Transit</h4>
                          <p>{currentPackages.green_choice.transit.vehicle}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.green_choice.transit.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.green_choice.transit.co2_kg} kg</div>
                      </div>

                      <div className="package-summary">
                        <strong>AI Summary justification:</strong> {currentPackages.green_choice.summary}
                      </div>
                    </div>

                    <div className="package-footer">
                      <div className="package-price-info">
                        <h5>Estimated Cost</h5>
                        <p>${currentPackages.green_choice.total_price_usd.toLocaleString()}</p>
                      </div>
                      <button className="package-action-btn primary" onClick={() => bookTrip('green')}>
                        Book Green Choice
                      </button>
                    </div>
                  </div>

                  {/* Standard Package */}
                  <div className="glass-card package-card">
                    <div className="package-header">
                      <h3 className="package-title">Standard Baseline Itinerary</h3>
                      <span className="package-co2-badge standard">
                        <AlertCircle size={14} />
                        {currentPackages.standard_choice.total_co2} kg CO₂ Total
                      </span>
                    </div>

                    <div className="package-body">
                      <div className="package-item">
                        <div className="package-item-icon">
                          <Plane size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Flight Option</h4>
                          <p>{currentPackages.standard_choice.flight.carrier}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.standard_choice.flight.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.standard_choice.flight.co2_kg} kg</div>
                      </div>

                      <div className="package-item">
                        <div className="package-item-icon">
                          <Hotel size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Accommodation</h4>
                          <p>{currentPackages.standard_choice.stay.hotel}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.standard_choice.stay.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.standard_choice.stay.co2_kg} kg</div>
                      </div>

                      <div className="package-item">
                        <div className="package-item-icon">
                          <Car size={18} />
                        </div>
                        <div className="package-item-details">
                          <h4>Local Transit</h4>
                          <p>{currentPackages.standard_choice.transit.vehicle}</p>
                          <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.standard_choice.transit.details}</p>
                        </div>
                        <div className="package-item-co2">{currentPackages.standard_choice.transit.co2_kg} kg</div>
                      </div>
                    </div>

                    <div className="package-footer">
                      <div className="package-price-info">
                        <h5>Estimated Cost</h5>
                        <p>${currentPackages.standard_choice.total_price_usd.toLocaleString()}</p>
                      </div>
                      <button className="package-action-btn secondary" onClick={() => bookTrip('standard')}>
                        Book Standard
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB: TRANSACTIONS & STATEMENT ==================== */}
        {activeTab === 'transactions' && (
          <div className="glass-card">
            <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <History size={20} style={{ color: 'var(--primary)' }} />
              Carbon Ledger Statement
            </h2>

            <div className="transaction-table-wrapper">
              <table className="tx-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Date</th>
                    <th>Description</th>
                    <th>Carbon (kg CO₂)</th>
                    <th>Points Reward</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((tx) => (
                    <tr key={tx.id}>
                      <td>
                        <span className={`tx-type-badge ${tx.type}`}>
                          {tx.type === 'flight' && <Plane size={14} />}
                          {tx.type === 'car' && <Car size={14} />}
                          {tx.type === 'energy' && <Leaf size={14} />}
                          {tx.type === 'offset' && <Award size={14} />}
                        </span>
                      </td>
                      <td>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{tx.date}</span>
                      </td>
                      <td>
                        <span className="tx-description">{tx.description}</span>
                      </td>
                      <td>
                        <span className={`tx-amount ${tx.amount > 0 ? 'positive' : 'negative'}`}>
                          {tx.amount > 0 ? `+${tx.amount.toLocaleString()}` : tx.amount.toLocaleString()}
                        </span>
                      </td>
                      <td>
                        <span className="tx-points">{tx.points_earned > 0 ? `+${tx.points_earned}` : '0'}</span>
                      </td>
                      <td>
                        <span className={`tx-status ${tx.status}`}>
                          {tx.status === 'completed' && <Check size={10} />}
                          {tx.status === 'pending' && <Clock size={10} />}
                          {tx.status === 'cancelled' && <X size={10} />}
                          {tx.status}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {tx.status === 'pending' && (
                          <div className="tx-actions" style={{ justifyContent: 'flex-end' }}>
                            <button className="tx-btn confirm" onClick={() => confirmBooking(tx.id)}>
                              Confirm
                            </button>
                            <button className="tx-btn cancel" onClick={() => cancelBooking(tx.id)}>
                              Cancel
                            </button>
                          </div>
                        )}
                        {tx.status === 'completed' && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Posted</span>
                        )}
                        {tx.status === 'cancelled' && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Voided</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Toast Notification popups */}
      {toastMessage && (
        <div className="toast">
          <Leaf size={16} />
          <span>{toastMessage}</span>
        </div>
      )}
    </div>
  );
}

export default App;
