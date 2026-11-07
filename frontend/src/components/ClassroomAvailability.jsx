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

export default function ClassroomAvailability() {
  const [resType, setResType] = useState('CLASSROOM'); // 'CLASSROOM' or 'LABORATORY'
  const [selectedDay, setSelectedDay] = useState('Monday');
  const [selectedPeriod, setSelectedPeriod] = useState(3);
  const [roomFilter, setRoomFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // 'ALL', 'Occupied', 'Unoccupied'
  const [resourceList, setResourceList] = useState([]);
  const [summaryData, setSummaryData] = useState({ slot: '', total: 0 });
  const [loading, setLoading] = useState(false);

  const fetchResources = async () => {
    setLoading(true);
    try {
      const url = `/api/v1/availability/resources/?day=${selectedDay}&period=${selectedPeriod}&type=${resType}`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setResourceList(data.resources || []);
        setSummaryData({
          slot: data.slot || `Period ${selectedPeriod}`,
          total: data.total_resources || (data.resources || []).length
        });
      }
    } catch (e) {
      console.error('Failed to fetch resource availability:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResources();
  }, [resType, selectedDay, selectedPeriod]);

  // Client-side filtering by specific room/lab name & status
  const filteredResources = resourceList.filter(r => {
    const matchesQuery = roomFilter
      ? (r.code.toLowerCase().includes(roomFilter.toLowerCase()) || r.name.toLowerCase().includes(roomFilter.toLowerCase()))
      : true;
    const matchesStatus = statusFilter === 'ALL' || r.status === statusFilter;
    return matchesQuery && matchesStatus;
  });

  const occupiedCount = resourceList.filter(r => r.status === 'Occupied').length;
  const unoccupiedCount = resourceList.filter(r => r.status === 'Unoccupied').length;

  return (
    <div className="space-y-6">
      {/* Header & Main Toggle */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">
            {resType === 'CLASSROOM' ? 'Classroom Availability Tracker' : 'Laboratory Availability Tracker'}
          </h2>
          <p className="text-xs text-slate-500">
            Verified room allocation covering all departments (AIML, CS, DS, CSBS, IoT, BS, MSC, MTech)
          </p>
        </div>

        {/* Classroom vs Laboratory Tab Selector */}
        <div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-2xs">
          <button
            onClick={() => { setResType('CLASSROOM'); setRoomFilter(''); }}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition ${
              resType === 'CLASSROOM' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Classrooms
          </button>
          <button
            onClick={() => { setResType('LABORATORY'); setRoomFilter(''); }}
            className={`px-4 py-1.5 rounded-md text-xs font-bold transition ${
              resType === 'LABORATORY' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Laboratories
          </button>
        </div>
      </div>

      {/* Filters Bar: Day, Period, Resource search, and Quick status pill */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
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

          {/* Specific Room/Lab Filter */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              {resType === 'CLASSROOM' ? 'Classroom Code' : 'Laboratory Code'}
            </label>
            <div className="relative">
              <input
                type="text"
                placeholder={resType === 'CLASSROOM' ? 'e.g. 619, 502, 216...' : 'e.g. 601, 604, 617...'}
                value={roomFilter}
                onChange={(e) => setRoomFilter(e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
              />
              {roomFilter && (
                <button
                  onClick={() => setRoomFilter('')}
                  className="absolute right-2.5 top-2 text-3xs text-slate-400 hover:text-slate-600 font-bold"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          {/* Availability Status Filter */}
          <div>
            <label className="block text-3xs font-bold uppercase tracking-wider text-slate-500 mb-1">
              Availability Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs font-semibold text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              <option value="ALL">All ({resourceList.length})</option>
              <option value="Occupied">Occupied ({occupiedCount})</option>
              <option value="Unoccupied">Unoccupied ({unoccupiedCount})</option>
            </select>
          </div>
        </div>

        {/* Live Status Summary Banner */}
        <div className="mt-3 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-700">{selectedDay} • {summaryData.slot}</span>
            <span className="text-3xs text-slate-400">({filteredResources.length} facilities shown)</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 text-3xs font-bold text-rose-700 bg-rose-50 border border-rose-200 px-2.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
              Occupied: {occupiedCount}
            </span>
            <span className="inline-flex items-center gap-1.5 text-3xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2.5 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              Unoccupied: {unoccupiedCount}
            </span>
          </div>
        </div>
      </div>

      {/* Grid of Classrooms / Laboratories */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm font-medium">
          Checking {resType === 'CLASSROOM' ? 'classroom' : 'laboratory'} schedules for {selectedDay}, Period {selectedPeriod}...
        </div>
      ) : filteredResources.length === 0 ? (
        <div className="p-12 text-center text-slate-400 text-sm bg-white border border-slate-200 rounded-xl">
          No {resType === 'CLASSROOM' ? 'classrooms' : 'laboratories'} matched the selected filters.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredResources.map((r) => {
            const isOccupied = r.status === 'Occupied';
            return (
              <div
                key={r.id}
                className={`p-4 rounded-xl border transition shadow-2xs flex flex-col justify-between ${
                  isOccupied
                    ? 'bg-rose-50/40 border-rose-200/90 hover:bg-rose-50/70'
                    : 'bg-emerald-50/40 border-emerald-200/90 hover:bg-emerald-50/70'
                }`}
              >
                <div>
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <h4 className="font-extrabold text-base text-slate-900 tracking-tight">{r.code}</h4>
                      <p className="text-3xs text-slate-500">{r.name}</p>
                    </div>
                    {/* Strictly Occupied or Unoccupied badge */}
                    <span
                      className={`px-2.5 py-0.5 text-3xs font-extrabold uppercase rounded-md tracking-wider shadow-2xs ${
                        isOccupied
                          ? 'bg-rose-600 text-white'
                          : 'bg-emerald-600 text-white'
                      }`}
                    >
                      {r.status}
                    </span>
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex items-center justify-between text-3xs text-slate-600">
                    <span>Capacity: <strong>{r.capacity} seats</strong></span>
                    <span className="font-semibold text-slate-500 bg-white/80 border border-slate-200 px-1.5 py-0.5 rounded text-3xs">
                      {resType === 'CLASSROOM' ? 'Classroom' : 'Lab'}
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-slate-200/60 text-xs">
                  {isOccupied && r.details ? (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-3xs font-bold text-slate-900 truncate" title={r.details.section}>
                          {r.details.section}
                        </span>
                        {r.details.department && (
                          <span className="text-3xs font-bold px-1 py-0.2 rounded bg-indigo-100 text-indigo-800">
                            {r.details.department}
                          </span>
                        )}
                      </div>
                      <p className="text-3xs text-slate-700 font-medium truncate" title={r.details.subject}>
                        {r.details.subject}
                      </p>
                      <p className="text-3xs text-slate-500 truncate" title={r.details.faculty}>
                        Faculty: {r.details.faculty || 'Unassigned'}
                      </p>
                    </div>
                  ) : (
                    <p className="text-emerald-700 font-semibold text-3xs flex items-center gap-1">
                      <span>✓</span> Unoccupied • Available for Period {selectedPeriod}
                    </p>
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
