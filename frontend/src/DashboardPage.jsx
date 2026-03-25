import React, { useState, useEffect } from "react";
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler,
} from "chart.js";
import "chartjs-adapter-date-fns";
import { Line } from "react-chartjs-2";
import { motion } from "framer-motion";

// Register Chart.js components
ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler
);

// --- Icons ---
const Icon = ({ path, className = "w-5 h-5" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path fillRule="evenodd" d={path} clipRule="evenodd" />
  </svg>
);

const LogoIcon = ({ className = "w-10 h-10" }) => (
  <div className={`${className} bg-gradient-to-br from-indigo-500 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/40`}>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-6 h-6">
      <path d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-2.625 6c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975V9.225c0-.54-.435-.975-.975-.975h-5.25zm0 4.5c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975v-.015c0-.54-.435-.975-.975-.975h-5.25z" />
    </svg>
  </div>
);

// --- Helper: Safe Currency Formatter ---
const formatMoney = (val) => {
  if (val === undefined || val === null || isNaN(val)) return "$0.00";
  return "$" + Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

// --- Login Page (High Visibility Dark Mode) ---
// --- Login Page (High Visibility Dark Mode) ---
// Notice the new 'onBack' prop added here:
export const LoginPage = ({ onLogin, onBack }) => {
  const [token, setToken] = useState('');
  const [server, setServer] = useState('Exness-MT5Trial10'); 
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!token) { setError('Please enter your Account ID.'); return; }
    if (!server) { setError('Please enter your Broker Server name.'); return; }
    
    setError(''); setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, server }),
      });
      const data = await response.json();
      if (response.ok) { onLogin(data.user); }
      else { setError(data.message || 'Login failed. Check ID and Server name.'); }
    } catch (err) { setError('Backend connection failed. Is api_server.py running?'); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white flex items-center justify-center p-6 font-sans relative overflow-hidden">
      <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[120px]"></div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md p-8 bg-slate-900 rounded-3xl shadow-2xl border border-slate-700 relative z-10"
      >
        
        {/* --- NEW: ELITE BACK BUTTON --- */}
        {onBack && (
          <button 
            onClick={onBack}
            className="absolute top-5 left-5 p-2.5 rounded-full bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700 hover:border-slate-500 transition-all cursor-pointer group shadow-sm"
            title="Return to Main Site"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5 group-hover:-translate-x-0.5 transition-transform">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
          </button>
        )}
        {/* ------------------------------ */}

        <div className="text-center mb-10">
          <div className="flex justify-center mb-6"><LogoIcon className="w-16 h-16" /></div>
          <h2 className="text-3xl font-bold text-white">Terminal Access</h2>
          <p className="mt-2 text-slate-400 text-sm">Secure MT5 Connection</p>
        </div>

        <div className="space-y-6">
          <div className="space-y-4">
            <div className="relative">
              <input type="number" placeholder="MT5 Account ID" value={token} onChange={(e) => setToken(e.target.value)} 
                className="w-full bg-slate-800 border border-slate-600 rounded-xl px-4 py-3.5 text-white placeholder:text-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all outline-none"
              />
            </div>
            <div className="relative">
              <input type="text" placeholder="Server (e.g., Exness-MT5Trial10)" value={server} onChange={(e) => setServer(e.target.value)}
                className="w-full bg-slate-800 border border-slate-600 rounded-xl px-4 py-3.5 text-white placeholder:text-slate-400 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all outline-none"
              />
            </div>
          </div>
          
          {error && <p className="text-sm text-center text-red-400 bg-red-900/30 py-3 rounded-lg border border-red-500/50 font-medium">{error}</p>}
          
          <button onClick={handleSubmit} disabled={loading} 
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-4 rounded-xl transition-all shadow-lg shadow-indigo-600/30 disabled:opacity-50 flex justify-center items-center"
          >
            {loading ? <span className="animate-spin h-5 w-5 border-2 border-white/40 border-t-white rounded-full mr-2"></span> : null}
            {loading ? 'Authenticating...' : 'Connect to Terminal'}
          </button>
        </div>
      </motion.div>
    </div>
  );
};

