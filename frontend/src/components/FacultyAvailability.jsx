import React, { useState, useEffect } from 'react';

const PERIODS = [
  { id: 1, label: 'Period 1 (08:15 - 09:05)', start: '08:15', end: '09:05' },
  { id: 2, label: 'Period 2 (09:05 - 09:55)', start: '09:05', end: '09:55' },
  { id: 3, label: 'Period 3 (10:10 - 11:00)', start: '10:10', end: '11:00' },
  { id: 4, label: 'Period 4 (11:00 - 11:50)', start: '11:00', end: '11:50' },
  { id: 5, label: 'Period 5 (11:50 - 12:40)', start: '11:50', end: '12:40' },
  { id: 6, label: 'Period 6 (13:40 - 14:30)', start: '13:40', end: '14:30' },
  { id: 7, label: 'Period 7 (14:30 - 15:20)', start: '14:30', end: '15:20' },
  { id: 8, label: 'Period 8 (15:20 - 16:05)', start: '15:20', end: '16:05' },
];

const DAYS = [
  { id: 'Monday', label: 'Monday' },
  { id: 'Tuesday', label: 'Tuesday' },
  { id: 'Wednesday', label: 'Wednesday' },
  { id: 'Thursday', label: 'Thursday' },
  { id: 'Friday', label: 'Friday' },
  { id: 'Saturday', label: 'Saturday' },
];

