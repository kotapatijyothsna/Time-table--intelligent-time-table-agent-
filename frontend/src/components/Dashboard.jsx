import React, { useState, useEffect } from 'react';
import AvailabilityInfoModal from './AvailabilityInfoModal';

export default function Dashboard({ setActiveTab, openChat, stats }) {
  const [liveData, setLiveData] = useState(null);
  const [liveLoading, setLiveLoading] = useState(true);
  const [showInfoModal, setShowInfoModal] = useState(false);

  useEffect(() => {
    fetch('/api/v1/availability/live-dashboard/')
      .then(res => res.json())
      .then(data => {
        setLiveData(data);
        setLiveLoading(false);
      })
      .catch(() => setLiveLoading(false));
  }, []);

  const cards = [
    {
      title: 'Academic Cohorts',
      value: '44 Sections',
      subtitle: 'AIML (24), CS (4), DS (5), CSBS (2), IOT (2), BS/MSC/MTech (7)',
      color: 'border-blue-500',
      action: () => setActiveTab('timetable')
    },
    {
      title: 'Teaching Faculty',
      value: '217 Members',
      subtitle: 'Deduplicated Faculty, TAs & Staff across all branches',
      color: 'border-emerald-500',
      action: () => setActiveTab('faculty')
    },
    {
      title: 'Academic Resources',
      value: '46 Facilities',
      subtitle: '23 Classrooms & 23 Computing Labs',
      color: 'border-purple-500',
      action: () => setActiveTab('resources')
    },
    {
      title: 'Active Timetable',
      value: 'Version 7',
      subtitle: 'Effective 17-08-2026 • Multi-Department',
      color: 'border-amber-500',
      action: () => setActiveTab('admin')
    }
  ];

  return (
    <div className="space-y-8">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 text-white shadow-xl relative overflow-hidden">
        <div className="relative z-10 max-w-3xl">
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 mb-4">
            Semester I • Academic Year 2026–27
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Campus Timetable & Resource Availability Engine
          </h2>
          <p className="mt-3 text-sm sm:text-base text-slate-300 leading-relaxed">
            Real-time availability tracker and scheduling platform for all departments and branches at VFSTR: CS, DS, CSBS, IoT, AIML, BS(DS), M.Sc(DS), and M.Tech.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              onClick={() => setActiveTab('faculty')}
              className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-semibold shadow-md transition"
            >
              Check Faculty Availability
            </button>
            <button
              onClick={() => setActiveTab('resources')}
              className="bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 px-4 py-2 rounded-lg text-sm font-semibold transition"
            >
              Explore Classrooms & Labs
            </button>
          </div>
        </div>
        <div className="absolute -right-12 -bottom-12 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
      </div>

      {/* Live Campus Availability Status Widget (Current Day and Time) */}
      <div className="bg-white border-2 border-indigo-500/30 rounded-2xl p-6 shadow-md relative overflow-hidden">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-4 border-b border-slate-200">
          <div className="flex items-center space-x-3">
            <span className="relative flex h-3.5 w-3.5">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${liveData?.is_break ? 'bg-amber-400' : (!liveData?.is_college_hours ? 'bg-slate-400' : 'bg-emerald-400')}`}></span>
              <span className={`relative inline-flex rounded-full h-3.5 w-3.5 ${liveData?.is_break ? 'bg-amber-500' : (!liveData?.is_college_hours ? 'bg-slate-500' : 'bg-emerald-500')}`}></span>
            </span>
            <div>
              <h3 className="font-extrabold text-slate-900 text-base sm:text-lg flex items-center gap-2">
                <span>Live Campus Availability Dashboard</span>
                <button
                  type="button"
                  onClick={() => setShowInfoModal(true)}
                  title="Dynamic Availability Information"
                  className="text-slate-400 hover:text-indigo-600 transition inline-flex items-center justify-center p-1 rounded-full hover:bg-slate-100"
                >
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </button>
                <span className={`text-3xs font-semibold px-2 py-0.5 rounded border ${liveData?.is_break ? 'bg-amber-100 text-amber-800 border-amber-300' : (!liveData?.is_college_hours ? 'bg-slate-100 text-slate-700 border-slate-300' : 'bg-emerald-100 text-emerald-800 border-emerald-300')}`}>
                  {liveData?.is_break ? liveData.break_name?.toUpperCase() : (!liveData?.is_college_hours ? 'OFF-HOURS' : 'ACTIVE PERIOD')}
                </span>
              </h3>
              <p className="text-xs text-slate-500">
                Working Hours: 08:15 AM – 04:05 PM • Breaks: Morning (09:55–10:10 AM) & Lunch (12:40–01:40 PM)
              </p>
            </div>
          </div>

          {liveData && (
            <div className={`px-3 py-1.5 rounded-lg text-xs font-bold shadow-2xs border ${liveData.is_break ? 'bg-amber-50 border-amber-300 text-amber-900' : (!liveData.is_college_hours ? 'bg-slate-100 border-slate-300 text-slate-700' : 'bg-indigo-50 border-indigo-200 text-indigo-900')}`}>
              📅 {liveData.day} • {liveData.slot_label}
            </div>
          )}
        </div>

        {liveLoading ? (
          <div className="p-8 text-center text-slate-500 text-sm">Evaluating live campus occupancy...</div>
        ) : liveData ? (
          <div className="mt-5 space-y-6">
            {/* Context Banner: Break or Off-Hours notification */}
            {liveData.is_break ? (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 flex items-center gap-3 text-amber-900 text-xs">
                <span className="text-lg">☕</span>
                <div>
                  <span className="font-bold">{liveData.break_name} in progress:</span> No scheduled classes are running. All classrooms, laboratories, and faculty members are 100% available for open use.
                </div>
              </div>
            ) : !liveData.is_college_hours ? (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 flex items-center gap-3 text-slate-700 text-xs">
                <span className="text-lg">🌙</span>
                <div>
                  <span className="font-bold">{liveData.status_message}:</span> College classes operate between 08:15 AM and 04:05 PM. All facilities are currently unoccupied and ready to use.
                </div>
              </div>
            ) : null}

            {/* Live occupancy status cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Classrooms */}
              <div
                onClick={() => setActiveTab('resources')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Classrooms</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.classrooms.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.classrooms.unoccupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Available</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.classrooms.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">In Use</span>
                  </div>
                </div>
              </div>

              {/* Laboratories */}
              <div
                onClick={() => setActiveTab('resources')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Laboratories</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.laboratories.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.laboratories.unoccupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Available</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.laboratories.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">In Use</span>
                  </div>
                </div>
              </div>

              {/* Faculty Members */}
              <div
                onClick={() => setActiveTab('faculty')}
                className="bg-slate-50 hover:bg-indigo-50/50 border border-slate-200 rounded-xl p-4 cursor-pointer transition shadow-2xs"
              >
                <div className="flex justify-between items-start">
                  <span className="text-xs font-bold text-slate-600">Faculty Members</span>
                  <span className="text-3xs font-bold bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-600">
                    Total: {liveData.faculty.total}
                  </span>
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    <span className="text-xl font-black text-emerald-700">{liveData.faculty.available}</span>
                    <span className="text-3xs font-semibold text-slate-500">Available</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                    <span className="text-xl font-black text-rose-700">{liveData.faculty.occupied}</span>
                    <span className="text-3xs font-semibold text-slate-500">Teaching</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Glance Ready-to-Use Classrooms */}
            <div className="bg-slate-50/80 rounded-xl p-4 border border-slate-200">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
                <div className="flex items-center gap-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600">
                    Ready-to-Use Classrooms Right Now
                  </h4>
                  <span className="text-3xs font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-300">
                    {liveData.classrooms.unoccupied} Available
                  </span>
                </div>
                <button
                  onClick={() => setActiveTab('resources')}
                  className="text-3xs font-bold text-indigo-600 hover:text-indigo-800"
                >
                  View All Facilities →
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {liveData.classrooms.free_list && liveData.classrooms.free_list.length > 0 ? (
                  liveData.classrooms.free_list.map((r, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 bg-white border border-emerald-300 text-emerald-800 text-xs font-mono font-bold px-2.5 py-1 rounded-md shadow-2xs hover:bg-emerald-50 transition cursor-pointer"
                      onClick={() => setActiveTab('resources')}
                    >
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                      Room {r.code} ({r.capacity} seats)
                    </span>
                  ))
                ) : (
                  <span className="text-xs text-slate-400 italic">No classrooms available during this active period.</span>
                )}
              </div>
            </div>

            {/* Ongoing Classes when period is active */}
            {liveData.is_college_hours && !liveData.is_break && liveData.ongoing_classes && liveData.ongoing_classes.length > 0 && (
              <div className="bg-slate-50/60 rounded-xl p-4 border border-slate-200">
                <div className="flex justify-between items-center mb-2.5">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
                    Running Classes in Period {liveData.current_period} ({liveData.ongoing_classes.length} active)
                  </h4>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5 max-h-48 overflow-y-auto pr-1">
                  {liveData.ongoing_classes.slice(0, 9).map((c, i) => (
                    <div key={i} className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs shadow-2xs">
                      <div className="flex justify-between items-center font-bold text-slate-900">
                        <span>Room {c.room}</span>
                        <span className="text-3xs bg-indigo-100 text-indigo-800 px-1.5 py-0.5 rounded">{c.section}</span>
                      </div>
                      <div className="text-slate-600 font-medium truncate mt-0.5">{c.subject}</div>
                      <div className="text-3xs text-slate-500 truncate mt-0.5">Prof: {c.faculty}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c, i) => (
          <div
            key={i}
            onClick={c.action}
            className={`bg-white border-l-4 ${c.color} border border-slate-200/80 rounded-xl p-5 shadow-xs hover:shadow-md transition-all cursor-pointer`}
          >
            <p className="text-xs font-bold uppercase tracking-wider text-slate-400">{c.title}</p>
            <h3 className="text-2xl font-black text-slate-900 mt-1">{c.value}</h3>
            <p className="text-3xs text-slate-500 mt-2 leading-tight">{c.subtitle}</p>
          </div>
        ))}
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Period-Wise Classroom Tracker</h4>
            <p className="text-xs text-slate-500 mt-1">
              Select specific academic periods (1 to 8) to instantly view Occupied and Unoccupied classrooms across all academic blocks.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('resources')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Track Classrooms →</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Period-Wise Laboratory Tracker</h4>
            <p className="text-xs text-slate-500 mt-1">
              Check computing laboratories and practical session allocations for any period with instant Occupied/Unoccupied detection.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('resources')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Track Laboratories →</span>
          </button>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-xs flex flex-col justify-between">
          <div>
            <h4 className="font-bold text-base text-slate-900">Deduplicated Faculty Directory</h4>
            <p className="text-xs text-slate-500 mt-1">
              Search faculty availability by department, day, and period without profile duplicates, preserving all teaching schedules.
            </p>
          </div>
          <button
            onClick={() => setActiveTab('faculty')}
            className="mt-4 text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
          >
            <span>Check Faculty →</span>
          </button>
        </div>
      </div>

      {/* Dynamic Availability Information Modal */}
      <AvailabilityInfoModal
        isOpen={showInfoModal}
        onClose={() => setShowInfoModal(false)}
      />
    </div>
  );
}