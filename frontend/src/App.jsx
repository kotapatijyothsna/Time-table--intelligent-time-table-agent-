import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import FacultyAvailability from './components/FacultyAvailability';
import ClassroomAvailability from './components/ClassroomAvailability';
import TimetableViewer from './components/TimetableViewer';
import AdminDashboard from './components/AdminDashboard';
import AIAssistantModal from './components/AIAssistantModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans text-slate-800 antialiased">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        openChat={() => setIsChatOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'dashboard' && (
          <Dashboard
            setActiveTab={setActiveTab}
            openChat={() => setIsChatOpen(true)}
          />
        )}
        {activeTab === 'faculty' && <FacultyAvailability />}
        {activeTab === 'resources' && <ClassroomAvailability />}
        {activeTab === 'timetable' && <TimetableViewer />}
        {activeTab === 'admin' && <AdminDashboard />}
      </main>

      {/* Persistent AI Assistant Trigger Pill */}
      <button
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-6 right-6 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-bold px-4 py-3 rounded-full shadow-2xl flex items-center space-x-2 transition-all scale-100 hover:scale-105 active:scale-95 z-30"
      >
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
        <span className="text-xs">Ask Campus AI</span>
      </button>

      {/* Floating AI Chat Modal */}
      <AIAssistantModal
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
      />

      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <p>© 2026 Vignan's Foundation for Science, Technology and Research (VFSTR) • Multi-Department Campus</p>
        <p className="mt-1 text-3xs text-slate-400">Smart Campus Multi-Department Timetable & Resource Scheduling Engine</p>
      </footer>
    </div>
  );
}
