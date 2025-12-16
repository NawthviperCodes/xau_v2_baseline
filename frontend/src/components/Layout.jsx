import React from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';

const LogoIcon = ({ className = "w-10 h-10" }) => (
  <div className={`${className} relative group overflow-hidden bg-gradient-to-br from-indigo-600 to-violet-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20`}>
    <div className="absolute inset-0 bg-white/20 group-hover:translate-x-full transition-transform duration-500 ease-out skew-x-12"></div>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-6 h-6 relative z-10">
      <path d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-2.625 6c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975V9.225c0-.54-.435-.975-.975-.975h-5.25zm0 4.5c-.54 0-.975.435-.975.975v.015c0 .54.435.975.975.975h5.25c.54 0 .975-.435.975-.975v-.015c0-.54-.435-.975-.975-.975h-5.25z" />
    </svg>
  </div>
);

const Layout = ({ user }) => {
  return (
    <div className="min-h-screen bg-[#0B0F19] text-white font-sans selection:bg-indigo-500/30 flex flex-col">
      
      {/* HEADER */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-[#0B0F19]/90 backdrop-blur-md">
        <nav className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
          <Link to="/" className="flex items-center space-x-3 cursor-pointer group">
            <LogoIcon />
            <span className="text-xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400 group-hover:to-white transition-all">
              Nawthviper
            </span>
          </Link>
          
          <div className="hidden md:flex items-center space-x-8">
            {['About', 'Services', 'Signals', 'Contact'].map((item) => (
              <NavLink 
                key={item} 
                to={`/${item.toLowerCase()}`}
                className={({ isActive }) => 
                  `text-sm font-medium transition-colors relative group ${isActive ? 'text-white' : 'text-slate-400 hover:text-white'}`
                }
              >
                {item}
                <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-indigo-500 transition-all group-hover:w-full"></span>
              </NavLink>
            ))}
          </div>

          <Link 
            to={user ? "/dashboard" : "/login"} 
            className="hidden sm:block bg-white text-[#0B0F19] hover:bg-slate-200 text-sm font-bold py-2.5 px-6 rounded-lg transition-all shadow-lg hover:shadow-white/10"
          >
            {user ? "Dashboard" : "Launch App"}
          </Link>
        </nav>
      </header>

      {/* DYNAMIC CONTENT */}
      <main className="flex-grow relative z-10 pt-20">
        <Outlet />
      </main>

      {/* FOOTER */}
      <footer className="border-t border-white/5 py-12 bg-[#05080F]">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center">
           <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <LogoIcon className="w-8 h-8 opacity-80 grayscale" />
              <span className="font-bold text-slate-500">Nawthviper Systems</span>
           </div>
           <div className="text-slate-600 text-sm">
              &copy; {new Date().getFullYear()} Thabo Gelson Masilopana. All rights reserved.
           </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;