// --- Updated Chart (Higher Contrast) ---
const PerformanceChart = ({ chartData = [] }) => {
  const data = {
    labels: chartData.map(d => new Date(d.time)),
    datasets: [{
      label: "Equity",
      data: chartData.map(d => d.balance),
      fill: 'start',
      backgroundColor: (context) => {
        const ctx = context.chart.ctx;
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0.05)');
        return gradient;
      },
      borderColor: "#818cf8",
      borderWidth: 3,
      pointRadius: 0,
      pointHoverRadius: 6,
      tension: 0.4,
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: { 
        type: "time", 
        time: { unit: "day" }, 
        grid: { display: false },
        ticks: { color: "#94a3b8", font: { size: 11, weight: '500' } }
      },
      y: { 
        grid: { color: "rgba(255,255,255,0.08)" },
        ticks: { color: "#94a3b8", font: { size: 11, weight: '500' }, callback: v => `$${v}` }
      }
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: "#1e293b",
        titleColor: "#f8fafc",
        bodyColor: "#818cf8",
        padding: 12,
        borderColor: "#475569",
        borderWidth: 1,
        displayColors: false,
        titleFont: { size: 13, weight: 'bold' },
        bodyFont: { size: 14, weight: 'bold' }
      }
    },
    interaction: { mode: 'index', intersect: false },
  };
  
  return <Line data={data} options={options} />;
};

// --- Data Display Components ---
const StatCard = ({ title, value, subtext, icon, trend }) => (
  <div className="bg-slate-900 border border-slate-700 p-6 rounded-2xl shadow-lg hover:border-indigo-500/50 transition-all group">
    <div className="flex justify-between items-start">
      <div>
        <p className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">{title}</p>
        <h3 className="text-3xl font-bold text-white mb-2">{value}</h3>
        {trend !== undefined && (
          <span className={`text-sm font-bold px-2 py-1 rounded ${trend >= 0 ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400'}`}>
            {trend >= 0 ? '+' : ''}{Number(trend).toFixed(2)}%
          </span>
        )}
        {subtext && <p className="text-sm font-medium text-slate-400 mt-2">{subtext}</p>}
      </div>
      <div className="p-3 bg-slate-800 rounded-xl text-slate-300 group-hover:text-indigo-400 group-hover:bg-indigo-900/30 transition-colors">
        {icon}
      </div>
    </div>
  </div>
);

