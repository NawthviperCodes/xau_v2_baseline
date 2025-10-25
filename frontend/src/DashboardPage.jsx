import React, { useState, useEffect, useRef } from "react";
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler,
} from "chart.js";
import "chartjs-adapter-date-fns";
import { Line } from "react-chartjs-2";

// Register all necessary components for the chart, including 'Filler' for the gradient
ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, TimeScale, Filler
);

// --- SVG Icon Components (No changes here) ---
const Icon = ({ path, className = "w-6 h-6" }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path fillRule="evenodd" d={path} clipRule="evenodd" />
  </svg>
);

const LogoIcon = ({ className = "w-10 h-10" }) => (
  <div className={`${className} bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center`}>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-6 h-6">
      <path d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-2.625 6c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975V9.225c0-.54-.435-.975-.975-.975h-5.25zm0 4.5c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975v-.015c0-.54-.435-.975-.975-.975h-5.25z" />
    </svg>
  </div>
);

const KeyIcon = () => <Icon path="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />;
const ServerIcon = () => <Icon path="M5.25 3A2.25 2.25 0 003 5.25v2.5A2.25 2.25 0 005.25 10h13.5A2.25 2.25 0 0021 7.75v-2.5A2.25 2.25 0 0018.75 3H5.25zm0 11A2.25 2.25 0 003 16.25v2.5A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75v-2.5A2.25 2.25 0 0018.75 14H5.25z" />;

// --- Login Page Component (No changes here) ---
export const LoginPage = ({ onLogin }) => {
  const [token, setToken] = useState('');
  const [server, setServer] = useState('Deriv-Server');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!token) { setError('Please enter your Deriv Account ID.'); return; }
    setError(''); setLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, server }),
      });
      const data = await response.json();
      if (response.ok) { onLogin(data.user); }
      else { setError(data.message || 'Login failed.'); }
    } catch (err) { setError('Cannot connect to the backend server. Is it running?'); }
    finally { setLoading(false); }
  };

  const handleKeyPress = (e) => { if (e.key === 'Enter') handleSubmit(); };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white flex items-center justify-center p-4 font-sans">
      <div className="w-full max-w-md p-8 space-y-8 bg-slate-800/50 backdrop-blur-xl rounded-2xl shadow-2xl border border-slate-700/50">
        <div className="text-center">
          <div className="flex justify-center mb-4"><LogoIcon className="w-16 h-16" /></div>
          <h2 className="text-3xl font-bold tracking-tight">Access Your Dashboard</h2>
          <p className="mt-2 text-slate-400">Enter your MT5 credentials to continue</p>
        </div>
        <div className="mt-8 space-y-6">
          <div className="space-y-4">
            <div className="relative"><div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3"><KeyIcon className="h-5 w-5 text-slate-500" /></div><input id="api-token" name="token" type="password" className="block w-full rounded-lg border-0 bg-slate-700/50 py-3 pl-10 text-white shadow-sm ring-1 ring-inset ring-slate-600/50 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm transition-all" placeholder="Deriv Account ID / Token" value={token} onChange={(e) => setToken(e.target.value)} onKeyPress={handleKeyPress} /></div>
            <div className="relative"><div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3"><ServerIcon className="h-5 w-5 text-slate-500" /></div><select id="server" name="server" value={server} onChange={(e) => setServer(e.target.value)} className="block w-full appearance-none rounded-lg border-0 bg-slate-700/50 py-3 pl-10 text-white shadow-sm ring-1 ring-inset ring-slate-600/50 focus:ring-2 focus:ring-inset focus:ring-indigo-500 sm:text-sm transition-all"><option>Deriv-Server</option><option>Deriv-Demo</option></select></div>
          </div>
          {error && <p className="mt-2 text-sm text-center text-red-400">{error}</p>}
          <div><button onClick={handleSubmit} disabled={loading} className="group relative flex w-full justify-center rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 py-3 px-4 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:opacity-50 transition-all duration-300 shadow-lg shadow-indigo-500/25">{loading ? 'Connecting...' : 'Secure Login'}</button></div>
        </div>
      </div>
    </div>
  );
};

