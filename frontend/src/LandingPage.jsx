import React, { useState } from 'react';
import { motion } from 'framer-motion';

// --- Reusable Components ---
const LogoIcon = ({ className = "w-10 h-10" }) => (
  <div className={`${className} relative group overflow-hidden bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20`}>
    <div className="absolute inset-0 bg-white/20 group-hover:translate-x-full transition-transform duration-500 ease-out skew-x-12"></div>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-6 h-6 relative z-10">
      <path d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-2.625 6c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975V9.225c0-.54-.435-.975-.975-.975h-5.25zm0 4.5c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975v-.015c0-.54-.435-.975-.975-.975h-5.25z" />
    </svg>
  </div>
);

// --- Animation Variants ---
const fadeInUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" } }
};

const staggerContainer = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.15, delayChildren: 0.2 }
  }
};

const floatAnimation = {
  animate: {
    y: [0, -15, 0],
    transition: { duration: 6, repeat: Infinity, ease: "easeInOut" }
  }
};

// --- Main Landing Page Component ---
const LandingPage = ({ onAccessDashboard }) => {
  const [contactStatus, setContactStatus] = useState('');

  const handleContactSubmit = async (e) => {
    e.preventDefault();
    setContactStatus('Sending...');
    // ... (Keep existing logic here)
    setTimeout(() => setContactStatus('Message sent!'), 1500); // Simulating success for UI demo
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white font-sans overflow-x-hidden selection:bg-indigo-500/30">
      
      {/* --- BACKGROUND FX --- */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        {/* Technical Grid Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
        {/* Glow Orbs */}
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[120px]"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-purple-600/20 rounded-full blur-[120px]"></div>
      </div>

      {/* --- HEADER --- */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0B0F19]/80 backdrop-blur-md">
        <nav className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-3 cursor-pointer">
            <LogoIcon />
            <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
              Nawthviper
            </span>
          </div>
          
          <div className="hidden md:flex items-center space-x-8">
            {['About', 'Services', 'Signals', 'Contact'].map((item) => (
              <a key={item} href={`#${item.toLowerCase()}`} className="text-sm font-medium text-slate-400 hover:text-white transition-colors relative group">
                {item}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-indigo-500 transition-all group-hover:w-full"></span>
              </a>
            ))}
          </div>

          <button 
            onClick={onAccessDashboard} 
            className="hidden sm:block bg-white text-[#0B0F19] hover:bg-slate-200 text-sm font-bold py-2.5 px-6 rounded-lg transition-all shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.2)]"
          >
            Launch App
          </button>
        </nav>
      </header>

      <main className="relative z-10">
        
        {/* --- HERO SECTION --- */}
        <section id="home" className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 px-6">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
            
            {/* Left: Text */}
            <motion.div initial="hidden" animate="visible" variants={staggerContainer} className="text-left">
              <motion.div variants={fadeInUp} className="inline-flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3 py-1 mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-medium text-indigo-300">V2.0 Engine Live</span>
              </motion.div>
              
              <motion.h1 variants={fadeInUp} className="text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
                Algorithmic <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-400 animate-gradient-x">Precision.</span>
              </motion.h1>
              
              <motion.p variants={fadeInUp} className="text-lg text-slate-400 mb-8 max-w-lg leading-relaxed">
                Stop trading with emotion. Nawthviper connects directly to your MT5 terminal to execute institutional-grade strategies with mathematical discipline.
              </motion.p>
              
              <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4">
                <button onClick={onAccessDashboard} className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-4 px-8 rounded-xl transition-all shadow-lg shadow-indigo-600/25 flex items-center justify-center">
                  Start Trading
                  <svg className="w-4 h-4 ml-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
                </button>
                <a href="#about" className="px-8 py-4 rounded-xl border border-slate-700 hover:bg-slate-800/50 text-slate-300 hover:text-white transition-all text-center">
                  How it works
                </a>
              </motion.div>
            </motion.div>

            {/* Right: Abstract UI Visualization (The "Unique" Part) */}
            <motion.div 
              initial={{ opacity: 0, x: 50 }} 
              animate={{ opacity: 1, x: 0 }} 
              transition={{ duration: 0.8, delay: 0.4 }}
              className="relative hidden lg:block"
            >
              {/* Floating Glass Cards representing the Dashboard */}
              <motion.div variants={floatAnimation} animate="animate" className="relative z-10">
                {/* Card 1: Main Equity */}
                <div className="absolute top-0 right-0 w-80 h-48 bg-slate-900/60 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl transform rotate-6 border-t-indigo-500/50">
                   <div className="flex justify-between items-center mb-4">
                      <div className="h-8 w-8 bg-indigo-500/20 rounded-lg flex items-center justify-center"><svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg></div>
                      <span className="text-xs text-emerald-400 font-mono">+12.5%</span>
                   </div>
                   <div className="text-slate-400 text-sm mb-1">Total Equity</div>
                   <div className="text-3xl font-bold text-white">$24,592.00</div>
                   <div className="mt-4 h-1 w-full bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full w-2/3 bg-gradient-to-r from-indigo-500 to-purple-500"></div>
                   </div>
                </div>

                {/* Card 2: Active Trade */}
                <div className="absolute top-32 right-48 w-64 bg-slate-800/80 backdrop-blur-xl border border-slate-600/50 rounded-2xl p-5 shadow-2xl transform -rotate-3 border-l-4 border-l-emerald-500">
                   <div className="flex justify-between text-xs text-slate-400 mb-2">
                      <span>GBP/USD</span>
                      <span className="text-emerald-400">Running</span>
                   </div>
                   <div className="flex justify-between items-end">
                      <div>
                        <div className="text-lg font-bold">Buy 1.00</div>
                        <div className="text-xs text-slate-500">@ 1.2450</div>
                      </div>
                      <div className="text-xl font-bold text-emerald-400">+$145.00</div>
                   </div>
                </div>
              </motion.div>
              
              {/* Background Glow behind cards */}
              <div className="absolute top-10 right-20 w-96 h-96 bg-indigo-500/30 rounded-full blur-[100px] pointer-events-none"></div>
            </motion.div>
          </div>
        </section>

        {/* --- FEATURES (BENTO GRID) --- */}
        <section id="services" className="py-24 relative">
          <div className="max-w-7xl mx-auto px-6">
            <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={staggerContainer} className="mb-16">
              <motion.h2 variants={fadeInUp} className="text-3xl md:text-5xl font-bold mb-6">Engineered for <span className="text-indigo-400">Profit.</span></motion.h2>
              <div className="h-1 w-20 bg-indigo-500 rounded-full"></div>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[minmax(180px,auto)]">
              {/* Large Feature */}
              <motion.div whileHover={{ y: -5 }} className="md:col-span-2 bg-gradient-to-br from-slate-900 to-slate-800 border border-slate-700/50 rounded-3xl p-8 relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/10 rounded-full blur-3xl group-hover:bg-indigo-500/20 transition-all duration-500"></div>
                <h3 className="text-2xl font-bold mb-4 relative z-10">Low Latency Execution</h3>
                <p className="text-slate-400 max-w-md relative z-10">Our Python-based engine processes market ticks in milliseconds. No repainting, no hesitation. Just pure logic execution directly to your broker.</p>
                <div className="mt-8 flex gap-2">
                   <span className="px-3 py-1 bg-slate-950/50 rounded-lg text-xs font-mono text-emerald-400 border border-emerald-500/20">0.4ms Ping</span>
                   <span className="px-3 py-1 bg-slate-950/50 rounded-lg text-xs font-mono text-indigo-400 border border-indigo-500/20">MT5 Direct</span>
                </div>
              </motion.div>

              {/* Tall Feature */}
              <motion.div whileHover={{ y: -5 }} className="md:row-span-2 bg-slate-900 border border-slate-700/50 rounded-3xl p-8 flex flex-col justify-between group overflow-hidden">
                <div className="absolute -bottom-10 -right-10 w-40 h-40 bg-purple-500/20 rounded-full blur-2xl group-hover:scale-150 transition-transform duration-700"></div>
                <div>
                   <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center mb-6 text-purple-400"><svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg></div>
                   <h3 className="text-2xl font-bold mb-4">Capital Guard</h3>
                   <p className="text-slate-400 text-sm leading-relaxed">Hard-coded risk limits protect your account from massive drawdowns. Set your daily loss limit and the bot kills the switch automatically.</p>
                </div>
                <div className="mt-8 pt-8 border-t border-slate-800">
                    <p className="text-xs font-mono text-slate-500">MAX_DRAWDOWN_LIMIT = TRUE</p>
                </div>
              </motion.div>

              {/* Standard Feature */}
              <motion.div whileHover={{ y: -5 }} className="bg-slate-900 border border-slate-700/50 rounded-3xl p-8">
                <h3 className="text-xl font-bold mb-2">Trend & Scalp Modes</h3>
                <p className="text-sm text-slate-400">Switch between aggressive scalping for high volatility or safe trend-following for steady growth.</p>
              </motion.div>

              {/* Standard Feature */}
              <motion.div whileHover={{ y: -5 }} className="bg-slate-900 border border-slate-700/50 rounded-3xl p-8">
                 <h3 className="text-xl font-bold mb-2">Performance Analytics</h3>
                 <p className="text-sm text-slate-400">Visualize your equity curve. Analyze wins vs losses to refine your edge.</p>
              </motion.div>
            </div>
          </div>
        </section>

        {/* --- SIGNALS TEASER (NEW!) --- */}
        <section id="signals" className="py-20 border-y border-white/5 bg-slate-900/30">
           <div className="max-w-4xl mx-auto px-6 text-center">
              <span className="text-emerald-400 font-mono text-sm tracking-widest uppercase">Coming Q1 2026</span>
              <h2 className="text-3xl md:text-4xl font-bold mt-4 mb-6">Nawthviper Premium Signals</h2>
              <p className="text-slate-400 text-lg mb-8">
                 Don't want to run the bot? Receive our high-probability setups directly to your phone via Telegram or view them live on our upcoming Signals Dashboard.
              </p>
              <div className="flex justify-center space-x-4">
                 <div className="px-6 py-3 bg-slate-800 rounded-lg border border-slate-700 flex items-center space-x-3 opacity-75">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium">Telegram Integration</span>
                 </div>
                 <div className="px-6 py-3 bg-slate-800 rounded-lg border border-slate-700 flex items-center space-x-3 opacity-75">
                    <div className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse"></div>
                    <span className="text-sm font-medium">Web Terminal</span>
                 </div>
              </div>
           </div>
        </section>

        {/* --- CONTACT FORM --- */}
        <section id="contact" className="py-24">
           <div className="max-w-xl mx-auto px-6">
              <div className="text-center mb-12">
                 <h2 className="text-3xl font-bold">Start Your Journey</h2>
                 <p className="text-slate-400 mt-2">Ready to automate? Send us a message.</p>
              </div>
              <form onSubmit={handleContactSubmit} className="space-y-4">
                 <input type="text" name="name" placeholder="Name" required className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600" />
                 <input type="email" name="email" placeholder="Email Address" required className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600" />
                 <textarea name="message" rows="4" placeholder="How can we help?" required className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600"></textarea>
                 <button type="submit" className="w-full bg-white text-slate-900 font-bold py-4 rounded-xl hover:bg-slate-200 transition-colors shadow-lg">
                    {contactStatus || 'Send Message'}
                 </button>
              </form>
           </div>
        </section>

      </main>

      {/* --- FOOTER --- */}
      <footer className="border-t border-white/5 py-12 bg-[#0B0F19]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center">
           <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <LogoIcon className="w-8 h-8 opacity-80" />
              <span className="font-bold text-slate-300">Nawthviper</span>
           </div>
           <div className="text-slate-500 text-sm">
              &copy; {new Date().getFullYear()} Nawthviper Systems. Designed for MT5.
           </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;