const LivePositionsTable = ({ trades, isLoading }) => (
  <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900 shadow-lg">
    <table className="w-full text-left text-sm">
      <thead className="bg-slate-800 text-slate-300 font-bold uppercase tracking-wider text-xs border-b border-slate-700">
        <tr>
          <th className="px-6 py-4">Symbol</th>
          <th className="px-6 py-4">Side</th>
          <th className="px-6 py-4">Size</th>
          <th className="px-6 py-4">Entry</th>
          <th className="px-6 py-4">P/L</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-800 text-slate-200">
        {isLoading ? (
          <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400 font-medium animate-pulse">Scanning market data...</td></tr>
        ) : trades.length > 0 ? (
          trades.map((t, i) => (
            <tr key={i} className="hover:bg-slate-800/50 transition-colors">
              <td className="px-6 py-4 font-bold text-white">{t.symbol}</td>
              <td className="px-6 py-4">
                <span className={`px-2.5 py-1 rounded text-xs font-black uppercase ${t.side === 'Buy' ? 'bg-emerald-900/50 text-emerald-400 border border-emerald-500/30' : 'bg-red-900/50 text-red-400 border border-red-500/30'}`}>
                  {t.side}
                </span>
              </td>
              <td className="px-6 py-4 font-mono font-medium text-slate-300">{t.lot}</td>
              <td className="px-6 py-4 font-mono font-medium text-slate-300">{t.entry}</td>
              <td className={`px-6 py-4 font-mono font-bold text-base ${t.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
              </td>
            </tr>
          ))
        ) : (
          <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400 font-medium">No active positions running.</td></tr>
        )}
      </tbody>
    </table>
  </div>
);

const HistoryTable = ({ trades, isLoading }) => (
    <div className="overflow-x-auto rounded-xl border border-slate-700 bg-slate-900 shadow-lg">
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-800 text-slate-300 font-bold uppercase tracking-wider text-xs border-b border-slate-700">
          <tr>
            <th className="px-6 py-4">Symbol</th>
            <th className="px-6 py-4">Type</th>
            <th className="px-6 py-4">Vol</th>
            <th className="px-6 py-4">Time</th>
            <th className="px-6 py-4">Profit</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 text-slate-200">
          {isLoading ? (
             <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400 font-medium">Loading history...</td></tr>
          ) : trades && trades.length > 0 ? (
            trades.map((t, i) => (
              <tr key={i} className="hover:bg-slate-800/50 transition-colors">
                <td className="px-6 py-4 font-bold text-white">{t.symbol}</td>
                <td className="px-6 py-4">
                    <span className={`text-xs font-bold uppercase ${t.type === 'Buy' ? 'text-emerald-400' : 'text-red-400'}`}>{t.type}</span>
                </td>
                <td className="px-6 py-4 font-mono font-medium text-slate-300">{t.volume}</td>
                <td className="px-6 py-4 font-mono text-slate-400 text-xs">{t.close_time}</td>
                <td className={`px-6 py-4 font-mono font-bold text-base ${t.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {t.profit >= 0 ? '+' : ''}{t.profit.toFixed(2)}
                </td>
              </tr>
            ))
          ) : (
            <tr><td colSpan="5" className="px-6 py-8 text-center text-slate-400 font-medium">History is empty.</td></tr>
          )}
        </tbody>
      </table>
    </div>
);


// --- Main Dashboard Layout ---
export const Dashboard = ({ user, onLogout }) => {
  const [botStatus, setBotStatus] = useState('Stopped');
  const [strategy, setStrategy] = useState('trend_follow');
  const [lotSize, setLotSize] = useState(0.01);
  const [maxDailyLoss, setMaxDailyLoss] = useState(200);
  const [maxDrawdown, setMaxDrawdown] = useState(300);
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState('');
  
  const [trades, setTrades] = useState([]);
  const [accountDetails, setAccountDetails] = useState(user || {});
  const [history, setHistory] = useState({ totalProfitLoss: 0, percentageGain: 0, chartData: [], closedTrades: [] });
  const [activeTab, setActiveTab] = useState('live');

  useEffect(() => {
    if (user) setAccountDetails(prev => ({ ...prev, ...user }));

    const fetchData = async () => {
      try {
        const [posRes, accRes] = await Promise.all([
          fetch('http://127.0.0.1:5000/get-positions'),
          fetch('http://127.0.0.1:5000/get-account-info')
        ]);
        
        if (posRes.ok) {
           const data = await posRes.json();
           setTrades(data.trades || []);
        }
        
        if (accRes.ok) {
           const data = await accRes.json();
           setAccountDetails(prev => ({ ...prev, ...(data.info || {}) }));
        }
      } catch (e) { 
        console.error("Poll error (API might be down)", e); 
      }
    };
    
    const fetchHistory = async () => {
      try {
        const res = await fetch('http://127.0.0.1:5000/get-account-history');
        if (res.ok) {
           const data = await res.json();
           setHistory(data.data || { totalProfitLoss: 0, percentageGain: 0, chartData: [], closedTrades: [] });
        }
      } catch (e) { console.error("History error", e); }
    };

    fetchData();
    fetchHistory();
    
    const timer = setInterval(fetchData, 2000); 
    return () => clearInterval(timer);
  }, [user]);

  const handleBotAction = async () => {
    setIsUpdating(true);
    const newStatus = botStatus === 'Running' ? 'Stopped' : 'Running';
    const endpoint = newStatus === 'Running' ? 'start-bot' : 'stop-bot';
    try {
      await fetch(`http://127.0.0.1:5000/${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy, lotSize, maxDailyLoss, maxDrawdown }),
      });
      setBotStatus(newStatus);
      setMessage(newStatus === 'Running' ? 'Engine Initialized.' : 'Engine Halted.');
    } catch { setMessage('Connection Error.'); }
    finally { setIsUpdating(false); setTimeout(() => setMessage(''), 3000); }
  };

  const totalPnL = trades.reduce((acc, t) => acc + (t.pnl || 0), 0);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans selection:bg-indigo-500/50 pb-12">
        
        {/* Navbar */}
        <header className="border-b border-slate-800 bg-slate-950 sticky top-0 z-50 shadow-sm">
           <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
              <div className="flex items-center space-x-4">
                 <LogoIcon className="w-10 h-10" />
                 <span className="text-xl font-black text-white tracking-tight">Nawthviper <span className="text-slate-500 font-medium">/ Terminal</span></span>
              </div>
              <div className="flex items-center space-x-6">
                 <div className="hidden md:flex items-center space-x-2 text-sm font-mono bg-slate-900 px-4 py-2 rounded-xl border border-slate-700 shadow-inner">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></span>
                    <span className="text-emerald-400 font-bold">ID: {accountDetails?.accountId || 'N/A'}</span>
                 </div>
                 <button onClick={onLogout} className="text-sm font-bold text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 px-4 py-2 rounded-lg transition-colors">Log out</button>
              </div>
           </div>
        </header>

        <main className="max-w-7xl mx-auto px-6 py-10">
            {/* Top Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                <StatCard 
                  title="Balance" 
                  value={formatMoney(accountDetails?.balance)}
                  trend={history?.percentageGain}
                  icon={<Icon path="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />}
                />
                <StatCard 
                  title="Equity" 
                  value={formatMoney(accountDetails?.equity)} 
                  icon={<Icon path="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941" />}
                />
                <StatCard 
                  title="Unrealized P/L" 
                  value={<span className={totalPnL >= 0 ? "text-emerald-400" : "text-red-400"}>{totalPnL >= 0 ? '+' : ''}{formatMoney(Math.abs(totalPnL))}</span>}
                  subtext={`${trades.length} active positions`}
                  icon={<Icon path="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" />}
                />
                 <StatCard 
                  title="Net Profit" 
                  value={<span className={(history?.totalProfitLoss || 0) >= 0 ? "text-emerald-400" : "text-red-400"}>{(history?.totalProfitLoss || 0) >= 0 ? '+' : ''}{formatMoney(Math.abs(history?.totalProfitLoss || 0))}</span>}
                  icon={<Icon path="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />}
                />
            </div>

            {/* Main Content Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                
                {/* Left: Engine Controls */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-2xl shadow-lg">
                        <div className="flex items-center justify-between mb-8">
                           <h3 className="font-bold text-xl text-white">Engine Config</h3>
                           <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-black uppercase tracking-wider ${botStatus === 'Running' ? 'bg-emerald-900/60 text-emerald-400 border border-emerald-500/50' : 'bg-red-900/60 text-red-400 border border-red-500/50'}`}>
                              <span className={`w-2 h-2 rounded-full ${botStatus === 'Running' ? 'bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.8)]' : 'bg-red-500'}`}></span>
                              <span>{botStatus}</span>
                           </div>
                        </div>
                        
                        <div className="space-y-6">
                            {/* Row 1: Strategy */}
                            <div>
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Strategy Logic</label>
                                <select value={strategy} onChange={e => setStrategy(e.target.value)} className="w-full bg-slate-800 border border-slate-600 rounded-xl px-4 py-3.5 text-sm font-medium text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all cursor-pointer">
                                    <option value="trend_follow">Trend Follow (H4 Bias)</option>
                                    <option value="aggressive">Aggressive Scalper (M1)</option>
                                </select>
                            </div>

                            {/* Row 2: Lot & Max Loss */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Fixed Lot</label>
                                    <select value={lotSize} onChange={e => setLotSize(parseFloat(e.target.value))} className="w-full bg-slate-800 border border-slate-600 rounded-xl px-4 py-3.5 text-sm font-mono font-bold text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none cursor-pointer">
                                        <option value={0.01}>0.01</option>
                                        <option value={0.05}>0.05</option>
                                        <option value={0.1}>0.10</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Daily Limit</label>
                                    <div className="relative">
                                        <span className="absolute left-4 top-3.5 text-slate-400 font-bold">$</span>
                                        <input type="number" value={maxDailyLoss} onChange={e => setMaxDailyLoss(parseFloat(e.target.value))} className="w-full bg-slate-800 border border-slate-600 rounded-xl pl-8 pr-4 py-3.5 text-sm font-mono font-bold text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all" />
                                    </div>
                                </div>
                            </div>

                            {/* Row 3: Drawdown Limit */}
                            <div>
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 block">Max Drawdown Kill-Switch</label>
                                <div className="relative">
                                    <span className="absolute left-4 top-3.5 text-slate-400 font-bold">$</span>
                                    <input type="number" value={maxDrawdown} onChange={e => setMaxDrawdown(parseFloat(e.target.value))} className="w-full bg-slate-800 border border-slate-600 rounded-xl pl-8 pr-4 py-3.5 text-sm font-mono font-bold text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all" />
                                </div>
                            </div>

                            <button onClick={handleBotAction} disabled={isUpdating} className={`w-full py-4 rounded-xl font-black text-sm uppercase tracking-wider shadow-lg transition-all transform active:scale-[0.98] ${botStatus === 'Running' ? 'bg-red-600 hover:bg-red-500 text-white shadow-red-600/30 border border-red-500' : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-emerald-500/30'}`}>
                                {isUpdating ? 'Processing...' : (botStatus === 'Running' ? 'STOP ENGINE' : 'START ENGINE')}
                            </button>
                            
                            {message && <div className="text-center text-sm font-bold text-slate-300 pt-2">{message}</div>}
                        </div>
                    </div>
                </div>

                {/* Right: Chart & Tables */}
                <div className="lg:col-span-2 space-y-6">
                    {/* Chart Panel */}
                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-2xl shadow-lg h-[360px] relative">
                         <div className="absolute top-8 right-8 z-10">
                            <span className="text-xs font-bold font-mono text-indigo-400 bg-indigo-900/50 px-3 py-1.5 rounded-lg border border-indigo-500/50">LIVE DATA</span>
                         </div>
                         <h3 className="font-bold text-xl text-white mb-6">Equity Curve</h3>
                         <div className="h-[240px]">
                            {history?.chartData?.length > 0 ? <PerformanceChart chartData={history.chartData} /> : <div className="h-full flex items-center justify-center text-slate-500 font-medium text-sm">No historical data available for chart.</div>}
                         </div>
                    </div>

                    {/* Tabs & Table Panel */}
                    <div className="bg-slate-900 border border-slate-700 p-8 rounded-2xl shadow-lg min-h-[300px]">
                        <div className="flex space-x-8 border-b border-slate-800 mb-6">
                            <button onClick={() => setActiveTab('live')} className={`pb-4 text-sm font-bold uppercase tracking-wider transition-colors border-b-2 ${activeTab === 'live' ? 'text-indigo-400 border-indigo-500' : 'text-slate-500 border-transparent hover:text-slate-300'}`}>
                                Active Trades <span className="ml-2 bg-slate-800 text-slate-300 px-2.5 py-0.5 rounded-full text-xs border border-slate-700">{trades.length}</span>
                            </button>
                            <button onClick={() => setActiveTab('history')} className={`pb-4 text-sm font-bold uppercase tracking-wider transition-colors border-b-2 ${activeTab === 'history' ? 'text-indigo-400 border-indigo-500' : 'text-slate-500 border-transparent hover:text-slate-300'}`}>
                                Trade History
                            </button>
                        </div>
                        
                        {activeTab === 'live' ? <LivePositionsTable trades={trades} /> : <HistoryTable trades={history?.closedTrades} />}
                    </div>
                </div>
            </div>
        </main>
    </div>
  );
};