import React from 'react';

export default function Navbar({ activeTab, setActiveTab, openChat }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'faculty', label: 'Faculty Availability' },
    { id: 'resources', label: 'Classrooms & Labs' },
    { id: 'timetable', label: 'Timetable Matrix' },
    { id: 'admin', label: 'Admin Portal' },
  ];

  return (
    <header className="bg-slate-900 border-b border-slate-800 text-white sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('dashboard')}>
          <div className="h-10 w-10 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-xl shadow-md">
            VF
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight tracking-wide">Smart Campus</h1>
            <p className="text-xs text-indigo-400 font-medium">VFSTR • Multi-Department Campus Tracker</p>
          </div>
        </div>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex space-x-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === item.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* AI Assistant Quick Trigger */}
        <div className="flex items-center space-x-2">
          <button
            onClick={openChat}
            className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white px-3.5 py-1.5 rounded-full text-xs font-semibold shadow-md transition-all scale-100 hover:scale-105 active:scale-95"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>Ask Campus AI</span>
          </button>
        </div>
      </div>
    </header>
  );
}