// --- ✅ UPDATED Performance Chart Component ---
const PerformanceChart = ({ chartData = [] }) => {
  const chartRef = useRef(null);

  // Function to create the beautiful gradient fill
  const createGradient = (ctx, chartArea) => {
    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
    gradient.addColorStop(0, 'rgba(79, 70, 229, 0)'); // Fades to transparent at the bottom
    gradient.addColorStop(1, 'rgba(99, 102, 241, 0.5)');   // Brighter indigo at the top
    return gradient;
  };

  const data = {
    labels: chartData.map(d => new Date(d.time)),
    datasets: [{
      label: "Equity Growth",
      data: chartData.map(d => d.balance),
      fill: 'start', // Fill the area under the line
      backgroundColor: (context) => {
        const chart = context.chart;
        const { ctx, chartArea } = chart;
        if (!chartArea) {
          // This case happens on initial render or resizing, return null
          return null;
        }
        return createGradient(ctx, chartArea);
      },
      borderColor: "rgba(129, 140, 248, 1)", // A nice, solid indigo line
      borderWidth: 2, // Slightly thicker line for better visibility
      tension: 0.4, // This creates the smooth, flowing curves
      pointRadius: 0, // We don't want dots on the line itself
      pointHoverRadius: 6, // Show a larger dot only when the user hovers
      pointHoverBackgroundColor: 'rgba(255, 255, 255, 1)',
      pointHoverBorderColor: 'rgba(129, 140, 248, 1)',
    }]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      x: {
        type: "time",
        time: { unit: "day", tooltipFormat: "MMM dd, yyyy" },
        ticks: { color: "#9ca3af", maxRotation: 0, minRotation: 0, autoSkip: true, maxTicksLimit: 7 },
        grid: { color: "rgba(255, 255, 255, 0.05)" } // Very subtle grid lines
      },
      y: {
        ticks: { 
          color: "#9ca3af", 
          callback: v => "$" + v.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})
        },
        grid: { color: "rgba(255, 255, 255, 0.05)" }
      }
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: "index",
        intersect: false,
        backgroundColor: "#1f2937",
        titleColor: '#cbd5e1',
        bodyColor: '#cbd5e1',
        padding: 12,
        cornerRadius: 8,
        displayColors: false, // Hide the little color box in the tooltip
        callbacks: {
          label: ctx => `Equity: ${new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(ctx.parsed.y)}`
        }
      }
    },
    interaction: {
      mode: 'index',
      intersect: false,
    },
  };
  
  return <Line ref={chartRef} data={data} options={options} />;
};


