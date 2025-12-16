import React from 'react';

const SignalsPage = () => {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24 text-center">
        <h1 className="text-4xl md:text-6xl font-bold mb-6">Live Signals</h1>
        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-16">
            Real-time trade execution from the Nawthviper Engine. 
            <br/><span className="text-indigo-400 text-sm">Note: Signal feed is exclusive to Gold Tier members.</span>
        </p>

        {/* Simulated Live Signal Feed UI */}
        <div className="max-w-4xl mx-auto bg-slate-900 rounded-2xl border border-slate-800 overflow-hidden">
            <div className="bg-slate-800 px-6 py-4 flex justify-between items-center border-b border-slate-700">
                <span className="font-mono text-emerald-400 text-sm flex items-center gap-2">
                    <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span> SYSTEM ONLINE
                </span>
                <span className="text-xs text-slate-500">Last updated: Just now</span>
            </div>
            
            <div className="divide-y divide-slate-800">
                {/* Signal Item 1 */}
                <div className="p-6 flex items-center justify-between hover:bg-slate-800/30 transition-colors">
                    <div className="text-left">
                        <div className="flex items-center gap-3 mb-1">
                            <span className="text-white font-bold">XAUUSD</span>
                            <span className="bg-emerald-500/20 text-emerald-400 text-xs px-2 py-0.5 rounded font-bold">BUY</span>
                        </div>
                        <div className="text-xs text-slate-500">12:30 PM • Sniper Mode</div>
                    </div>
                    <div className="text-right">
                        <div className="text-slate-300 font-mono">@ 2045.50</div>
                        <div className="text-emerald-500 text-xs font-bold">+45 Pips Running</div>
                    </div>
                </div>

                {/* Signal Item 2 */}
                <div className="p-6 flex items-center justify-between hover:bg-slate-800/30 transition-colors opacity-75">
                    <div className="text-left">
                        <div className="flex items-center gap-3 mb-1">
                            <span className="text-white font-bold">US30</span>
                            <span className="bg-red-500/20 text-red-400 text-xs px-2 py-0.5 rounded font-bold">SELL</span>
                        </div>
                        <div className="text-xs text-slate-500">10:15 AM • Trend Follow</div>
                    </div>
                    <div className="text-right">
                        <div className="text-slate-300 font-mono">@ 34,150.00</div>
                        <div className="text-emerald-500 text-xs font-bold">TP HIT (+120 Pips)</div>
                    </div>
                </div>
                
                {/* Locked Content Overlay */}
                <div className="p-12 relative">
                    <div className="absolute inset-0 bg-slate-900/80 backdrop-blur-sm flex flex-col items-center justify-center z-10">
                        <svg className="w-12 h-12 text-slate-600 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                        <h3 className="text-xl font-bold text-white mb-2">Signal Feed Locked</h3>
                        <p className="text-slate-400 text-sm mb-6">Upgrade to Gold Tier to view real-time signals.</p>
                        <a href="/contact" className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold text-sm transition-colors">
                            Unlock Access
                        </a>
                    </div>
                    {/* Fake content behind blur */}
                    <div className="opacity-20 blur-sm">
                        <div className="h-16 bg-slate-800 rounded mb-4"></div>
                        <div className="h-16 bg-slate-800 rounded mb-4"></div>
                        <div className="h-16 bg-slate-800 rounded"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
  );
};

export default SignalsPage;