export default function FacultyAvailability() {
  const [facultyList, setFacultyList] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDept, setSelectedDept] = useState('ALL');
  const [selectedDay, setSelectedDay] = useState('Monday');
  const [selectedPeriod, setSelectedPeriod] = useState(3);
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL', 'Available', 'Occupied'
  const [summaryData, setSummaryData] = useState({ slot: '', total: 0 });
  const [loading, setLoading] = useState(false);

  // Fetch departments list for the dropdown filter
  useEffect(() => {
    fetch('/api/v1/academics/departments/')
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setDepartments(data);
        }
      })
      .catch(err => console.error('Failed to load departments:', err));
  }, []);

  const fetchAvailability = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        day: selectedDay,
        period: selectedPeriod,
      });
      if (selectedDept && selectedDept !== 'ALL') {
        params.append('department', selectedDept);
      }
      if (searchQuery.trim()) {
        params.append('name', searchQuery.trim());
      }

      const res = await fetch(`/api/v1/availability/faculty/?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        // Client-side safety deduplication by normalized name
        const rawList = data.faculty || [];
        const seenNames = new Set();
        const uniqueFaculty = [];
        for (const f of rawList) {
          const normKey = (f.name || '').toLowerCase().replace(/^(dr\.?\s*|mr\.?\s*|ms\.?\s*|mrs\.?\s*|prof\.?\s*)/, '').replace(/[^a-z0-9]/g, ' ').trim();
          if (!seenNames.has(normKey)) {
            seenNames.add(normKey);
            uniqueFaculty.push(f);
          }
        }

        setFacultyList(uniqueFaculty);
        setSummaryData({
          slot: data.slot || `Period ${selectedPeriod}`,
          total: uniqueFaculty.length
        });
      }
    } catch (e) {
      console.error('Failed to load faculty availability:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailability();
  }, [selectedDay, selectedPeriod, selectedDept, searchQuery]);

  // Status filtering (All, Available, Occupied)
  const displayedFaculty = facultyList.filter(f => {
    if (statusFilter === 'ALL') return true;
    return f.status === statusFilter;
  });

  const availableCount = facultyList.filter(f => f.status === 'Available').length;
  const occupiedCount = facultyList.filter(f => f.status === 'Occupied').length;

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Faculty Availability Tracker</h2>
          <p className="text-xs text-slate-500">
            Real-time status across all departments (AIML, CS, DS, CSBS, IoT, BS, MSC, MTech) with deduplicated instructor records
          </p>
        </div>
      </div>

      {/* Control Filters Bar: Day, Period, Department, Faculty Search, Status */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* Day Filter */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              Day
            </label>
            <select
              value={selectedDay}
              onChange={(e) => setSelectedDay(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              {DAYS.map(d => (
                <option key={d.id} value={d.id}>{d.label}</option>
              ))}
            </select>
          </div>

          {/* Period Filter */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              Academic Period
            </label>
            <select
              value={selectedPeriod}
              onChange={(e) => setSelectedPeriod(Number(e.target.value))}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              {PERIODS.map(p => (
                <option key={p.id} value={p.id}>{p.label}</option>
              ))}
            </select>
          </div>

          {/* Department Filter (Optional) */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              Department / Branch
            </label>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              <option value="ALL">All Departments & Branches</option>
              {departments.map(d => (
                <option key={d.code} value={d.code}>
                  {d.code} - {d.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              Availability Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              <option value="ALL">All ({facultyList.length})</option>
              <option value="Available">Available ({availableCount})</option>
              <option value="Occupied">Occupied ({occupiedCount})</option>
            </select>
          </div>
        </div>

        {/* Search Input by Faculty Name */}
        <div className="relative pt-1">
          <input
            type="text"
            placeholder="Search by faculty name (e.g. Dr. Srikantha Reddy, Dr. Sudha Rani, Dr. Kalpana)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-4 pr-10 py-2 bg-slate-50/70 border border-slate-300 rounded-lg text-xs placeholder-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500 shadow-2xs"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-3 text-3xs text-slate-400 hover:text-slate-600 font-bold"
            >
              Clear
            </button>
          )}
        </div>

        {/* Summary Counter Bar */}
        <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">{selectedDay} • {summaryData.slot}</span>
            <span className="text-3xs text-slate-400">({displayedFaculty.length} unique faculty shown)</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 text-3xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              Available: {availableCount}
            </span>
            <span className="inline-flex items-center gap-1.5 text-3xs font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              Occupied: {occupiedCount}
            </span>
          </div>
        </div>
      </div>

      {/* Faculty Cards Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm font-medium">
          Evaluating faculty availability schedules for {selectedDay}, Period {selectedPeriod}...
        </div>
      ) : displayedFaculty.length === 0 ? (
        <div className="p-12 text-center text-slate-400 text-sm bg-white border border-slate-200 rounded-xl">
          No faculty members matched the selected criteria.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {displayedFaculty.map((f) => {
            const isAvail = f.status === 'Available';
            return (
              <div
                key={f.id}
                className={`p-4 rounded-xl border transition shadow-2xs flex flex-col justify-between ${
                  isAvail ? 'bg-emerald-50/40 border-emerald-200/90 hover:bg-emerald-50/70' : 'bg-rose-50/40 border-rose-200/90 hover:bg-rose-50/70'
                }`}
              >
                <div>
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <h4 className="font-bold text-sm text-slate-900 leading-tight">{f.name}</h4>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-3xs text-slate-500">{f.designation || 'Faculty'}</span>
                        <span className="text-3xs font-bold px-1.5 py-0.2 rounded bg-slate-200/70 text-slate-700">
                          {f.department}
                        </span>
                        {f.is_outsourced && (
                          <span className="text-3xs font-black px-1.5 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300">
                            OUTSOURCED
                          </span>
                        )}
                      </div>
                    </div>
                    {/* Consistent Availability Indicator */}
                    <span
                      className={`px-2.5 py-0.5 text-3xs font-extrabold uppercase rounded-md tracking-wider shadow-2xs ${
                        isAvail ? 'bg-emerald-600 text-white' : 'bg-rose-600 text-white'
                      }`}
                    >
                      {f.status}
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-slate-200/60 text-xs text-slate-600">
                  {isAvail ? (
                    <p className="text-emerald-700 font-semibold text-3xs flex items-center gap-1">
                      <span>✓</span> Free for Period {selectedPeriod} • Available for scheduling
                    </p>
                  ) : (
                    <div className="space-y-1">
                      <p className="text-rose-700 font-semibold text-3xs">{f.reason}</p>
                      {f.details && (
                        <div className="flex flex-wrap items-center justify-between text-3xs text-slate-500 bg-white/70 p-1.5 rounded border border-slate-200/60">
                          <span className="font-semibold text-slate-800">{f.details.section}</span>
                          <span>Room: <strong className="text-indigo-600">{f.details.room || 'Unassigned'}</strong></span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