// --- Live Positions Table (No changes here) ---
const LivePositionsTable = ({ trades, isLoading }) => (
  <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-700/50"><thead className="bg-slate-900/30"><tr><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Type</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Size</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Entry</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">P/L</th></tr></thead><tbody className="divide-y divide-slate-700/30">{isLoading ? (<tr><td colSpan="5" className="px-6 py-12 text-center text-slate-400">Loading live trades...</td></tr>) : trades.length > 0 ? (trades.map((trade, idx) => (<tr key={idx} className="hover:bg-slate-700/20 transition-colors"><td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-white">{trade.symbol}</td><td className="px-6 py-4 whitespace-nowrap"><span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${trade.side === 'Buy' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-1 ring-red-500/20'}`}>{trade.side}</span></td><td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{trade.lot.toFixed(2)}</td><td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{trade.entry.toFixed(4)}</td><td className="px-6 py-4 whitespace-nowrap"><span className={`text-sm font-semibold ${trade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{trade.pnl >= 0 ? '+' : ''}{trade.pnl.toFixed(2)}</span></td></tr>))) : (<tr><td colSpan="5" className="px-6 py-12 text-center text-slate-400">No open positions.</td></tr>)}</tbody></table></div>
);

// --- History Table Component (No changes here) ---
const HistoryTable = ({ trades, isLoading }) => (
  <div className="overflow-x-auto"><table className="min-w-full divide-y divide-slate-700/50"><thead className="bg-slate-900/30"><tr><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Symbol</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Type</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Volume</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Close Time</th><th className="px-6 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">Profit</th></tr></thead><tbody className="divide-y divide-slate-700/30">{isLoading ? (<tr><td colSpan="5" className="px-6 py-12 text-center text-slate-400">Loading history...</td></tr>) : trades && trades.length > 0 ? (trades.map((trade, idx) => (<tr key={idx} className="hover:bg-slate-700/20 transition-colors"><td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-white">{trade.symbol}</td><td className="px-6 py-4 whitespace-nowrap"><span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${trade.type === 'Buy' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20' : 'bg-red-500/10 text-red-400 ring-1 ring-red-500/20'}`}>{trade.type}</span></td><td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{trade.volume.toFixed(2)}</td><td className="px-6 py-4 whitespace-nowrap text-sm text-slate-300">{trade.close_time}</td><td className="px-6 py-4 whitespace-nowrap"><span className={`text-sm font-semibold ${trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{trade.profit >= 0 ? '+' : ''}{trade.profit.toFixed(2)}</span></td></tr>))) : (<tr><td colSpan="5" className="px-6 py-12 text-center text-slate-400">No closed trades found.</td></tr>)}</tbody></table></div>
);

// --- Dashboard Component ---
export const Dashboard = ({ user, onLogout }) => {
  // State hooks (no changes here)
  const [botStatus, setBotStatus] = useState('Stopped');
  const [strategy, setStrategy] = useState('trend_follow');
  const [lotSize, setLotSize] = useState(0.01);
  const [maxDailyLoss, setMaxDailyLoss] = useState(200);
  const [maxDrawdown, setMaxDrawdown] = useState(300);
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState('');
  const [trades, setTrades] = useState([]);
  const [isLoadingTrades, setIsLoadingTrades] = useState(true);
  const [accountDetails, setAccountDetails] = useState(user);
  const [history, setHistory] = useState(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [activeTab, setActiveTab] = useState('live');

  // Data fetching useEffect (no changes here)
  useEffect(() => {
    const pollLiveData = async () => {
      try {
        const [tradesResponse, accountResponse] = await Promise.all([
          fetch('http://127.0.0.1:5000/get-positions'),
          fetch('http://127.0.0.1:5000/get-account-info')
        ]);
        if (tradesResponse.ok) {
          const tradesData = await tradesResponse.json();
          setTrades(tradesData.trades || []);
        } else { console.error("Failed to fetch positions"); }
        if (accountResponse.ok) {
          const accountData = await accountResponse.json();
          if (accountData.info) { setAccountDetails(prevDetails => ({ ...prevDetails, ...accountData.info })); }
        } else { console.error("Failed to fetch account info"); }
      } catch (err) { console.error("Error fetching live data:", err); } 
      finally { setIsLoadingTrades(false); }
    };
    const fetchHistoryData = async () => {
      setIsLoadingHistory(true);
      try {
        const historyResponse = await fetch('http://127.0.0.1:5000/get-account-history');
        if (historyResponse.ok) {
          const historyData = await historyResponse.json();
          setHistory(historyData.data);
        } else { console.error("Failed to fetch history:", (await historyResponse.json()).message); }
      } catch (err) { console.error("Error fetching history:", err); } 
      finally { setIsLoadingHistory(false); }
    };
    pollLiveData();
    fetchHistoryData();
    const intervalId = setInterval(pollLiveData, 5000);
    return () => clearInterval(intervalId);
  }, []);

  // Other functions and JSX (no changes from here down)
  const totalPnL = trades.reduce((total, trade) => total + (trade.pnl || 0), 0);
  const activeTrades = trades.length;

  const handleBotAction = async () => {
    setIsUpdating(true); setMessage('');
    const newStatus = botStatus === 'Running' ? 'Stopped' : 'Running';
    const endpoint = newStatus === 'Running' ? 'start-bot' : 'stop-bot';
    try {
      const response = await fetch(`http://127.0.0.1:5000/${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy, lotSize, maxDailyLoss, maxDrawdown }),
      });
      const data = await response.json();
      if (response.ok) { setBotStatus(newStatus); setMessage(data.message); }
      else { setMessage(`Error: ${data.message}`); }
    } catch (err) { setMessage('Error: Could not connect to the backend.'); }
    finally { setIsUpdating(false); setTimeout(() => setMessage(''), 3000); }
  };

  const StatCard = ({ title, value, subtext, icon, colorClass, percentage }) => (
    <div className="bg-slate-800/50 backdrop-blur-sm p-6 rounded-2xl border border-slate-700/50 hover:border-slate-600/50 transition-all"><div className="flex items-start justify-between"><div className="flex-1"><p className="text-sm text-slate-400 font-medium mb-1">{title}</p><p className="text-3xl font-bold text-white mb-1">{value}</p>{percentage !== undefined && (<p className={`text-sm font-semibold ${percentage >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{percentage >= 0 ? '↑' : '↓'} {Math.abs(percentage).toFixed(2)}%</p>)}{subtext && <p className="text-xs text-slate-500">{subtext}</p>}</div><div className={`p-3 rounded-xl ${colorClass}`}>{icon}</div></div></div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white font-sans"><div className="min-h-screen backdrop-blur-3xl"><header className="border-b border-slate-700/50 bg-slate-900/50 backdrop-blur-xl sticky top-0 z-10"><div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4"><div className="flex items-center justify-between"><div className="flex items-center space-x-4"><LogoIcon /><div><h1 className="text-xl font-bold">Nawthviper Trading System</h1><div className="flex items-center space-x-2 mt-0.5"><p className="text-sm text-slate-400">Welcome, Account {user?.accountId || 'N/A'}</p><span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">Deriv-Demo</span></div></div></div><button onClick={onLogout} className="bg-slate-800/80 hover:bg-red-600/80 text-white font-semibold py-2 px-6 rounded-lg transition-all duration-200 border border-slate-700/50 hover:border-red-500/50">Logout</button></div></div></header><main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"><div className="grid grid-cols-1 lg:grid-cols-3 gap-6"><div className="lg:col-span-1 space-y-6"><StatCard title="Account Balance" value={`$${accountDetails?.balance?.toFixed(2) || '0.00'}`} percentage={history?.percentageGain} icon={<svg className="w-6 h-6 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>} colorClass="bg-blue-500/10" /><StatCard title="Current Equity" value={`$${accountDetails?.equity?.toFixed(2) || '0.00'}`} icon={<svg className="w-6 h-6 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>} colorClass="bg-emerald-500/10" /><StatCard title="Live P/L" value={<span className={totalPnL >= 0 ? 'text-emerald-400' : 'text-red-400'}>{totalPnL >= 0 ? '+' : '-'}${Math.abs(totalPnL).toFixed(2)}</span>} subtext={`${activeTrades} active trade${activeTrades !== 1 ? 's' : ''}`} icon={<svg className="w-6 h-6 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>} colorClass="bg-purple-500/10" /><StatCard title="Total Net Profit" value={<span className={history?.totalProfitLoss >= 0 ? 'text-emerald-400' : 'text-red-400'}>{history?.totalProfitLoss >= 0 ? '+' : '-'}${Math.abs(history?.totalProfitLoss || 0).toFixed(2)}</span>} subtext="From all closed trades" icon={<svg className="w-6 h-6 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" /></svg>} colorClass="bg-yellow-500/10" /><div className="bg-slate-800/50 backdrop-blur-sm p-6 rounded-2xl border border-slate-700/50"><h3 className="text-lg font-bold mb-4 flex items-center"><span className="mr-2">Bot Controls</span>{botStatus === 'Running' && (<span className="inline-flex items-center"><span className="animate-pulse h-2 w-2 rounded-full bg-emerald-400 mr-2"></span><span className="text-xs font-medium text-emerald-400">Active</span></span>)}</h3><div className="space-y-4"><div><label className="block text-sm font-medium text-slate-400 mb-2">Strategy Mode</label><select value={strategy} onChange={e => setStrategy(e.target.value)} className="w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"><option value="trend_follow">Trend-Follow (Safe)</option><option value="aggressive">Aggressive (Scalp)</option></select></div><div><label className="block text-sm font-medium text-slate-400 mb-2">Lot Size</label><select value={lotSize} onChange={e => setLotSize(parseFloat(e.target.value))} className="w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"><option value={0.01}>0.01</option><option value={0.02}>0.02</option><option value={0.05}>0.05</option><option value={0.1}>0.1</option></select></div><div><label htmlFor="max-loss" className="block text-sm font-medium text-slate-400 mb-2">Max Daily Loss ($)</label><input id="max-loss" type="number" value={maxDailyLoss} onChange={e => setMaxDailyLoss(parseFloat(e.target.value))} className="w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all" /></div><div><label htmlFor="max-dd" className="block text-sm font-medium text-slate-400 mb-2">Max Drawdown ($)</label><input id="max-dd" type="number" value={maxDrawdown} onChange={e => setMaxDrawdown(parseFloat(e.target.value))} className="w-full bg-slate-700/50 border border-slate-600/50 rounded-lg px-4 py-2.5 text-white focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all" /></div><button onClick={handleBotAction} disabled={isUpdating} className={`w-full font-semibold py-3 px-4 rounded-lg transition-all duration-300 flex items-center justify-center space-x-2 shadow-lg ${botStatus === 'Running' ? 'bg-red-600 hover:bg-red-700 shadow-red-500/25' : 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-500/25'} disabled:opacity-50 disabled:cursor-not-allowed`}><span className={`w-2 h-2 rounded-full ${botStatus === 'Running' ? 'bg-white animate-pulse' : 'bg-white'}`}></span><span>{isUpdating ? 'Updating...' : (botStatus === 'Running' ? 'Stop Bot' : 'Start Bot')}</span></button>{message && (<div className="text-center text-sm text-slate-400 bg-slate-700/30 rounded-lg py-2 px-3">{message}</div>)}</div></div></div><div className="lg:col-span-2 space-y-6"><div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6"><h2 className="text-xl font-bold mb-4">Performance History</h2><div className="h-64">{isLoadingHistory ? (<div className="flex items-center justify-center h-full text-slate-400">Loading Chart...</div>) : history && history.chartData && history.chartData.length > 0 ? (<PerformanceChart chartData={history.chartData} />) : (<div className="flex items-center justify-center h-full text-slate-400">No historical data to display.</div>)}</div></div><div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 overflow-hidden"><div className="px-6 border-b border-slate-700/50"><nav className="-mb-px flex space-x-6" aria-label="Tabs"><button onClick={() => setActiveTab('live')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all ${activeTab === 'live' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-500'}`}>Live Positions<span className={`ml-2 inline-flex items-center justify-center px-2.5 py-1 rounded-full text-xs font-bold ${activeTab === 'live' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-700 text-slate-300'}`}>{activeTrades}</span></button><button onClick={() => setActiveTab('history')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-all ${activeTab === 'history' ? 'border-indigo-500 text-indigo-400' : 'border-transparent text-slate-400 hover:text-slate-300 hover:border-slate-500'}`}>Trade History</button></nav></div><div className="p-0">{activeTab === 'live' ? (<LivePositionsTable trades={trades} isLoading={isLoadingTrades} />) : (<HistoryTable trades={history?.closedTrades} isLoading={isLoadingHistory} />)}</div></div></div></div></main></div></div>
  );
};
