import React, { useState } from 'react';
import { motion } from 'framer-motion';

// --- Reusable Components ---
const LogoIcon = ({ className = "w-10 h-10" }) => (
    <div className={`${className} bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center`}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-6 h-6">
        <path d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-2.625 6c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975V9.225c0-.54-.435-.975-.975-.975h-5.25zm0 4.5c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975v-.015c0-.54-.435-.975-.975-.975h-5.25z" />
      </svg>
    </div>
);

const FeatureIcon = ({ children }) => (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 w-12 h-12 flex items-center justify-center mb-4">
        {children}
    </div>
);

// --- Animation Variants for Framer Motion ---
const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: { staggerChildren: 0.2, delayChildren: 0.3 }
    }
};

const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
        y: 0,
        opacity: 1,
        transition: { type: 'spring', stiffness: 100 }
    }
};

// --- Main Landing Page Component ---
const LandingPage = ({ onAccessDashboard }) => {
    const [contactStatus, setContactStatus] = useState('');

    const handleContactSubmit = async (e) => {
        e.preventDefault();
        setContactStatus('Sending...');
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('http://127.0.0.1:5000/send-message', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (response.ok) {
                setContactStatus('Message sent successfully!');
                e.target.reset();
            } else {
                setContactStatus('Error: Could not send message.');
            }
        } catch (error) {
            console.error('Contact form error:', error);
            setContactStatus('Error: Could not connect to the server.');
        }
        setTimeout(() => setContactStatus(''), 5000);
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white font-sans overflow-x-hidden">
            {/* Header */}
            <header className="fixed top-0 left-0 right-0 bg-slate-900/50 backdrop-blur-xl z-50 border-b border-slate-700/50">
                <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-20">
                        <a href="#home" className="flex items-center space-x-3">
                            <LogoIcon />
                            <span className="text-xl font-bold tracking-tight">Nawthviper</span>
                        </a>
                        <div className="hidden md:flex items-center space-x-6">
                            <a href="#about" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">About Us</a>
                            <a href="#services" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Services</a>
                            <a href="#contact" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Contact</a>
                        </div>
                        <button onClick={onAccessDashboard} className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold py-2.5 px-5 rounded-lg transition-all duration-200 shadow-lg shadow-indigo-500/25">
                            Access Dashboard
                        </button>
                    </div>
                </nav>
            </header>

            <main>
                {/* Hero Section */}
                <section id="home" className="relative pt-40 pb-20 lg:pt-56 lg:pb-32 text-center">
                     <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(120,119,198,0.3),rgba(255,255,255,0))] opacity-60"></div>
                     <motion.div className="max-w-4xl mx-auto px-4" variants={containerVariants} initial="hidden" animate="visible">
                        <motion.h1 variants={itemVariants} className="text-4xl lg:text-6xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-400">
                            Elevate Your Trading Strategy. Automate with Precision.
                        </motion.h1>
                        <motion.p variants={itemVariants} className="mt-6 max-w-2xl mx-auto text-lg text-slate-300">
                            Nawthviper is a sophisticated, data-driven trading system that connects directly to your MT5 account, executing your chosen strategies with discipline and control.
                        </motion.p>
                     </motion.div>
                </section>

                {/* About Us Section */}
                <section id="about" className="py-20 sm:py-24 bg-slate-900/50">
                    <motion.div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center" initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }} variants={containerVariants}>
                        <motion.h2 variants={itemVariants} className="text-3xl lg:text-4xl font-bold tracking-tight">About Nawthviper</motion.h2>
                        <motion.p variants={itemVariants} className="mt-4 max-w-3xl mx-auto text-lg text-slate-400">
                            Founded by a team of quantitative analysts and software engineers, Nawthviper was born from a single mission: to democratize algorithmic trading. We believe that powerful, automated trading tools shouldn't be reserved for large financial institutions. Our system provides retail traders with the technology to execute strategies based on logic and data, removing the emotional element that so often leads to poor decision-making. We are committed to transparency, security, and performance.
                        </motion.p>
                    </motion.div>
                </section>

                {/* Services Section */}
                <section id="services" className="py-20 sm:py-24">
                    <motion.div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8" initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }} variants={containerVariants}>
                        <div className="text-center">
                            <motion.h2 variants={itemVariants} className="text-3xl lg:text-4xl font-bold tracking-tight">Our Services</motion.h2>
                            <motion.p variants={itemVariants} className="mt-4 text-lg text-slate-400">Everything you need to trade smarter, not harder.</motion.p>
                        </div>
                        <div className="mt-16 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                           <motion.div variants={itemVariants} className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700/50"> <FeatureIcon><svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2a4 4 0 00-4-4H3V7h2a4 4 0 004-4v-2m0 16l6-6m0 0l6 6m-6-6v12" /></svg></FeatureIcon><h3 className="font-bold text-lg">Real-Time Dashboard</h3><p className="text-sm text-slate-400 mt-2">Instantly monitor your account balance, equity, and live P/L from a single, intuitive interface.</p></motion.div>
                           <motion.div variants={itemVariants} className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700/50"><FeatureIcon><svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg></FeatureIcon><h3 className="font-bold text-lg">Advanced Bot Controls</h3><p className="text-sm text-slate-400 mt-2">Switch between tested strategies and fine-tune your risk with adjustable lot sizes.</p></motion.div>
                           <motion.div variants={itemVariants} className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700/50"><FeatureIcon><svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg></FeatureIcon><h3 className="font-bold text-lg">Robust Risk Management</h3><p className="text-sm text-slate-400 mt-2">Protect your capital by setting hard limits for maximum daily loss and total drawdown.</p></motion.div>
                           <motion.div variants={itemVariants} className="bg-slate-800/50 p-6 rounded-2xl border border-slate-700/50"><FeatureIcon><svg className="w-6 h-6 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" /></svg></FeatureIcon><h3 className="font-bold text-lg">Comprehensive Analytics</h3><p className="text-sm text-slate-400 mt-2">Visualize your equity growth and analyze past trades to refine your future strategy.</p></motion.div>
                        </div>
                    </motion.div>
                </section>

                {/* Contact Section */}
                <section id="contact" className="py-20 sm:py-24 bg-slate-900/50">
                    <motion.div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8" initial="hidden" whileInView="visible" viewport={{ once: true, amount: 0.3 }} variants={containerVariants}>
                        <div className="text-center">
                            <motion.h2 variants={itemVariants} className="text-3xl lg:text-4xl font-bold tracking-tight">Get in Touch</motion.h2>
                            <motion.p variants={itemVariants} className="mt-4 text-lg text-slate-400">Have questions? We'd love to hear from you.</motion.p>
                        </div>
                        <motion.form variants={itemVariants} onSubmit={handleContactSubmit} className="mt-12 space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <div><label htmlFor="name" className="sr-only">Name</label><input type="text" name="name" id="name" required className="block w-full rounded-lg border-0 bg-slate-700/50 py-3 px-4 text-white ring-1 ring-inset ring-slate-600/50 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition" placeholder="Your Name" /></div>
                                <div><label htmlFor="email" className="sr-only">Email</label><input type="email" name="email" id="email" required className="block w-full rounded-lg border-0 bg-slate-700/50 py-3 px-4 text-white ring-1 ring-inset ring-slate-600/50 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition" placeholder="Your Email" /></div>
                            </div>
                            <div><label htmlFor="message" className="sr-only">Message</label><textarea name="message" id="message" rows="4" required className="block w-full rounded-lg border-0 bg-slate-700/50 py-3 px-4 text-white ring-1 ring-inset ring-slate-600/50 placeholder:text-slate-500 focus:ring-2 focus:ring-inset focus:ring-indigo-500 transition" placeholder="Your Message"></textarea></div>
                            <div className="text-center">
                                <button type="submit" className="group relative inline-flex items-center justify-center rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 py-3.5 px-8 text-sm font-semibold text-white hover:from-indigo-500 hover:to-purple-500 focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 shadow-lg shadow-indigo-500/25 transition-all">Send Message</button>
                            </div>
                             {contactStatus && <p className="mt-4 text-center text-sm text-slate-400">{contactStatus}</p>}
                        </motion.form>
                    </motion.div>
                </section>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-700/50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-center text-sm text-slate-400">
                    <p>&copy; {new Date().getFullYear()} Nawthviper Systems. All rights reserved.</p>
                    <p className="mt-2">Trading involves substantial risk and is not for every investor. An investor could potentially lose all or more than the initial investment.</p>
                </div>
            </footer>
        </div>
    );
};

export default LandingPage;
