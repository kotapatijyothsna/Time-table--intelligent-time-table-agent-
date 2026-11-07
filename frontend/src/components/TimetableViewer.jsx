import React, { useState, useEffect } from 'react';

export default function TimetableViewer() {
  const [viewMode, setViewMode] = useState('section'); // 'section' | 'faculty' | 'resource'
  
  // Section data
  const [sections, setSections] = useState([]);
  const [selectedSecId, setSelectedSecId] = useState('');
  
  // Faculty data
  const [facultyList, setFacultyList] = useState([]);
  const [selectedFacId, setSelectedFacId] = useState('');
  const [facultySearch, setFacultySearch] = useState('');

  // Resource data
  const [resourceList, setResourceList] = useState([]);
  const [selectedResId, setSelectedResId] = useState('');

  // Active timetable data
  const [timetableData, setTimetableData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Initial loads
  useEffect(() => {
    // Fetch sections
    fetch('/api/v1/timetables/sections/')
      .then(res => res.json())
      .then(data => {
        setSections(data);
        if (data.length > 0 && !selectedSecId) {
          setSelectedSecId(data[0].id);
        }
      });

    // Fetch faculty list
    fetch('/api/v1/faculty/all/')
      .then(res => res.json())
      .then(data => {
        setFacultyList(data);
        if (data.length > 0 && !selectedFacId) {
          setSelectedFacId(data[0].id);
        }
      });

    // Fetch resources list
    fetch('/api/v1/resources/all/')
      .then(res => res.json())
      .then(data => {
        setResourceList(data);
        if (data.length > 0 && !selectedResId) {
          setSelectedResId(data[0].id);
        }
      });
  }, []);

  // Fetch timetable when selection changes
  useEffect(() => {
    setLoading(true);
    let url = '';

    if (viewMode === 'section' && selectedSecId) {
      url = `/api/v1/timetables/sections/${selectedSecId}/`;
    } else if (viewMode === 'faculty' && selectedFacId) {
      url = `/api/v1/timetables/faculty/${selectedFacId}/`;
    } else if (viewMode === 'resource' && selectedResId) {
      url = `/api/v1/timetables/resources/${selectedResId}/`;
    }

    if (!url) {
      setLoading(false);
      return;
    }

    fetch(url)
      .then(res => res.json())
      .then(data => {
        setTimetableData(data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, [viewMode, selectedSecId, selectedFacId, selectedResId]);

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

  // Filtered faculty for dropdown
  const filteredFaculty = facultyList.filter(f =>
    facultySearch ? f.name.toLowerCase().includes(facultySearch.toLowerCase()) : true
  );

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Academic Timetable Matrix</h2>
          <p className="text-xs text-slate-500">
            Multi-view weekly timetable engine: inspect schedule by Cohort, Faculty Member, or Room/Laboratory.
          </p>
        </div>

        {/* View Mode Switcher */}
        <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1 text-xs">
          <button
            onClick={() => setViewMode('section')}
            className={`px-3 py-1.5 rounded-md font-bold transition ${
              viewMode === 'section'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            🎓 Cohort / Section
          </button>
          <button
            onClick={() => setViewMode('faculty')}
            className={`px-3 py-1.5 rounded-md font-bold transition ${
              viewMode === 'faculty'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            👨‍🏫 Faculty-Wise
          </button>
          <button
            onClick={() => setViewMode('resource')}
            className={`px-3 py-1.5 rounded-md font-bold transition ${
              viewMode === 'resource'
                ? 'bg-white text-indigo-700 shadow-2xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            🏫 Room / Lab-Wise
          </button>
        </div>
      </div>

      {/* Selectors Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-wrap items-center gap-4">
        {viewMode === 'section' && (
          <div className="flex items-center space-x-2">
            <label className="text-xs font-semibold text-slate-600">Select Cohort:</label>
            <select
              value={selectedSecId}
              onChange={(e) => setSelectedSecId(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 bg-white font-bold focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              {sections.map(s => (
                <option key={s.id} value={s.id}>{s.full_name} ({s.department})</option>
              ))}
            </select>
          </div>
        )}

        {viewMode === 'faculty' && (
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600">Search Faculty:</label>
              <input
                type="text"
                placeholder="Filter by name..."
                value={facultySearch}
                onChange={(e) => setFacultySearch(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 bg-white focus:ring-2 focus:ring-indigo-500 shadow-2xs w-44"
              />
            </div>
            <div className="flex items-center space-x-2">
              <label className="text-xs font-semibold text-slate-600">Instructor:</label>
              <select
                value={selectedFacId}
                onChange={(e) => setSelectedFacId(e.target.value)}
                className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 bg-white font-bold focus:ring-2 focus:ring-indigo-500 shadow-2xs max-w-xs"
              >
                {filteredFaculty.map(f => (
                  <option key={f.id} value={f.id}>{f.name} ({f.department || 'AIML'})</option>
                ))}
              </select>
            </div>
          </div>
        )}

        {viewMode === 'resource' && (
          <div className="flex items-center space-x-2">
            <label className="text-xs font-semibold text-slate-600">Select Facility:</label>
            <select
              value={selectedResId}
              onChange={(e) => setSelectedResId(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 bg-white font-bold focus:ring-2 focus:ring-indigo-500 shadow-2xs"
            >
              <optgroup label="Classrooms">
                {resourceList.filter(r => r.type === 'CLASSROOM').map(r => (
                  <option key={r.id} value={r.id}>Room {r.code} ({r.capacity} seats)</option>
                ))}
              </optgroup>
              <optgroup label="Laboratories">
                {resourceList.filter(r => r.type === 'LABORATORY').map(r => (
                  <option key={r.id} value={r.id}>Lab {r.code} - {r.name} ({r.capacity} seats)</option>
                ))}
              </optgroup>
            </select>
          </div>
        )}
      </div>

      {/* Timetable Display Grid */}
      {loading ? (
        <div className="p-12 text-center text-slate-500 text-sm">Loading weekly schedule grid...</div>
      ) : timetableData ? (
        <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
          <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex flex-wrap justify-between items-center gap-2">
            <div className="flex items-center gap-3">
              <h3 className="font-extrabold text-sm text-slate-800 tracking-wide">
                {viewMode === 'section' && `${timetableData.section} Weekly Timetable`}
                {viewMode === 'faculty' && `${timetableData.faculty} (${timetableData.designation}) — Weekly Teaching Schedule`}
                {viewMode === 'resource' && `${timetableData.type === 'CLASSROOM' ? 'Classroom' : 'Laboratory'} ${timetableData.resource} — Weekly Allocation Grid`}
              </h3>
              <span className="text-3xs font-medium text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
                {timetableData.entries.length} scheduled sessions
              </span>
            </div>
            <span className="text-3xs font-semibold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">
              Active Version {timetableData.version}
            </span>
          </div>

          <div className="p-4 overflow-x-auto">
            <div className="space-y-4">
              {days.map((dayName, dayIdx) => {
                const dayEntries = timetableData.entries.filter(e => e.day_of_week === dayIdx);
                return (
                  <div key={dayIdx} className="border border-slate-200/80 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-xs font-bold text-indigo-900 uppercase tracking-wider">
                        {dayName}
                      </h4>
                      <span className="text-3xs text-slate-400">
                        {dayEntries.length} {dayEntries.length === 1 ? 'class' : 'classes'}
                      </span>
                    </div>

                    {dayEntries.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No scheduled sessions</p>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
                        {dayEntries.map(e => (
                          <div
                            key={e.id}
                            className={`p-3 rounded-lg border text-xs transition shadow-2xs ${
                              e.is_multi_period
                                ? 'bg-indigo-50/40 border-indigo-200 hover:bg-indigo-50/60'
                                : 'bg-slate-50 hover:bg-slate-100/80 border-slate-200'
                            }`}
                          >
                            <div className="flex justify-between items-center text-3xs font-mono mb-1.5">
                              <span className="font-semibold text-slate-700">{e.start_time.slice(0,5)} - {e.end_time.slice(0,5)}</span>
                              <div className="flex items-center gap-1">
                                {e.is_multi_period && (
                                  <span className="font-bold text-amber-800 bg-amber-100/90 border border-amber-300 px-1.5 py-0.2 rounded text-3xs">
                                    2 Periods
                                  </span>
                                )}
                                <span className={`font-bold px-1.5 py-0.5 rounded ${
                                  e.session_type === 'PRACTICAL'
                                    ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                                    : 'text-indigo-700 bg-indigo-50 border border-indigo-200'
                                }`}>
                                  {e.session_type}
                                </span>
                              </div>
                            </div>

                            <p className="font-bold text-slate-900 text-xs leading-snug line-clamp-2" title={e.subject}>
                              {e.subject}
                            </p>

                            <div className="mt-2 pt-2 border-t border-slate-200/60 flex flex-col gap-1 text-3xs">
                              {/* Display Cohort if in faculty or resource mode */}
                              {viewMode !== 'section' && (
                                <div className="flex items-center justify-between">
                                  <span className="text-slate-400">Cohort:</span>
                                  <span className="font-bold text-indigo-700 bg-indigo-50/80 px-1 rounded">
                                    {e.section || 'N/A'}
                                  </span>
                                </div>
                              )}

                              {/* Display Faculty if in section or resource mode */}
                              {viewMode !== 'faculty' && (
                                <div className="flex items-start justify-between gap-1">
                                  <span className="text-slate-400 shrink-0">Faculty:</span>
                                  <span className={`font-medium text-right truncate ${
                                    e.faculty === 'Unassigned' ? 'text-slate-400 italic' : 'text-slate-800 font-semibold'
                                  }`} title={e.faculty}>
                                    {e.faculty}
                                  </span>
                                </div>
                              )}

                              {/* Display Room if in section or faculty mode */}
                              {viewMode !== 'resource' && (
                                <div className="flex items-center justify-between">
                                  <span className="text-slate-400">Room:</span>
                                  <span className={`font-mono font-semibold ${
                                    e.room === 'Unassigned' ? 'text-slate-400 italic' : 'text-indigo-700 bg-indigo-50/80 px-1 rounded'
                                  }`}>
                                    {e.room}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}