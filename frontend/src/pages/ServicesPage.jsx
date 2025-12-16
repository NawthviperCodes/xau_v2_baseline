import React from 'react';

const PricingCard = ({ tier, price, duration, features, recommended, cta, badge }) => (
  <div className={`relative p-8 rounded-2xl border backdrop-blur-sm transition-all duration-300 hover:scale-105 ${
    recommended 
      ? 'bg-gradient-to-br from-indigo-600/20 via-purple-600/10 to-slate-900 border-indigo-400/50 shadow-2xl shadow-indigo-500/20' 
      : 'bg-slate-900/60 border-slate-700/50 hover:border-slate-600'
  } flex flex-col h-full`}>
    {recommended && (
      <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-xs font-bold px-6 py-2 rounded-full shadow-lg">
        ⭐ MOST POPULAR
      </div>
    )}
    
    {badge && (
      <div className="absolute top-4 right-4 bg-emerald-500/20 text-emerald-400 text-xs font-semibold px-3 py-1 rounded-full border border-emerald-500/30">
        {badge}
      </div>
    )}
    
    <div className="mb-6">
      <h3 className="text-2xl font-bold text-white mb-3">{tier}</h3>
      <div className="flex items-baseline gap-2">
        <span className="text-5xl font-bold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">{price}</span>
        <span className="text-slate-500 text-base font-medium">/{duration}</span>
      </div>
    </div>
    
    <ul className="space-y-3 mb-8 flex-grow">
      {features.map((feat, i) => (
        <li key={i} className="flex items-start text-sm text-slate-300">
          <svg className="w-5 h-5 text-emerald-400 mr-3 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span>{feat}</span>
        </li>
      ))}
    </ul>
    
    <button 
      onClick={() => window.location.href = '/contact'}
      className={`w-full py-4 rounded-xl text-center font-bold transition-all duration-300 cursor-pointer ${
        recommended 
          ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/30' 
          : 'border-2 border-slate-600 hover:border-indigo-500 hover:bg-slate-800/50 text-white'
      }`}
    >
      {cta}
    </button>
  </div>
);

const FeatureBadge = ({ icon, text }) => (
  <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-full border border-slate-700/50">
    <span className="text-indigo-400">{icon}</span>
    <span className="text-sm text-slate-300 font-medium">{text}</span>
  </div>
);

const ServicesPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950">
      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
        <div className="text-center max-w-4xl mx-auto mb-12">
          <div className="inline-block mb-6 px-4 py-2 bg-indigo-600/10 rounded-full border border-indigo-500/20">
            <span className="text-indigo-400 text-sm font-semibold">INSTITUTIONAL-GRADE TRADING</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Institutional Access.
          </h1>
          
          <p className="text-slate-400 text-xl mb-8">
            Choose the tier that fits your capital. Start small, scale fast.
          </p>
          
          <div className="flex flex-wrap justify-center gap-4">
            <FeatureBadge icon="⚡" text="Millisecond Execution" />
            <FeatureBadge icon="🎯" text="79% Win Rate" />
            <FeatureBadge icon="🔒" text="Bank-Grade Security" />
          </div>
        </div>

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto mt-16">
          <PricingCard 
            tier="Trial Access"
            price="Free"
            duration="14 Days"
            badge="RISK FREE"
            features={[
              "Full Dashboard Access",
              "XAUUSD (Gold) Only",
              "Standard Execution Speed",
              "Telegram Community Access",
              "Email Support",
              "No Credit Card Required"
            ]}
            cta="Start Free Trial"
          />
          
          <PricingCard 
            tier="Gold Tier"
            price="R200"
            duration="Month"
            recommended={true}
            features={[
              "All Assets (Indices + Forex + Crypto)",
              "Sniper Mode (79% Win Rate Logic)",
              "Direct WhatsApp & Telegram Alerts",
              "Private 1-on-1 Strategy Discussions",
              "Millisecond Execution Latency",
              "Priority Support from Thabo",
              "Exclusive Trading Signals"
            ]}
            cta="Get Gold Access"
          />
        </div>
      </div>
      
      {/* Trust Indicators */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-3 gap-6 mb-16">
          <div className="text-center p-6 bg-slate-900/30 rounded-xl border border-slate-800/50">
            <div className="text-3xl font-bold text-white mb-2">500+</div>
            <div className="text-slate-400 text-sm">Active Traders</div>
          </div>
          <div className="text-center p-6 bg-slate-900/30 rounded-xl border border-slate-800/50">
            <div className="text-3xl font-bold text-white mb-2">$2.4M+</div>
            <div className="text-slate-400 text-sm">Capital Deployed</div>
          </div>
          <div className="text-center p-6 bg-slate-900/30 rounded-xl border border-slate-800/50">
            <div className="text-3xl font-bold text-white mb-2">79%</div>
            <div className="text-slate-400 text-sm">Average Win Rate</div>
          </div>
        </div>

        {/* Enterprise CTA */}
        <div className="text-center p-12 bg-gradient-to-br from-slate-900/80 to-slate-800/50 rounded-3xl border border-slate-700/50 backdrop-blur-sm">
          <div className="max-w-2xl mx-auto">
            <h3 className="text-3xl font-bold mb-4 bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">
              Need a Custom Enterprise Solution?
            </h3>
            <p className="text-slate-400 text-lg mb-8">
              For prop firms and fund managers handling {'>'} $100k capital. Get dedicated infrastructure, custom integrations, and white-label options.
            </p>
            <button 
              onClick={() => window.location.href = '/contact'}
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-slate-900 font-bold rounded-xl hover:bg-slate-200 transition-all shadow-xl hover:shadow-2xl cursor-pointer"
            >
              Contact for Enterprise Pricing
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* FAQ or Additional Info */}
      <div className="max-w-4xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-2 gap-8">
          <div className="p-6 bg-slate-900/40 rounded-xl border border-slate-800/50">
            <h4 className="text-lg font-bold text-white mb-3">💳 Flexible Payment</h4>
            <p className="text-slate-400 text-sm">
              Cancel anytime. No long-term commitments. Month-to-month billing with instant activation.
            </p>
          </div>
          <div className="p-6 bg-slate-900/40 rounded-xl border border-slate-800/50">
            <h4 className="text-lg font-bold text-white mb-3">🔐 Secure & Private</h4>
            <p className="text-slate-400 text-sm">
              Bank-grade encryption. Your strategies and data remain completely confidential.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ServicesPage;