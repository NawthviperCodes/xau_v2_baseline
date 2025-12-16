import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import TradingViewChart from '../components/TradingViewChart';
import ForexNews from '../components/ForexNews';

// --- Animation Variants ---
const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15 }
  }
};

const tickerVariants = {
  animate: {
    x: [0, -1000],
    transition: {
      x: {
        repeat: Infinity,
        repeatType: "loop",
        duration: 20,
        ease: "linear",
      },
    },
  },
};

// --- Dummy Live Trades Data for Ticker ---
const LIVE_TRADES = [
  { pair: "XAUUSD", type: "BUY", price: "2045.50", profit: "+$450" },
  { pair: "US30", type: "SELL", price: "34,150", profit: "+$1,200" },
  { pair: "NAS100", type: "BUY", price: "15,200", profit: "+$890" },
  { pair: "GBPJPY", type: "SELL", price: "182.40", profit: "+$320" },
  { pair: "XAUUSD", type: "BUY", price: "2048.10", profit: "+$210" },
  { pair: "EURUSD", type: "SELL", price: "1.0850", profit: "+$150" },
];

const HomePage = () => {
  return (
    <div className="relative overflow-x-hidden w-full">
      
      {/* --- LIVE TICKER --- */}
      <div className="w-full bg-indigo-900/20 border-b border-indigo-500/20 h-10 flex items-center overflow-hidden relative z-30">
        <div className="px-4 bg-indigo-600 h-full flex items-center z-10 text-xs font-bold uppercase tracking-wider shadow-lg">
          Live Executions
        </div>
        <motion.div className="flex whitespace-nowrap" variants={tickerVariants} animate="animate">
          {[...LIVE_TRADES, ...LIVE_TRADES, ...LIVE_TRADES].map((t, i) => (
            <div key={i} className="flex items-center mx-6 text-xs font-mono text-indigo-200">
              <span className="font-bold text-white mr-2">{t.pair}</span>
              <span className={t.type === 'BUY' ? 'text-emerald-400' : 'text-red-400'}>{t.type}</span>
              <span className="mx-2 text-slate-600">|</span>
              <span>{t.price}</span>
              <span className="ml-2 px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">{t.profit}</span>
            </div>
          ))}
        </motion.div>
      </div>

      {/* --- HERO SECTION --- */}
      <div className="relative pt-20 pb-32 px-6 z-20">
        {/* Abstract Background */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none"></div>

        <div className="max-w-7xl mx-auto text-center relative z-10">
          <motion.div initial="hidden" animate="visible" variants={staggerContainer}>
            
            <motion.div variants={fadeInUp} className="inline-flex items-center space-x-2 bg-slate-900/80 border border-slate-700 rounded-full px-4 py-1.5 mb-8 backdrop-blur-md">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-sm font-medium text-slate-300">V2.0 Sniper Engine Online</span>
            </motion.div>
            
            <motion.h1 variants={fadeInUp} className="text-6xl md:text-8xl font-extrabold tracking-tight mb-8 leading-tight">
              Algorithmic <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-400 animate-gradient-x">Dominance.</span>
            </motion.h1>
            
            <motion.p variants={fadeInUp} className="text-xl text-slate-400 mb-12 max-w-3xl mx-auto leading-relaxed">
              We don't trade often. We trade right. Nawthviper executes institutional order-flow logic directly on your MT5 terminal, targeting a <strong>79% win rate</strong> with mathematical precision.
            </motion.p>
            
            <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row justify-center gap-4">
              <Link to="/services" className="bg-white text-slate-900 hover:bg-slate-200 font-bold py-4 px-10 rounded-xl transition-all shadow-[0_0_40px_rgba(255,255,255,0.2)] text-lg">
                View Access Tiers
              </Link>
              <Link to="/about" className="px-10 py-4 rounded-xl border border-slate-700 hover:bg-slate-800/50 text-slate-300 hover:text-white transition-all text-lg">
                Meet the Architect
              </Link>
            </motion.div>
          </motion.div>
        </div>
      </div>

      {/* --- LIVE MARKET DATA SECTION --- */}
      <section className="py-20 bg-slate-900/30 border-y border-white/5 relative z-30">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-end mb-12">
            <div>
              <h2 className="text-3xl font-bold mb-2">Live Market Analysis</h2>
              <p className="text-slate-400">Real-time XAUUSD data feeds powering our algorithm.</p>
            </div>
            <div className="flex items-center space-x-2 text-emerald-400 mt-4 md:mt-0">
              <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-mono uppercase tracking-widest">Data Stream Active</span>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-8 items-start">
            {/* Chart (Takes up 2 columns) */}
            <div className="lg:col-span-2 bg-slate-950 rounded-2xl overflow-hidden border border-slate-800">
              <TradingViewChart />
            </div>
            
            {/* News Feed (Takes up 1 column) - FIXED HEIGHT AND OVERFLOW */}
            <div className="lg:col-span-1 h-[500px] bg-slate-950 rounded-2xl overflow-hidden border border-slate-800 relative">
              <ForexNews />
            </div>
          </div>
        </div>
      </section>

      {/* --- STRATEGY BREAKDOWN --- */}
      {/* Added extra top padding and explicit z-index to force separation */}
      <section className="py-32 px-6 relative z-20 bg-[#0B0F19]">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-20">
            <h2 className="text-4xl font-bold mb-6">How the Sniper Works</h2>
            <p className="text-slate-400 max-w-2xl mx-auto">Our bot isn't guessing. It follows a strict 4-step institutional checklist before every single trade.</p>
          </div>

          <div className="grid md:grid-cols-4 gap-6">
            {[
              { title: "1. Structure Scan", desc: "Scans H1/H4 timeframes for institutional Supply & Demand zones.", color: "bg-blue-500", step: "01" },
              { title: "2. Trend Filter", desc: "Verifies the daily bias. We never trade against the dominant trend.", color: "bg-indigo-500", step: "02" },
              { title: "3. Trap Detection", desc: "Waits for a 'Stop Hunt' or 'Liquidity Sweep' to trap retail traders.", color: "bg-purple-500", step: "03" },
              { title: "4. Execution", desc: "Enters with millisecond precision only when price confirms reversal.", color: "bg-emerald-500", step: "04" }
            ].map((step, i) => (
              <motion.div 
                key={i}
                whileHover={{ y: -10 }}
                className="bg-slate-900 border border-slate-800 p-8 rounded-2xl relative overflow-hidden group h-full"
              >
                <div className={`absolute top-0 left-0 w-full h-1 ${step.color}`}></div>
                <div className="text-6xl font-bold text-slate-800 absolute top-4 right-4 opacity-50 group-hover:opacity-10 transition-opacity">{step.step}</div>
                <h3 className="text-xl font-bold mb-4 relative z-10">{step.title}</h3>
                <p className="text-slate-400 text-sm relative z-10 leading-relaxed">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

    </div>
  );
};

export default HomePage;