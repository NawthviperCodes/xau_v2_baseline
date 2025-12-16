import React from 'react';
import { motion } from 'framer-motion';

const AboutPage = () => {
  return (
    <div className="max-w-7xl mx-auto px-6 py-24">
      <div className="grid md:grid-cols-2 gap-16 items-center mb-32">
        <motion.div initial={{ opacity: 0, x: -50 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.6 }}>
          <h2 className="text-sm font-mono text-indigo-400 mb-4 uppercase tracking-widest">The Architect</h2>
          <h1 className="text-4xl md:text-5xl font-bold mb-6">Thabo Gelson Masilopana</h1>
          <div className="h-1 w-20 bg-indigo-600 mb-8"></div>
          
          <p className="text-slate-400 text-lg mb-6 leading-relaxed">
            A visionary in the algorithmic trading space, Thabo merges deep technical knowledge with financial market expertise.
          </p>
          <p className="text-slate-400 text-lg mb-8 leading-relaxed">
            As a <span className="text-white font-semibold">Computer Science Graduate</span> and specialized Software Developer, he engineered Nawthviper to solve the biggest problem in retail trading: Emotional Execution.
          </p>
          
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate-900 rounded-xl border border-white/5">
              <div className="text-2xl font-bold text-white mb-1">066 229 7338</div>
              <div className="text-xs text-slate-500 uppercase">Direct Line</div>
            </div>
            <div className="p-4 bg-slate-900 rounded-xl border border-white/5">
              <div className="text-2xl font-bold text-white mb-1">Quant Dev</div>
              <div className="text-xs text-slate-500 uppercase">Specialization</div>
            </div>
          </div>
        </motion.div>
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }} 
          animate={{ opacity: 1, scale: 1 }} 
          transition={{ duration: 0.6, delay: 0.2 }}
          className="relative"
        >
          <div className="aspect-square rounded-2xl overflow-hidden bg-gradient-to-br from-slate-800 to-black border border-white/10 relative">
             {/* Placeholder for Founder Image - Using abstract representation for now */}
             <div className="absolute inset-0 flex items-center justify-center text-slate-700">
                <span className="text-9xl font-bold opacity-10">TGM</span>
             </div>
             <div className="absolute bottom-0 left-0 right-0 p-8 bg-gradient-to-t from-black/90 to-transparent">
                <div className="text-white font-bold text-xl">Founder & CEO</div>
                <div className="text-indigo-400 text-sm">Nawthviper Systems</div>
             </div>
          </div>
        </motion.div>
      </div>

      {/* Testimonials */}
      <div className="border-t border-white/5 pt-24">
        <h3 className="text-2xl font-bold text-center mb-12">Trusted by Traders</h3>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { name: "Kagiso M.", role: "Forex Trader", text: "I've tried EA after EA. Thabo's bot is the only one that actually manages risk like a human." },
            { name: "Sarah Jenkins", role: "Investor", text: "The Sniper Mode is brilliant. Less trades, but when it shoots, it hits. My portfolio is up 40%." },
            { name: "David L.", role: "Prop Firm Trader", text: "Passed my challenge using the Gold Tier signals. The daily filter is a lifesaver." }
          ].map((t, i) => (
            <motion.div 
              key={i} 
              initial={{ opacity: 0, y: 20 }} 
              whileInView={{ opacity: 1, y: 0 }} 
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className="bg-slate-900/50 p-8 rounded-2xl border border-white/5 hover:border-indigo-500/30 transition-colors"
            >
              <div className="flex gap-1 text-yellow-500 mb-4">★★★★★</div>
              <p className="text-slate-300 mb-6">"{t.text}"</p>
              <div>
                <div className="font-bold text-white">{t.name}</div>
                <div className="text-xs text-slate-500">{t.role}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AboutPage;