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

// --- Testimonials Data ---
const TESTIMONIALS = [
  { name: "Sarah K.", profit: "+$4,200", text: "I was skeptical about bots, but the Sniper Mode is scary accurate. The 14-day trial convinced me." },
  { name: "David M.", profit: "+$12,500", text: "Finally a system that respects risk management. The daily circuit breaker saved me during NFP." },
  { name: "Lerato P.", profit: "+$850", text: "Thabo's team is legit. The signals are clean, no repainting. Best investment for my small account." },
];

// --- Main Landing Page Component ---
const LandingPage = ({ onAccessDashboard }) => {
  
  // WhatsApp Integration Logic
  const [formData, setFormData] = useState({ name: '', message: '' });

  const handleWhatsAppSubmit = (e) => {
    e.preventDefault();
    const phoneNumber = "27662297338"; // Thabo's Number (International Format without +)
    const text = `Hi Nawthviper, my name is ${formData.name}. ${formData.message}`;
    const url = `https://wa.me/${phoneNumber}?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
  };

  return (
    <div className="min-h-screen bg-[#0B0F19] text-white font-sans overflow-x-hidden selection:bg-indigo-500/30">
      
      {/* --- BACKGROUND FX --- */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]"></div>
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-indigo-600/20 rounded-full blur-[120px]"></div>
      </div>

      {/* --- HEADER --- */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0B0F19]/90 backdrop-blur-md">
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

          <button onClick={onAccessDashboard} className="hidden sm:block bg-white text-[#0B0F19] hover:bg-slate-200 text-sm font-bold py-2.5 px-6 rounded-lg transition-all shadow-lg hover:shadow-white/10">
            Launch App
          </button>
        </nav>
      </header>

      <main className="relative z-10">
        
        {/* --- HERO SECTION --- */}
        <section id="home" className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 px-6">
          <div className="max-w-7xl mx-auto grid lg:grid-cols-2 gap-16 items-center">
            <motion.div initial="hidden" animate="visible" variants={staggerContainer} className="text-left">
              <motion.div variants={fadeInUp} className="inline-flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full px-3 py-1 mb-8">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <span className="text-xs font-medium text-indigo-300">V2.0 Sniper Engine Live</span>
              </motion.div>
              
              <motion.h1 variants={fadeInUp} className="text-5xl lg:text-7xl font-bold tracking-tight leading-[1.1] mb-6">
                Algorithmic <br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-indigo-400 animate-gradient-x">Precision.</span>
              </motion.h1>
              
              <motion.p variants={fadeInUp} className="text-lg text-slate-400 mb-8 max-w-lg leading-relaxed">
                Execute institutional-grade strategies with mathematical discipline. The Nawthviper engine connects directly to your MT5 terminal for latency-free trading.
              </motion.p>
              
              <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4">
                <a href="#pricing" className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-4 px-8 rounded-xl transition-all shadow-lg shadow-indigo-600/25 flex items-center justify-center">
                  Start Free Trial
                </a>
                <a href="#services" className="px-8 py-4 rounded-xl border border-slate-700 hover:bg-slate-800/50 text-slate-300 hover:text-white transition-all text-center">
                  Explore Features
                </a>
              </motion.div>
            </motion.div>

            {/* Right: Feature Visualization */}
            <motion.div 
              initial={{ opacity: 0, x: 50 }} 
              animate={{ opacity: 1, x: 0 }} 
              transition={{ duration: 0.8, delay: 0.4 }}
              className="relative hidden lg:block"
            >
               <div className="relative z-10 w-full max-w-md mx-auto">
                  {/* Floating Terminal Window */}
                  <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
                      <div className="flex justify-between items-center mb-6 border-b border-white/5 pb-4">
                          <div className="flex space-x-2">
                              <div className="w-3 h-3 rounded-full bg-red-500"></div>
                              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                              <div className="w-3 h-3 rounded-full bg-green-500"></div>
                          </div>
                          <div className="text-xs font-mono text-slate-500">XAUUSD [M5]</div>
                      </div>
                      <div className="space-y-4">
                          <div className="flex justify-between items-center">
                              <div className="text-sm text-slate-400">Signal Confidence</div>
                              <div className="text-sm text-emerald-400 font-bold">92.4%</div>
                          </div>
                          <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full w-[92%] bg-emerald-500"></div>
                          </div>
                          <div className="grid grid-cols-2 gap-4 mt-4">
                              <div className="bg-slate-800/50 p-3 rounded-lg text-center">
                                  <div className="text-xs text-slate-500">Entry</div>
                                  <div className="font-mono text-white">2045.50</div>
                              </div>
                              <div className="bg-slate-800/50 p-3 rounded-lg text-center">
                                  <div className="text-xs text-slate-500">Target</div>
                                  <div className="font-mono text-emerald-400">2058.20</div>
                              </div>
                          </div>
                      </div>
                  </div>
               </div>
               <div className="absolute top-10 right-20 w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] pointer-events-none"></div>
            </motion.div>
          </div>
        </section>

        {/* --- ABOUT US (FOUNDER) --- */}
        <section id="about" className="py-24 bg-slate-900/30 border-y border-white/5">
            <div className="max-w-7xl mx-auto px-6 grid md:grid-cols-2 gap-12 items-center">
                <div>
                    <h2 className="text-3xl font-bold mb-6">Meet the Architect</h2>
                    <p className="text-slate-400 mb-6 leading-relaxed">
                        Nawthviper was engineered by <span className="text-white font-semibold">Thabo Gelson Masilopana</span>, a Computer Science graduate and Quantitative Software Developer.
                    </p>
                    <p className="text-slate-400 mb-8 leading-relaxed">
                        Frustrated by retail trading indicators that lag and repaint, Thabo built a proprietary execution engine that trades purely on institutional logic: Order Blocks, Liquidity Sweeps, and Time/Price theory.
                    </p>
                    <div className="flex items-center space-x-4">
                        <div className="px-4 py-2 bg-slate-800 rounded-lg text-sm border border-slate-700 text-slate-300">
                            Computer Science Grad
                        </div>
                        <div className="px-4 py-2 bg-slate-800 rounded-lg text-sm border border-slate-700 text-slate-300">
                            Quant Developer
                        </div>
                    </div>
                </div>
                
                {/* Testimonials */}
                <div className="space-y-4">
                    {TESTIMONIALS.map((t, i) => (
                        <div key={i} className="bg-slate-800/40 p-6 rounded-xl border border-white/5 backdrop-blur-sm">
                            <div className="flex justify-between items-start mb-2">
                                <span className="font-bold text-white">{t.name}</span>
                                <span className="text-emerald-400 text-sm font-mono bg-emerald-500/10 px-2 py-1 rounded">{t.profit}</span>
                            </div>
                            <p className="text-slate-400 text-sm">"{t.text}"</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>

        {/* --- SERVICES & PRICING --- */}
        <section id="pricing" className="py-24">
            <div className="max-w-7xl mx-auto px-6">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-bold mb-4">Choose Your Access</h2>
                    <p className="text-slate-400">Institutional tools for retail traders.</p>
                </div>

                <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                    {/* Free Tier */}
                    <div className="bg-slate-900 border border-slate-700 rounded-3xl p-8 hover:border-slate-500 transition-colors">
                        <h3 className="text-xl font-bold text-white mb-2">Trial Access</h3>
                        <div className="text-3xl font-bold text-white mb-6">Free <span className="text-sm font-normal text-slate-500">/ 14 Days</span></div>
                        <ul className="space-y-4 mb-8 text-slate-400 text-sm">
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> Access to Dashboard</li>
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> XAUUSD Signals Only</li>
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> Standard Execution Speed</li>
                            <li className="flex items-center opacity-50"><span className="mr-2">✕</span> WhatsApp Alerts</li>
                        </ul>
                        <button onClick={onAccessDashboard} className="w-full py-4 rounded-xl border border-white/10 hover:bg-white/5 transition-all text-white font-semibold">
                            Start Trial
                        </button>
                    </div>

                    {/* Gold Tier */}
                    <div className="bg-gradient-to-br from-indigo-900/40 to-slate-900 border border-indigo-500/50 rounded-3xl p-8 relative overflow-hidden">
                        <div className="absolute top-0 right-0 bg-indigo-600 text-white text-xs font-bold px-3 py-1 rounded-bl-xl">POPULAR</div>
                        <h3 className="text-xl font-bold text-white mb-2">Gold Tier</h3>
                        <div className="text-3xl font-bold text-white mb-6">R500 <span className="text-sm font-normal text-slate-500">/ Month</span></div>
                        <ul className="space-y-4 mb-8 text-slate-300 text-sm">
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> Full Dashboard Access</li>
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> All Assets (Indices + Forex)</li>
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> Millisecond Latency</li>
                            <li className="flex items-center"><span className="text-emerald-400 mr-2">✓</span> Direct WhatsApp Alerts</li>
                        </ul>
                        <button className="w-full py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 transition-all text-white font-bold shadow-lg shadow-indigo-600/20">
                            Upgrade Now
                        </button>
                    </div>
                </div>
            </div>
        </section>

        {/* --- SIGNALS & FEATURES --- */}
        <section id="signals" className="py-24 bg-slate-900/30 border-y border-white/5">
            <div className="max-w-7xl mx-auto px-6">
                <div className="grid md:grid-cols-3 gap-8 text-center">
                    <div className="p-6">
                        <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 text-emerald-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        </div>
                        <h3 className="font-bold text-white mb-2">High Voltage</h3>
                        <p className="text-sm text-slate-400">Optimized for NAS100, US30, and Gold volatility.</p>
                    </div>
                    <div className="p-6">
                        <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 text-purple-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                        </div>
                        <h3 className="font-bold text-white mb-2">Bank Security</h3>
                        <p className="text-sm text-slate-400">Your broker details are encrypted. We never hold your funds.</p>
                    </div>
                    <div className="p-6">
                        <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center mx-auto mb-4 text-blue-400">
                            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                        </div>
                        <h3 className="font-bold text-white mb-2">Live Analytics</h3>
                        <p className="text-sm text-slate-400">Track equity growth and drawdowns in real-time.</p>
                    </div>
                </div>
            </div>
        </section>

        {/* --- CONTACT (WHATSAPP INTEGRATION) --- */}
        <section id="contact" className="py-24">
           <div className="max-w-xl mx-auto px-6">
              <div className="text-center mb-12">
                 <h2 className="text-3xl font-bold">Contact Support</h2>
                 <p className="text-slate-400 mt-2">Questions about the bot? Chat directly with Thabo.</p>
              </div>
              <form onSubmit={handleWhatsAppSubmit} className="space-y-4">
                 <input 
                    type="text" 
                    placeholder="Your Name" 
                    required 
                    value={formData.name}
                    onChange={(e) => setFormData({...formData, name: e.target.value})}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600" 
                 />
                 <textarea 
                    rows="4" 
                    placeholder="How can we help?" 
                    required 
                    value={formData.message}
                    onChange={(e) => setFormData({...formData, message: e.target.value})}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none transition-all placeholder:text-slate-600"
                 ></textarea>
                 <button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-4 rounded-xl transition-colors shadow-lg flex items-center justify-center">
                    <span className="mr-2">Send via WhatsApp</span>
                    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M.057 24l1.687-6.163c-1.041-1.804-1.588-3.849-1.587-5.946.003-6.556 5.338-11.891 11.893-11.891 3.181.001 6.167 1.24 8.413 3.488 2.245 2.248 3.481 5.236 3.48 8.414-.003 6.557-5.338 11.892-11.893 11.892-1.99-.001-3.951-.5-5.688-1.448l-6.305 1.654zm6.597-3.807c1.676.995 3.276 1.591 5.392 1.592 5.448 0 9.886-4.434 9.889-9.885.002-5.462-4.415-9.89-9.881-9.892-5.452 0-9.887 4.434-9.889 9.884-.001 2.225.651 3.891 1.746 5.634l-.999 3.648 3.742-.981zm11.387-5.464c-.074-.124-.272-.198-.57-.347-.297-.149-1.758-.868-2.031-.967-.272-.099-.47-.149-.669.149-.198.297-.768.967-.941 1.165-.173.198-.347.223-.644.074-.297-.149-1.255-.462-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.297-.347.446-.521.151-.172.2-.296.3-.495.099-.198.05-.372-.025-.521-.075-.148-.669-1.611-.916-2.206-.242-.579-.487-.501-.669-.51l-.57-.01c-.198 0-.52.074-.792.372s-1.04 1.016-1.04 2.479 1.065 2.876 1.213 3.074c.149.198 2.095 3.2 5.076 4.487.709.306 1.263.489 1.694.626.712.226 1.36.194 1.872.118.571-.085 1.758-.719 2.006-1.413.248-.695.248-1.29.173-1.414z"/></svg>
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
              &copy; {new Date().getFullYear()} Nawthviper Systems. Founder: Thabo Masilopana.
           </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;