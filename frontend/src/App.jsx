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
  Gauge,
  Download,
  MapPin,
  Compass
} from 'lucide-react';

const API_URL = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [summary, setSummary] = useState({ budget_limit: 5000, current_usage: 1840, points: 650 });
  const [transactions, setTransactions] = useState([]);
  const [trajectory, setTrajectory] = useState([]);
  const [toastMessage, setToastMessage] = useState('');
  const [pointsAnimate, setPointsAnimate] = useState(false);
  
  // Carbon Patterns State
  const [carbonPatterns, setCarbonPatterns] = useState(null);
  const [patternsLoading, setPatternsLoading] = useState(false);
  const [patternsTrace, setPatternsTrace] = useState(null);

  // Agent State
  const [prompt, setPrompt] = useState('i want to travel to hawaii on a 3-day trip, give me carbon-efficient package for flights, car trips, and places for 3 days');
  const [loading, setLoading] = useState(false);
  const [thinkingSteps, setThinkingSteps] = useState([]);
  const [currentPackages, setCurrentPackages] = useState(null);
  const [travelLocation, setTravelLocation] = useState('Hawaii');
  const [searchQuery, setSearchQuery] = useState('Hawaii');
  const [activeSubTab, setActiveSubTab] = useState('maps');
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'agent',
      text: 'Hi! I am your Carbon Eco-Agent. Ask me for sustainable travel options, budget-friendly low-carbon trips, or a report on your spending patterns with Arize observability.',
      timestamp: new Date().toISOString(),
      type: 'text'
    }
  ]);
  const [latestPatternMessage, setLatestPatternMessage] = useState(null);
  
  // Arize Phoenix Observability State
  const [arizeTraces, setArizeTraces] = useState([]);
  const [showArizePanel, setShowArizePanel] = useState(true);
  const [phoenixUrl] = useState('http://localhost:6006');

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (currentPackages && currentPackages.destination) {
      setTravelLocation(currentPackages.destination);
      setSearchQuery(currentPackages.destination);
    }
  }, [currentPackages]);

  const showToast = (message) => {
    setToastMessage(message);
    setTimeout(() => {
      setToastMessage('');
    }, 4000);
  };

  const appendMessage = (message) => {
    setMessages((prev) => [...prev, message]);
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

  const fetchCarbonPatterns = async () => {
    setPatternsLoading(true);
    setPatternsTrace({
      id: 'trace-carbon-patterns',
      name: 'carbon_spending_analysis',
      status: 'active',
      startTime: new Date(),
      duration: null
    });

    const pendingMessage = {
      id: 'pending-pattern',
      sender: 'agent',
      text: 'Analyzing your carbon spending patterns with Arize and creating a quick report...',
      timestamp: new Date().toISOString(),
      type: 'text'
    };

    appendMessage(pendingMessage);
    setLatestPatternMessage(pendingMessage);

    try {
      const res = await fetch(`${API_URL}/api/carbon-patterns`);
      const data = await res.json();
      setCarbonPatterns(data);
      const reportText = `Here's a summary of your carbon spending: ${data.budget_used_percent}% of budget used, ${data.green_vs_standard.green} green choices vs ${data.green_vs_standard.standard} standard choices. Highest emissions come from ${data.high_emission_activities.map((a) => a.description).join(', ')}.`;
      const patternMessage = {
        id: `pattern-${Date.now()}`,
        sender: 'agent',
        text: reportText,
        timestamp: new Date().toISOString(),
        type: 'report',
        details: data
      };
      setMessages((prev) => prev.map((msg) => msg.id === 'pending-pattern' ? patternMessage : msg));
      setLatestPatternMessage(patternMessage);
      setPatternsTrace({
        id: 'trace-carbon-patterns',
        name: 'carbon_spending_analysis',
        status: 'completed',
        startTime: new Date(),
        duration: 800
      });
      showToast('Carbon patterns analyzed! Check Arize Phoenix for detailed observability.');
    } catch (err) {
      console.error('Error fetching carbon patterns:', err);
      setPatternsTrace((prev) => ({
        ...prev,
        status: 'failed',
        duration: 800
      }));
      setMessages((prev) => prev.map((msg) => msg.id === 'pending-pattern' ? {
        ...msg,
        text: 'I could not load the spending report. Please try again.',
        type: 'text'
      } : msg));
      showToast('Error analyzing carbon patterns.');
    } finally {
      setPatternsLoading(false);
    }
  };

  const runAgent = async (e, customPrompt = null, overridePackageContext = null) => {
    if (e) e.preventDefault();
    const promptText = customPrompt || prompt;
    if (!promptText.trim()) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: promptText.trim(),
      timestamp: new Date().toISOString(),
      type: 'text'
    };
    appendMessage(userMessage);

    const pendingAgentMessage = {
      id: 'pending-agent',
      sender: 'agent',
      text: 'Working through your request and preparing a carbon-aware travel report...',
      timestamp: new Date().toISOString(),
      type: 'text'
    };
    appendMessage(pendingAgentMessage);

    setLoading(true);
    if (!customPrompt) {
      setCurrentPackages(null);
    }
    setThinkingSteps([]);
    setArizeTraces([]); // Reset traces

    // Simulated thinking steps to mimic reasoning loop
    const steps = [
      { id: 1, text: 'Understanding your travel intent and destination preference...' },
      { id: 2, text: 'Estimating sustainable flights and lower-carbon routing...' },
      { id: 3, text: 'Checking green hotels, renewable energy stays, and EV transit options...' },
      { id: 4, text: 'Comparing against standard packages for carbon savings and cost...' },
      { id: 5, text: 'Assembling the agent report and OpenTelemetry trace summary...' }
    ];

    // Arize traces simulation - represents OTel spans being sent to Phoenix
    const traces = [
      { id: 'span-1', name: 'agent_reasoning_loop', status: 'pending', startTime: new Date(), duration: null, kind: 'CHAIN', tool: null },
      { id: 'span-2', name: 'flight_lookup_tool', status: 'pending', startTime: null, duration: null, kind: 'TOOL', tool: 'flight_lookup' },
      { id: 'span-3', name: 'stay_lookup_tool', status: 'pending', startTime: null, duration: null, kind: 'TOOL', tool: 'hotel_lookup' },
      { id: 'span-4', name: 'transit_lookup_tool', status: 'pending', startTime: null, duration: null, kind: 'TOOL', tool: 'transit_lookup' },
      { id: 'span-5', name: 'package_generator', status: 'pending', startTime: null, duration: null, kind: 'LLM', tool: 'llm' }
    ];

    // Simulate trace execution
    for (let i = 0; i < steps.length; i++) {
      const currentStep = steps[i];
      setThinkingSteps((prev) => [...prev.map((s) => ({ ...s, active: false })), { ...currentStep, active: true }]);

      if (i === 1) {
        setArizeTraces((prev) => [{ ...traces[1], status: 'active', startTime: new Date() }, ...prev]);
        await new Promise((r) => setTimeout(r, 450));
        setArizeTraces((prev) => prev.map((t) => (t.id === 'span-2' ? { ...t, status: 'completed', duration: 450 } : t)));
      } else if (i === 2) {
        setArizeTraces((prev) => [{ ...traces[2], status: 'active', startTime: new Date() }, ...prev]);
        await new Promise((r) => setTimeout(r, 380));
        setArizeTraces((prev) => prev.map((t) => (t.id === 'span-3' ? { ...t, status: 'completed', duration: 380 } : t)));
      } else if (i === 3) {
        setArizeTraces((prev) => [{ ...traces[3], status: 'active', startTime: new Date() }, ...prev]);
        await new Promise((r) => setTimeout(r, 420));
        setArizeTraces((prev) => prev.map((t) => (t.id === 'span-4' ? { ...t, status: 'completed', duration: 420 } : t)));
      } else if (i === 4) {
        setArizeTraces((prev) => [{ ...traces[4], status: 'active', startTime: new Date() }, ...prev]);
        await new Promise((r) => setTimeout(r, 500));
        setArizeTraces((prev) => prev.map((t) => (t.id === 'span-5' ? { ...t, status: 'completed', duration: 500 } : t)));
      } else {
        await new Promise((r) => setTimeout(r, 700));
      }

      setThinkingSteps((prev) => prev.map((s) => (s.id === currentStep.id ? { ...s, active: false, completed: true } : s)));
    }

    try {
      const contextToUse = overridePackageContext || currentPackages;
      const res = await fetch(`${API_URL}/api/agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: promptText.trim(), history: messages, package_context: contextToUse })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      
      // Validate response structure
      if (!data || typeof data !== 'object' || !('reply' in data)) {
        console.error('Invalid response structure:', data);
        throw new Error('Invalid response structure from agent');
      }

      const replyMessage = {
        id: `agent-${Date.now()}`,
        sender: 'agent',
        text: data.reply || 'I have an answer for you now.',
        timestamp: new Date().toISOString(),
        type: data.package_summary ? 'report' : 'text',
        packageSummary: data.package_summary || undefined
      };

      setMessages((prev) => prev.map((msg) => (msg.id === 'pending-agent' ? replyMessage : msg)));
      if (data.package_summary) {
        setCurrentPackages(data.package_summary);
      }
      if (!customPrompt) {
        setPrompt('');
      }
      setArizeTraces((prev) => prev.map((t) => (t.id === 'span-1' ? { ...t, status: 'completed', duration: 3200 } : t)));
      showToast('Agent responded successfully! Check Arize Phoenix for detailed traces.');
    } catch (err) {
      console.error('Agent error:', err);
      setArizeTraces((prev) => prev.map((t) => (t.id === 'span-1' ? { ...t, status: 'failed', duration: 0 } : t)));
      setMessages((prev) => prev.map((msg) => (msg.id === 'pending-agent' ? {
        ...msg,
        text: `Error communicating with agent: ${err.message}. Please check the browser console and backend logs for details.`,
        type: 'text'
      } : msg)));
      showToast(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };


  const bookTrip = async (packageType) => {
    if (!currentPackages) return;

    let pkg;
    let description;
    let points = 0;
    
    if (packageType === 'green') {
      pkg = currentPackages.green_choice;
      description = "Eco Premium Package";
      points = pkg.points_earned;
    } else if (packageType === 'balanced') {
      pkg = currentPackages.balanced_choice;
      description = "Eco Balanced Package";
      points = pkg.points_earned;
    } else {
      pkg = currentPackages.standard_choice;
      description = "Standard Package";
      points = 0;
    }

    try {
      const res = await fetch(`${API_URL}/api/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          destination: currentPackages.destination,
          days: currentPackages.days,
          package_type: packageType,
          description: description,
          co2_amount: pkg.total_co2,
          price_usd: pkg.total_price_usd,
          points_earned: points
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

  const handleLoadLocation = () => {
    if (searchQuery.trim()) {
      setTravelLocation(searchQuery.trim());
      showToast(`Google Travel loaded for ${searchQuery.trim()}!`);
    }
  };

  const downloadReportPdf = async (packageSummary = null) => {
    try {
      showToast("Generating Carbon Intelligence PDF...");
      const payload = packageSummary ? {
        destination: packageSummary.destination,
        days: packageSummary.days,
        green_flight: packageSummary.green_choice?.flight ? {
          carrier: packageSummary.green_choice.flight.carrier,
          co2_kg: packageSummary.green_choice.flight.co2_kg,
          price_usd: packageSummary.green_choice.flight.price_usd,
          details: packageSummary.green_choice.flight.details,
        } : null,
        green_stay: packageSummary.green_choice?.stay ? {
          hotel: packageSummary.green_choice.stay.hotel,
          co2_kg: packageSummary.green_choice.stay.co2_kg,
          price_usd: packageSummary.green_choice.stay.price_usd,
          details: packageSummary.green_choice.stay.details,
        } : null,
        green_transit: packageSummary.green_choice?.transit ? {
          vehicle: packageSummary.green_choice.transit.vehicle,
          co2_kg: packageSummary.green_choice.transit.co2_kg,
          price_usd: packageSummary.green_choice.transit.price_usd,
          details: packageSummary.green_choice.transit.details,
        } : null,
        std_flight: packageSummary.standard_choice?.flight ? {
          carrier: packageSummary.standard_choice.flight.carrier,
          co2_kg: packageSummary.standard_choice.flight.co2_kg,
          price_usd: packageSummary.standard_choice.flight.price_usd,
          details: packageSummary.standard_choice.flight.details,
        } : null,
        std_stay: packageSummary.standard_choice?.stay ? {
          hotel: packageSummary.standard_choice.stay.hotel,
          co2_kg: packageSummary.standard_choice.stay.co2_kg,
          price_usd: packageSummary.standard_choice.stay.price_usd,
          details: packageSummary.standard_choice.stay.details,
        } : null,
        std_transit: packageSummary.standard_choice?.transit ? {
          vehicle: packageSummary.standard_choice.transit.vehicle,
          co2_kg: packageSummary.standard_choice.transit.co2_kg,
          price_usd: packageSummary.standard_choice.transit.price_usd,
          details: packageSummary.standard_choice.transit.details,
        } : null,
        green_total_co2: packageSummary.green_choice?.total_co2,
        green_total_price: packageSummary.green_choice?.total_price_usd,
        std_total_co2: packageSummary.standard_choice?.total_co2,
        std_total_price: packageSummary.standard_choice?.total_price_usd,
        co2_savings: packageSummary.green_choice?.co2_savings,
        points_earned: packageSummary.green_choice?.points_earned,
        bal_flight: packageSummary.balanced_choice?.flight ? {
          carrier: packageSummary.balanced_choice.flight.carrier,
          co2_kg: packageSummary.balanced_choice.flight.co2_kg,
          price_usd: packageSummary.balanced_choice.flight.price_usd,
          details: packageSummary.balanced_choice.flight.details,
        } : null,
        bal_stay: packageSummary.balanced_choice?.stay ? {
          hotel: packageSummary.balanced_choice.stay.hotel,
          co2_kg: packageSummary.balanced_choice.stay.co2_kg,
          price_usd: packageSummary.balanced_choice.stay.price_usd,
          details: packageSummary.balanced_choice.stay.details,
        } : null,
        bal_transit: packageSummary.balanced_choice?.transit ? {
          vehicle: packageSummary.balanced_choice.transit.vehicle,
          co2_kg: packageSummary.balanced_choice.transit.co2_kg,
          price_usd: packageSummary.balanced_choice.transit.price_usd,
          details: packageSummary.balanced_choice.transit.details,
        } : null,
        bal_total_co2: packageSummary.balanced_choice?.total_co2 ?? null,
        bal_total_price: packageSummary.balanced_choice?.total_price_usd ?? null,
        bal_co2_savings: packageSummary.balanced_choice?.co2_savings ?? null,
        bal_points_earned: packageSummary.balanced_choice?.points_earned ?? null,
      } : {
        destination: null,
        days: null,
        green_flight: null,
        green_stay: null,
        green_transit: null,
        std_flight: null,
        std_stay: null,
        std_transit: null,
        green_total_co2: null,
        green_total_price: null,
        std_total_co2: null,
        std_total_price: null,
        co2_savings: null,
        points_earned: null,
        bal_flight: null,
        bal_stay: null,
        bal_transit: null,
        bal_total_co2: null,
        bal_total_price: null,
        bal_co2_savings: null,
        bal_points_earned: null,
      };

      const res = await fetch(`${API_URL}/api/download-pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to generate PDF");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `GreenRoute_Report_${packageSummary?.destination || 'Summary'}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast("PDF report downloaded successfully!");
    } catch (err) {
      console.error("Error downloading PDF:", err);
      showToast("Error downloading PDF report.");
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
          <span>GreenRoute</span>
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
              <span>Book A Trip</span>
  
            </a>
          </li>
          <li>
            <a 
              className={`nav-item ${activeTab === 'google-travel' ? 'active' : ''}`}
              onClick={() => setActiveTab('google-travel')}
            >
              <Compass className="nav-item-icon" size={18} />
              <span>Google Travel Hub</span>
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
              {activeTab === 'google-travel' && "Google Travel Hub"}
              {activeTab === 'transactions' && "Carbon Account Statement"}
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              {activeTab === 'overview' && "Track your budget, points ledger, and carbon trajectory."}
              {activeTab === 'agent' && "Consult the AI Agent to draft and book carbon-efficient travel itineraries."}
              {activeTab === 'google-travel' && "Explore Google Maps, Flights, Hotels, and Explore embeds."}
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

        {/* ==================== CARBON PATTERNS ANALYSIS ==================== */}
        {activeTab === 'overview' && (
          <div className="glass-card" style={{ marginTop: '2rem', background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08) 0%, rgba(21, 28, 44, 0.6) 100%)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Database size={20} style={{ color: '#a855f7' }} />
                Carbon Spending Patterns (Arize Observability)
              </h2>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {carbonPatterns && (
                  <button 
                    onClick={() => downloadReportPdf(null)}
                    style={{
                      padding: '0.5rem 1rem',
                      background: 'rgba(168, 85, 247, 0.1)',
                      border: '1px solid rgba(168, 85, 247, 0.3)',
                      color: '#a855f7',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: 600,
                      fontSize: '0.85rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.4rem',
                      transition: 'all 0.3s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'rgba(168, 85, 247, 0.2)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'rgba(168, 85, 247, 0.1)';
                    }}
                  >
                    <Download size={14} /> Download PDF
                  </button>
                )}
                <button 
                  onClick={fetchCarbonPatterns}
                  disabled={patternsLoading}
                  style={{
                    padding: '0.5rem 1rem',
                    background: 'rgba(168, 85, 247, 0.3)',
                    border: '1px solid rgba(168, 85, 247, 0.5)',
                    color: '#a855f7',
                    borderRadius: '8px',
                    cursor: patternsLoading ? 'not-allowed' : 'pointer',
                    fontWeight: 600,
                    fontSize: '0.85rem',
                    transition: 'all 0.3s'
                  }}
                >
                  {patternsLoading ? 'Analyzing...' : 'Analyze Patterns'}
                </button>
              </div>
            </div>

            {patternsTrace && (
              <div style={{ marginBottom: '1rem', padding: '0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(168,85,247,0.2)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: patternsTrace.status === 'completed' ? '#10b981' : patternsTrace.status === 'failed' ? '#ef4444' : '#8b5cf6' }}></div>
                  <strong style={{ color: 'var(--text-primary)' }}>{patternsTrace.name}</strong>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>OTel Trace</span>
                  {patternsTrace.status === 'completed' && <span style={{ fontSize: '0.75rem', color: '#10b981', marginLeft: 'auto' }}>✓ {patternsTrace.duration}ms</span>}
                </div>
              </div>
            )}

            {carbonPatterns ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                {/* Budget Utilization */}
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Budget Used</div>
                  <div style={{ fontSize: '1.6rem', fontWeight: 700, color: carbonPatterns.budget_used_percent > 85 ? '#ef4444' : carbonPatterns.budget_used_percent > 65 ? '#f59e0b' : '#10b981' }}>
                    {carbonPatterns.budget_used_percent}%
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                    {carbonPatterns.total_emissions.toLocaleString()} / {carbonPatterns.budget_limit.toLocaleString()} kg
                  </div>
                </div>

                {/* Green vs Standard */}
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Choices</div>
                  <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.9rem' }}>
                    <span style={{ color: '#10b981' }}>🌱 Green: {carbonPatterns.green_vs_standard.green}</span>
                    <span style={{ color: '#ef4444' }}>⚠️ Standard: {carbonPatterns.green_vs_standard.standard}</span>
                  </div>
                </div>

                {/* Trend */}
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Trajectory</div>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: carbonPatterns.trends.trajectory === 'stable' ? '#10b981' : '#f59e0b' }}>
                    {carbonPatterns.trends.trajectory === 'stable' ? '→ Stable' : '↑ Increasing'}
                  </div>
                </div>

                {/* Avg Per Transaction */}
                <div style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600, marginBottom: '0.5rem' }}>Avg Per Activity</div>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)' }}>
                    {carbonPatterns.trends.average_per_transaction.toLocaleString()}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>kg CO₂</div>
                </div>
              </div>
            ) : (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                <p>Click "Analyze Patterns" to see detailed carbon spending insights with Arize observability traces.</p>
              </div>
            )}

            {carbonPatterns && carbonPatterns.high_emission_activities.length > 0 && (
              <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.75rem', color: 'var(--text-primary)' }}>
                  🔴 Highest Emission Activities
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {carbonPatterns.high_emission_activities.map((activity, idx) => (
                    <div key={idx} style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '6px', fontSize: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>{activity.description}</span>
                        <span style={{ fontWeight: 700, color: '#ef4444' }}>{activity.amount.toLocaleString()} kg</span>
                      </div>
                      <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                        {activity.date} • {activity.status}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB: AI BOOKING AGENT ==================== */}
        {/* ==================== TAB: AI BOOKING AGENT ==================== */}
        {activeTab === 'agent' && (
          <div className="agent-container">
            {/* Synthesized packages results */}
            {currentPackages && currentPackages.green_choice && currentPackages.standard_choice && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', marginBottom: '2rem' }}>
                {/* Comparison Title Card */}
                <div className="glass-card" style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(21, 28, 44, 0.6) 100%)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '250px' }}>
                    <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)' }}>
                      Travel Packages for {currentPackages.destination} ({currentPackages.days} Days)
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>
                      Choosing Eco Premium saves <strong>{currentPackages.green_choice.co2_savings} kg CO₂</strong>, while Balanced saves <strong>{currentPackages.balanced_choice ? currentPackages.balanced_choice.co2_savings : 0} kg CO₂</strong>.
                    </p>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                    <button
                      onClick={() => downloadReportPdf(currentPackages)}
                      className="package-action-btn primary"
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        padding: '0.6rem 1.2rem',
                        borderRadius: '8px',
                        background: 'var(--primary)',
                        color: 'var(--bg)',
                        border: 'none',
                        fontWeight: 600,
                        cursor: 'pointer',
                        boxShadow: '0 4px 12px var(--primary-light)',
                        transition: 'transform 0.2s, box-shadow 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.boxShadow = '0 6px 16px var(--primary-light)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.transform = 'translateY(0)';
                        e.currentTarget.style.boxShadow = '0 4px 12px var(--primary-light)';
                      }}
                    >
                      <Download size={16} />
                      Download PDF Report
                    </button>
                    
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>Points Reward</div>
                      <div style={{ color: 'var(--accent)', fontFamily: 'var(--font-heading)', fontSize: '1.8rem', fontWeight: 800 }}>+{currentPackages.green_choice.points_earned} PTS</div>
                    </div>
                  </div>
                </div>

                {/* Side by side cards */}
                <div className="packages-wrapper">
                  {/* Eco-Green Package */}
                  <div className="glass-card package-card recommended">
                    <span className="badge-recommended">Eco Premium</span>
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
                        Book Eco Premium
                      </button>
                    </div>
                  </div>

                  {/* Eco-Balanced Package */}
                  {currentPackages.balanced_choice && (
                    <div className="glass-card package-card balanced">
                      <span className="badge-balanced">Eco Balanced</span>
                      <div className="package-header">
                        <h3 className="package-title">Eco Balanced Itinerary</h3>
                        <span className="package-co2-badge balanced">
                          <Compass size={14} />
                          {currentPackages.balanced_choice.total_co2} kg CO₂ Total
                        </span>
                      </div>

                      <div className="package-body">
                        <div className="package-item balanced">
                          <div className="package-item-icon">
                            <Plane size={18} />
                          </div>
                          <div className="package-item-details">
                            <h4>Flight Option</h4>
                            <p>{currentPackages.balanced_choice.flight.carrier}</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.balanced_choice.flight.details}</p>
                          </div>
                          <div className="package-item-co2">{currentPackages.balanced_choice.flight.co2_kg} kg</div>
                        </div>

                        <div className="package-item balanced">
                          <div className="package-item-icon">
                            <Hotel size={18} />
                          </div>
                          <div className="package-item-details">
                            <h4>Accommodation</h4>
                            <p>{currentPackages.balanced_choice.stay.hotel}</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.balanced_choice.stay.details}</p>
                          </div>
                          <div className="package-item-co2">{currentPackages.balanced_choice.stay.co2_kg} kg</div>
                        </div>

                        <div className="package-item balanced">
                          <div className="package-item-icon">
                            <Car size={18} />
                          </div>
                          <div className="package-item-details">
                            <h4>Local Transit</h4>
                            <p>{currentPackages.balanced_choice.transit.vehicle}</p>
                            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentPackages.balanced_choice.transit.details}</p>
                          </div>
                          <div className="package-item-co2">{currentPackages.balanced_choice.transit.co2_kg} kg</div>
                        </div>

                        <div className="package-summary balanced">
                          <strong>AI Summary justification:</strong> {currentPackages.balanced_choice.summary}
                        </div>
                      </div>

                      <div className="package-footer">
                        <div className="package-price-info">
                          <h5>Estimated Cost</h5>
                          <p>${currentPackages.balanced_choice.total_price_usd.toLocaleString()}</p>
                        </div>
                        <button className="package-action-btn balanced" onClick={() => bookTrip('balanced')}>
                          Book Eco Balanced
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Standard Package */}
                  <div className="glass-card package-card standard-card">
                    <span className="badge-standard">Standard Baseline</span>
                    <div className="package-header">
                      <h3 className="package-title">Standard Baseline Itinerary</h3>
                      <span className="package-co2-badge standard">
                        <AlertCircle size={14} />
                        {currentPackages.standard_choice.total_co2} kg CO₂ Total
                      </span>
                    </div>

                    <div className="package-body">
                      <div className="package-item standard">
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

                      <div className="package-item standard">
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

                      <div className="package-item standard">
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
                      <button className="package-action-btn standard-btn" onClick={() => bookTrip('standard')}>
                        Book Standard Baseline
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}
            
            <div className="glass-card">
              <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={20} style={{ color: 'var(--primary)' }} />
                Chat with the Eco-Agent
              </h2>

              <div className="agent-chat-window">
                {messages.map((message) => (
                  <div key={message.id} className={`chat-message ${message.sender}`}>
                    <div className={`chat-avatar ${message.sender}`}>
                      {message.sender === 'agent' ? 'A' : 'Y'}
                    </div>
                    <div className={`chat-bubble ${message.sender}`}>
                      <div className="chat-bubble-top">
                        <strong>{message.sender === 'agent' ? 'Eco-Agent' : 'You'}</strong>
                        <span>{new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <div className="chat-bubble-text">{message.text}</div>
                      {message.type === 'report' && message.details && (
                        <div className="chat-report-summary">
                          <div><strong>Budget Used:</strong> {message.details.budget_used_percent}%</div>
                          <div><strong>Green vs Standard:</strong> {message.details.green_vs_standard.green} / {message.details.green_vs_standard.standard}</div>
                          <div><strong>Top activity:</strong> {message.details.high_emission_activities[0]?.description || 'N/A'}</div>
                        </div>
                      )}
                      {message.packageSummary && (
                        <div className="chat-package-summary" style={{
                          marginTop: '0.75rem',
                          padding: '0.75rem',
                          borderRadius: '6px',
                          background: 'rgba(16, 185, 129, 0.1)',
                          border: '1px solid rgba(16, 185, 129, 0.2)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '0.5rem'
                        }}>
                          <div style={{ fontWeight: 600, color: 'var(--primary)' }}>
                            ✈️ Trip to {message.packageSummary?.destination} ({message.packageSummary?.days} Days)
                          </div>
                          <div style={{ fontSize: '0.85rem' }}>
                            Green package saves <strong>{message.packageSummary?.green_choice?.co2_savings} kg CO₂</strong> and earns <strong>+{message.packageSummary?.green_choice?.points_earned} PTS</strong>.
                          </div>
                          
                          <div style={{ 
                            display: 'grid', 
                            gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', 
                            gap: '0.5rem', 
                            marginTop: '0.5rem',
                            marginBottom: '0.5rem'
                          }}>
                            {/* Eco Premium */}
                            {message.packageSummary?.green_choice && (
                              <div style={{ 
                                padding: '0.5rem', 
                                background: 'rgba(16, 185, 129, 0.15)', 
                                borderRadius: '4px',
                                border: '1px solid rgba(16, 185, 129, 0.3)'
                              }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#10b981' }}>🟢 Eco Premium</div>
                                <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                                  <strong>{message.packageSummary.green_choice.total_co2} kg</strong> CO₂
                                </div>
                                <div style={{ fontSize: '0.8rem' }}>
                                  <strong>${message.packageSummary.green_choice.total_price_usd}</strong>
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--accent)', fontWeight: 600 }}>
                                  +{message.packageSummary.green_choice.points_earned} PTS
                                </div>
                              </div>
                            )}

                            {/* Eco Balanced */}
                            {message.packageSummary?.balanced_choice && (
                              <div style={{ 
                                padding: '0.5rem', 
                                background: 'rgba(245, 158, 11, 0.1)', 
                                borderRadius: '4px',
                                border: '1px solid rgba(245, 158, 11, 0.2)'
                              }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#f59e0b' }}>💛 Eco Balanced</div>
                                <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                                  <strong>{message.packageSummary.balanced_choice.total_co2} kg</strong> CO₂
                                </div>
                                <div style={{ fontSize: '0.8rem' }}>
                                  <strong>${message.packageSummary.balanced_choice.total_price_usd}</strong>
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--accent)', fontWeight: 600 }}>
                                  +{message.packageSummary.balanced_choice.points_earned} PTS
                                </div>
                              </div>
                            )}

                            {/* Standard Baseline */}
                            {message.packageSummary?.standard_choice && (
                              <div style={{ 
                                padding: '0.5rem', 
                                background: 'rgba(239, 68, 68, 0.05)', 
                                borderRadius: '4px',
                                border: '1px solid rgba(239, 68, 68, 0.2)'
                              }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#ef4444' }}>🔴 Standard Baseline</div>
                                <div style={{ fontSize: '0.8rem', marginTop: '0.2rem' }}>
                                  <strong>{message.packageSummary.standard_choice.total_co2} kg</strong> CO₂
                                </div>
                                <div style={{ fontSize: '0.8rem' }}>
                                  <strong>${message.packageSummary.standard_choice.total_price_usd}</strong>
                                </div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                  0 PTS
                                </div>
                              </div>
                            )}
                          </div>
                          
                          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                            <button
                              type="button"
                              onClick={() => {
                                setCurrentPackages(message.packageSummary);
                                runAgent(null, "Compare the travel options in detail, including cost breakdown, carbon emissions, and calculations.", message.packageSummary);
                              }}
                              className="package-action-btn secondary"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.4rem 0.8rem',
                                fontSize: '0.8rem',
                                borderRadius: '4px',
                                border: '1px solid var(--border)',
                                background: 'rgba(255, 255, 255, 0.05)',
                                color: 'var(--text)',
                                fontWeight: 500,
                                cursor: 'pointer'
                              }}
                            >
                              Compare Options
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                downloadReportPdf(message.packageSummary);
                              }}
                              className="package-action-btn primary"
                              style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '0.4rem',
                                padding: '0.4rem 0.8rem',
                                fontSize: '0.8rem',
                                borderRadius: '4px',
                                background: 'rgba(16, 185, 129, 0.2)',
                                border: '1px solid rgba(16, 185, 129, 0.4)',
                                color: 'var(--primary)',
                                fontWeight: 600,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.background = 'rgba(16, 185, 129, 0.3)';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.background = 'rgba(16, 185, 129, 0.2)';
                              }}
                            >
                              <Download size={14} /> Download PDF
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <form onSubmit={runAgent}>
                <div className="agent-prompt-wrapper">
                  <input
                    type="text"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="Ask your carbon agent for a trip, budget report, or green pattern summary..."
                    className="agent-input"
                    disabled={loading}
                  />
                  <button type="submit" className="agent-btn" disabled={loading}>
                    <ArrowRight size={20} />
                  </button>
                </div>
              </form>

              <div className="agent-actions-row">
                <button className="agent-secondary-btn" onClick={fetchCarbonPatterns} disabled={patternsLoading || loading}>
                  {patternsLoading ? 'Generating pattern report...' : 'Analyze Spending Patterns'}
                </button>
                <button className="agent-secondary-btn" onClick={() => setPrompt('Show me a low-emission 4-day trip to Lisbon with sustainable lodging and EV transport')} disabled={loading}>
                  Example Prompt
                </button>
              </div>

              <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.75rem' }}>
                Tip: Ask follow-up questions right here to refine your eco-travel package or request a pattern report backed by Arize telemetry.
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

            {/* Arize Phoenix Real-Time Traces Observer */}
            {(loading || arizeTraces.length > 0) && (
              <div className="glass-card" style={{ background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(21, 28, 44, 0.6) 100%)', marginBottom: '2rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                  <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#8b5cf6', display: 'inline-block', boxShadow: '0 0 8px #8b5cf6' }}></span>
                    Arize Phoenix Observability - Live Agent Traces
                  </h3>
                  <a 
                    href={phoenixUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    style={{ 
                      display: 'inline-flex', 
                      alignItems: 'center', 
                      gap: '0.5rem', 
                      padding: '0.4rem 0.8rem',
                      background: 'rgba(139, 92, 246, 0.2)',
                      color: '#8b5cf6',
                      border: '1px solid rgba(139, 92, 246, 0.3)',
                      borderRadius: '8px',
                      textDecoration: 'none',
                      fontSize: '0.8rem',
                      fontWeight: 600,
                      cursor: 'pointer'
                    }}
                  >
                    <ExternalLink size={12} />
                    Open Phoenix Dashboard
                  </a>
                </div>
                
                {/* Traces List */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {arizeTraces.map((trace) => (
                    <div 
                      key={trace.id} 
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '0.75rem',
                        background: 'rgba(255,255,255,0.03)',
                        border: `1px solid rgba(${trace.status === 'completed' ? '16,185,129' : trace.status === 'failed' ? '239,68,68' : '139,92,246'}, 0.3)`,
                        borderRadius: '8px',
                        fontSize: '0.85rem'
                      }}
                    >
                      {/* Trace Status Icon */}
                      <div style={{
                        width: '24px',
                        height: '24px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderRadius: '50%',
                        background: trace.status === 'completed' ? 'rgba(16,185,129,0.2)' : trace.status === 'failed' ? 'rgba(239,68,68,0.2)' : 'rgba(139,92,246,0.2)',
                        color: trace.status === 'completed' ? '#10b981' : trace.status === 'failed' ? '#ef4444' : '#8b5cf6'
                      }}>
                        {trace.status === 'active' && <div className="spinner" style={{width: '8px', height: '8px'}}></div>}
                        {trace.status === 'completed' && <Check size={14} />}
                        {trace.status === 'failed' && <X size={14} />}
                        {trace.status === 'pending' && <Clock size={14} />}
                      </div>

                      {/* Trace Info */}
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                          <strong style={{ color: 'var(--text-primary)' }}>{trace.name}</strong>
                          <span style={{ 
                            padding: '0.2rem 0.5rem', 
                            background: trace.kind === 'TOOL' ? 'rgba(245,158,11,0.2)' : trace.kind === 'LLM' ? 'rgba(59,130,246,0.2)' : 'rgba(168,85,247,0.2)',
                            color: trace.kind === 'TOOL' ? '#f59e0b' : trace.kind === 'LLM' ? '#3b82f6' : '#a855f7',
                            borderRadius: '4px',
                            fontSize: '0.7rem',
                            fontWeight: 600
                          }}>
                            {trace.kind}
                          </span>
                          {trace.tool && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>→ {trace.tool}</span>}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {trace.status === 'active' && 'Running...'}
                          {trace.status === 'completed' && `Completed in ${trace.duration}ms`}
                          {trace.status === 'failed' && 'Failed'}
                          {trace.status === 'pending' && 'Waiting'}
                        </div>
                      </div>

                      {/* Duration Badge */}
                      {trace.duration && (
                        <div style={{
                          padding: '0.4rem 0.6rem',
                          background: 'rgba(255,255,255,0.05)',
                          borderRadius: '6px',
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: 'var(--text-secondary)',
                          minWidth: '60px',
                          textAlign: 'right'
                        }}>
                          {trace.duration}ms
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
                  💡 <strong>Observability Tip:</strong> Each trace above represents an OpenTelemetry span being recorded in real-time. Visit the <strong>Arize Phoenix dashboard</strong> to see full trace details, span attributes, and latency breakdowns for this agent execution.
                </div>
              </div>
            )}


          </div>
        )}

        {/* ==================== TAB: GOOGLE TRAVEL PLANNER ==================== */}
        {activeTab === 'google-travel' && (
          <div className="glass-card" style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Header / Search bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1.5rem', borderBottom: '1px solid var(--card-border)', paddingBottom: '1.5rem' }}>
              <div>
                <h2 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.4rem', fontWeight: 700, color: 'var(--primary)', margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Compass size={24} style={{ color: 'var(--primary)' }} />
                  Google Travel Integration Hub
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                  Explore live flights, hotels, routes, and things to do for your destination.
                </p>
              </div>
              
              {/* Destination Search Box */}
              <div style={{ display: 'flex', gap: '0.5rem', minWidth: '280px' }}>
                <input
                  type="text"
                  placeholder="Enter destination (e.g. Paris, Tokyo)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleLoadLocation();
                    }
                  }}
                  style={{
                    flex: 1,
                    padding: '0.6rem 1rem',
                    background: 'rgba(255, 255, 255, 0.03)',
                    border: '1px solid var(--card-border)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                    fontSize: '0.9rem',
                    outline: 'none'
                  }}
                />
                <button
                  className="package-action-btn primary"
                  style={{ padding: '0.6rem 1.25rem', whiteSpace: 'nowrap', fontSize: '0.85rem' }}
                  onClick={handleLoadLocation}
                >
                  Load Location
                </button>
              </div>
            </div>

            {/* Embedded Services Sub-Tabs */}
            <div style={{ display: 'flex', gap: '0.5rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
              <button
                className={`package-action-btn ${activeSubTab === 'maps' ? 'primary' : 'secondary'}`}
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1.25rem' }}
                onClick={() => setActiveSubTab('maps')}
              >
                <MapPin size={16} />
                Google Maps
              </button>
              <button
                className={`package-action-btn ${activeSubTab === 'flights' ? 'primary' : 'secondary'}`}
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1.25rem' }}
                onClick={() => setActiveSubTab('flights')}
              >
                <Plane size={16} />
                Google Flights
              </button>
              <button
                className={`package-action-btn ${activeSubTab === 'hotels' ? 'primary' : 'secondary'}`}
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1.25rem' }}
                onClick={() => setActiveSubTab('hotels')}
              >
                <Hotel size={16} />
                Google Hotels
              </button>
              <button
                className={`package-action-btn ${activeSubTab === 'explore' ? 'primary' : 'secondary'}`}
                style={{ fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1.25rem' }}
                onClick={() => setActiveSubTab('explore')}
              >
                <Compass size={16} />
                Google Travel Explore
              </button>
            </div>

            {/* Embed Header / Link Card */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.02)', padding: '1rem 1.5rem', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
              <div>
                <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontFamily: 'var(--font-heading)', fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
                  {activeSubTab === 'maps' && <><MapPin size={18} color="var(--primary)" /> Google Maps Embed</>}
                  {activeSubTab === 'flights' && <><Plane size={18} color="var(--secondary)" /> Google Flights Embed</>}
                  {activeSubTab === 'hotels' && <><Hotel size={18} color="var(--accent)" /> Google Hotels Embed</>}
                  {activeSubTab === 'explore' && <><Compass size={18} color="#a855f7" /> Google Travel Explore Embed</>}
                </h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                  {activeSubTab === 'maps' && `Interactive map, routes, and points of interest for ${travelLocation}.`}
                  {activeSubTab === 'flights' && `Real-time search results for flights to ${travelLocation}.`}
                  {activeSubTab === 'hotels' && `Stays, resorts, and vacation rentals in ${travelLocation}.`}
                  {activeSubTab === 'explore' && `Popular travel guides, itineraries, and things to do in ${travelLocation}.`}
                </p>
              </div>
              <a
                href={
                  activeSubTab === 'maps' ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(travelLocation)}` :
                  activeSubTab === 'flights' ? `https://www.google.com/travel/flights?q=Flights+to+${encodeURIComponent(travelLocation)}` :
                  activeSubTab === 'hotels' ? `https://www.google.com/travel/hotels?q=Hotels+in+${encodeURIComponent(travelLocation)}` :
                  `https://www.google.com/travel/explore?q=${encodeURIComponent(travelLocation)}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="package-action-btn secondary"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '0.4rem', textDecoration: 'none', padding: '0.5rem 1rem', fontSize: '0.8rem' }}
              >
                <ExternalLink size={14} />
                Open full page
              </a>
            </div>

            {/* Embedded Viewer & Carbon-Efficiency Guides */}
            <div style={{ width: '100%', height: '600px', borderRadius: '12px', overflow: 'hidden', border: '1px solid var(--card-border)', background: '#111827' }}>
              {activeSubTab === 'maps' && (
                <iframe
                  width="100%"
                  height="100%"
                  style={{ border: 0, background: '#111827' }}
                  loading="lazy"
                  allowFullScreen
                  src={`https://maps.google.com/maps?q=${encodeURIComponent(travelLocation)}&t=&z=12&ie=UTF8&iwloc=&output=embed`}
                ></iframe>
              )}
              {activeSubTab === 'flights' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem', height: '100%', overflowY: 'auto', background: '#0f172a' }}>
                  <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--secondary)', fontWeight: 700, fontSize: '1.2rem', marginBottom: '0.25rem' }}>
                      <Plane size={22} />
                      Google Flights — Find Carbon-Efficient Flights
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Google Flights calculates and displays CO₂ emission estimates next to all flight results. It factors in aircraft model, cabin class, seating configuration, and route efficiency.
                    </p>
                  </div>
                  
                  {/* How-to Card */}
                  <div style={{ background: 'rgba(59,130,246,0.05)', border: '1px solid rgba(59,130,246,0.15)', borderRadius: '12px', padding: '1.25rem' }}>
                    <h5 style={{ color: 'var(--secondary)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>🌱 Choosing Low-Carbon Flights on Google Travel:</h5>
                    <ul style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', paddingLeft: '1.2rem', lineHeight: '1.5' }}>
                      <li><strong>Look for the Green Leaf Badge:</strong> Google highlights flights that emit less carbon than the median for your route.</li>
                      <li><strong>Sort by Emissions:</strong> Use the "Sort by" dropdown and choose "Emissions" to see the greenest options first.</li>
                      <li><strong>Examine Aircraft Efficiency:</strong> Modern twin-engine planes (like the Airbus A320neo, A350, or Boeing 787 Dreamliner) produce significantly lower per-passenger emissions.</li>
                    </ul>
                  </div>

                  {/* Interactive Flight Simulation Panel */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Mock Route Emissions for {travelLocation}</div>
                    
                    {/* Flight 1: Eco Option */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(16,185,129,0.03)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: '8px' }}>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>Direct Flight (Eco Option)</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.1rem' }}>Modern High-Efficiency Aircraft • Nonstop</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                          <Leaf size={10} />
                          -24% Emissions
                        </span>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', fontWeight: 600 }}>~320 kg CO₂</div>
                      </div>
                    </div>

                    {/* Flight 2: Standard */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid var(--card-border)', borderRadius: '8px' }}>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Standard Option</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.1rem' }}>Average Single-Aisle Jet • 1 Stop</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ display: 'inline-flex', background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600 }}>
                          Average Emissions
                        </span>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>~420 kg CO₂</div>
                      </div>
                    </div>
                  </div>

                  {/* Call to Action Button */}
                  <div style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                    <a
                      href={`https://www.google.com/travel/flights?q=Flights+to+${encodeURIComponent(travelLocation)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="package-action-btn primary"
                      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', textDecoration: 'none', padding: '0.8rem 1.5rem', width: '100%', textAlign: 'center', fontWeight: 700, fontSize: '0.9rem', borderRadius: '8px', boxShadow: '0 4px 12px var(--primary-light)' }}
                    >
                      <Plane size={18} />
                      Open Google Flights to Find Eco-Friendly Options
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              )}
              {activeSubTab === 'hotels' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem', height: '100%', overflowY: 'auto', background: '#0f172a' }}>
                  <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--accent)', fontWeight: 700, fontSize: '1.2rem', marginBottom: '0.25rem' }}>
                      <Hotel size={22} />
                      Google Hotels — Find Eco-Certified Stays
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Google Hotels highlights properties that have been certified by recognized independent sustainability organizations for waste reduction, water conservation, and energy efficiency.
                    </p>
                  </div>

                  {/* How-to Card */}
                  <div style={{ background: 'rgba(251,191,36,0.05)', border: '1px solid rgba(251,191,36,0.15)', borderRadius: '12px', padding: '1.25rem' }}>
                    <h5 style={{ color: 'var(--accent)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>🌱 Finding Sustainable Lodging on Google Travel:</h5>
                    <ul style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', paddingLeft: '1.2rem', lineHeight: '1.5' }}>
                      <li><strong>Look for the 'Eco-certified' Tag:</strong> Certified properties will display an 'Eco-certified' label with a leaf icon in their overview card.</li>
                      <li><strong>Review Sustainability Practices:</strong> Click on the hotel's 'About' section in Google Hotels to view their specific environmental audits (e.g. Green Key, EarthCheck, LEED).</li>
                    </ul>
                  </div>

                  {/* Interactive Hotels Simulation Panel */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>Eco-Stays in {travelLocation}</div>
                    
                    {/* Hotel 1: Eco */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', background: 'rgba(16,185,129,0.03)', border: '1px solid rgba(16,185,129,0.15)', borderRadius: '8px' }}>
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700 }}>Green Oasis Lodge</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.1rem' }}>Solar Powered • Single-Use Plastic Free</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.25rem', background: 'rgba(16,185,129,0.15)', color: '#10b981', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 700 }}>
                          🌱 Eco-Certified
                        </span>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', fontWeight: 600 }}>Water Saving • LEED Gold</div>
                      </div>
                    </div>
                  </div>

                  {/* Call to Action Button */}
                  <div style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                    <a
                      href={`https://www.google.com/travel/hotels?q=Hotels+in+${encodeURIComponent(travelLocation)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="package-action-btn primary"
                      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', textDecoration: 'none', padding: '0.8rem 1.5rem', width: '100%', textAlign: 'center', fontWeight: 700, fontSize: '0.9rem', borderRadius: '8px', boxShadow: '0 4px 12px var(--primary-light)' }}
                    >
                      <Hotel size={18} />
                      Find Eco-Certified Hotels on Google Travel
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              )}
              {activeSubTab === 'explore' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', padding: '2rem', height: '100%', overflowY: 'auto', background: '#0f172a' }}>
                  <div style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: '1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#a855f7', fontWeight: 700, fontSize: '1.2rem', marginBottom: '0.25rem' }}>
                      <Compass size={22} />
                      Google Travel Explore — Plan Local Excursions
                    </div>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                      Discover local spots, walking tours, cycling routes, and public transit maps for your destination. Researching in advance helps you coordinate low-carbon transportation and support eco-tourism.
                    </p>
                  </div>

                  {/* How-to Card */}
                  <div style={{ background: 'rgba(168,85,247,0.05)', border: '1px solid rgba(168,85,247,0.15)', borderRadius: '12px', padding: '1.25rem' }}>
                    <h5 style={{ color: '#a855f7', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>🚲 Sustainable Exploration Tips:</h5>
                    <ul style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', paddingLeft: '1.2rem', lineHeight: '1.5' }}>
                      <li><strong>Opt for Walking and Biking:</strong> Google Travel Explore lists walkable historic districts and parks. Use transit options to bypass car rentals.</li>
                      <li><strong>Support Eco-Tourism:</strong> Visit local nature reserves and check out community-led tours that prioritize conservation.</li>
                    </ul>
                  </div>

                  {/* Call to Action Button */}
                  <div style={{ marginTop: 'auto', paddingTop: '1rem' }}>
                    <a
                      href={`https://www.google.com/travel/explore?q=${encodeURIComponent(travelLocation)}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="package-action-btn primary"
                      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', textDecoration: 'none', padding: '0.8rem 1.5rem', width: '100%', textAlign: 'center', fontWeight: 700, fontSize: '0.9rem', borderRadius: '8px', boxShadow: '0 4px 12px var(--primary-light)' }}
                    >
                      <Compass size={18} />
                      Launch Google Travel Explore for {travelLocation}
                      <ExternalLink size={14} />
                    </a>
                  </div>
                </div>
              )}
            </div>
            
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '8px' }}>
              <span>📍 Current active location: <strong>{travelLocation}</strong></span>
              <span>💡 Tip: Plan a trip in the <strong>AI Eco-Agent</strong> tab to automatically synchronize the location here.</span>
            </div>
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
