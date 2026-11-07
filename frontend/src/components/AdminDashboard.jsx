import React, { useState, useEffect } from 'react';
import AvailabilityInfoModal from './AvailabilityInfoModal';

export default function AdminDashboard() {
  const [activeAdminTab, setActiveAdminTab] = useState('exceptions'); // 'exceptions', 'swaps', 'substitutions', 'clashes', 'audit'
  const [showInfoModal, setShowInfoModal] = useState(false);

  // Exceptions & Audit State
  const [exceptions, setExceptions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loadingExceptions, setLoadingExceptions] = useState(true);
  const [loadingAudit, setLoadingAudit] = useState(true);

  // Common Entity Lists
  const [allFaculty, setAllFaculty] = useState([]);
  const [allResources, setAllResources] = useState([]);

  // Schedule Exception Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [exceptionType, setExceptionType] = useState('CANCEL');
  const [exceptionDate, setExceptionDate] = useState(new Date().toISOString().split('T')[0]);
  const [departmentFilter, setDepartmentFilter] = useState('ALL');
  const [entrySearch, setEntrySearch] = useState('');
  const [availableEntries, setAvailableEntries] = useState([]);
  const [loadingEntries, setLoadingEntries] = useState(false);
  const [selectedEntryId, setSelectedEntryId] = useState('');
  const [replacementFacultyId, setReplacementFacultyId] = useState('');
  const [replacementResourceId, setReplacementResourceId] = useState('');
  const [newStartTime, setNewStartTime] = useState('');
  const [newEndTime, setNewEndTime] = useState('');
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');
  const [typeFilter, setTypeFilter] = useState('ALL');

  // --- Class Swap State ---
  const [swaps, setSwaps] = useState([]);
  const [loadingSwaps, setLoadingSwaps] = useState(false);
  const [swapMode, setSwapMode] = useState('same_class'); // 'same_class' (same section period exchange) | 'cross_class'
  const [swapDate, setSwapDate] = useState(new Date().toISOString().split('T')[0]);
  const [sections, setSections] = useState([]);
  const [sameClassSectionId, setSameClassSectionId] = useState('');
  const [sameClassEntries, setSameClassEntries] = useState([]);
  const [loadingSameClassEntries, setLoadingSameClassEntries] = useState(false);
  const [sameClassSlot1, setSameClassSlot1] = useState('');
  const [sameClassSlot2, setSameClassSlot2] = useState('');
  const [swapFac1, setSwapFac1] = useState('');
  const [swapFac2, setSwapFac2] = useState('');
  const [fac1Entries, setFac1Entries] = useState([]);
  const [fac2Entries, setFac2Entries] = useState([]);
  const [selectedEntry1, setSelectedEntry1] = useState('');
  const [selectedEntry2, setSelectedEntry2] = useState('');
  const [swapReason, setSwapReason] = useState('Mutual faculty schedule exchange');
  const [swapValidation, setSwapValidation] = useState(null);
  const [validatingSwap, setValidatingSwap] = useState(false);
  const [swapError, setSwapError] = useState('');
  const [swapSuccess, setSwapSuccess] = useState('');

  // --- Substitution Engine State ---
  const [subDate, setSubDate] = useState(new Date().toISOString().split('T')[0]);
  const [subAbsentFacultyId, setSubAbsentFacultyId] = useState('');
  const [absentFacultyEntries, setAbsentFacultyEntries] = useState([]);
  const [selectedSubEntryId, setSelectedSubEntryId] = useState('');
  const [eligibleSubstitutesData, setEligibleSubstitutesData] = useState(null);
  const [loadingEligible, setLoadingEligible] = useState(false);
  const [selectedSubstituteId, setSelectedSubstituteId] = useState('');
  const [subReason, setSubReason] = useState('Faculty medical/personal leave');
  const [subError, setSubError] = useState('');
  const [subSuccess, setSubSuccess] = useState('');
  const [submittingSub, setSubmittingSub] = useState(false);

  // --- Timetable Clash Detection State ---
  const [clashes, setClashes] = useState([]);
  const [clashesSummary, setClashesSummary] = useState(null);
  const [loadingClashes, setLoadingClashes] = useState(false);
  const [scanningClashes, setScanningClashes] = useState(false);
  const [clashTypeFilter, setClashTypeFilter] = useState('ALL');
  const [clashStatusFilter, setClashStatusFilter] = useState('UNRESOLVED');
  const [resolvingClashId, setResolvingClashId] = useState(null);
  const [resolutionNotes, setResolutionNotes] = useState('');

  // Load Initial Data
  useEffect(() => {
    fetchExceptions();
    fetchAuditLogs();
    fetchFacultyAndResources();
    fetchSections();
    fetchSwaps();
    fetchClashesSummary();
    fetchClashes();
  }, []);

  const fetchSections = async () => {
    try {
      const res = await fetch('/api/v1/timetables/sections/');
      if (res.ok) setSections(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchExceptions = async () => {
    try {
      setLoadingExceptions(true);
      const res = await fetch('/api/v1/timetables/exceptions/');
      if (res.ok) setExceptions(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingExceptions(false);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      setLoadingAudit(true);
      const res = await fetch('/api/v1/audit/logs/');
      if (res.ok) setAuditLogs(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingAudit(false);
    }
  };

  const fetchFacultyAndResources = async () => {
    try {
      const [fRes, rRes] = await Promise.all([
        fetch('/api/v1/faculty/all/'),
        fetch('/api/v1/resources/all/')
      ]);
      if (fRes.ok) setAllFaculty(await fRes.json());
      if (rRes.ok) setAllResources(await rRes.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchSwaps = async () => {
    try {
      setLoadingSwaps(true);
      const res = await fetch('/api/v1/timetables/swaps/');
      if (res.ok) setSwaps(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingSwaps(false);
    }
  };

  const fetchClashesSummary = async () => {
    try {
      const res = await fetch('/api/v1/timetables/clashes/summary/');
      if (res.ok) setClashesSummary(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  const fetchClashes = async () => {
    try {
      setLoadingClashes(true);
      const params = new URLSearchParams();
      if (clashTypeFilter !== 'ALL') params.append('clash_type', clashTypeFilter);
      if (clashStatusFilter !== 'ALL') params.append('status', clashStatusFilter);

      const res = await fetch(`/api/v1/timetables/clashes/?${params.toString()}`);
      if (res.ok) setClashes(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingClashes(false);
    }
  };

  useEffect(() => {
    fetchClashes();
  }, [clashTypeFilter, clashStatusFilter]);

  const handleRunClashScan = async () => {
    setScanningClashes(true);
    try {
      const res = await fetch('/api/v1/timetables/clashes/scan/', { method: 'POST' });
      if (res.ok) {
        await Promise.all([fetchClashesSummary(), fetchClashes(), fetchAuditLogs()]);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setScanningClashes(false);
    }
  };

  const handleResolveClash = async (clashId) => {
    try {
      const res = await fetch(`/api/v1/timetables/clashes/${clashId}/resolve/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution_notes: resolutionNotes || 'Resolved by Administrator' })
      });
      if (res.ok) {
        setResolvingClashId(null);
        setResolutionNotes('');
        await Promise.all([fetchClashesSummary(), fetchClashes(), fetchAuditLogs()]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- Fetch Timetable Entries for Same-Class Swaps ---
  useEffect(() => {
    if (!sameClassSectionId || !swapDate) {
      setSameClassEntries([]);
      setSameClassSlot1('');
      setSameClassSlot2('');
      return;
    }
    setLoadingSameClassEntries(true);
    fetch(`/api/v1/timetables/entries/search/?date=${swapDate}&section_id=${sameClassSectionId}`)
      .then(r => r.json())
      .then(data => {
        setSameClassEntries(data || []);
        if (data && data.length >= 2) {
          setSameClassSlot1(data[0].id);
          setSameClassSlot2(data[1].id);
        } else if (data && data.length === 1) {
          setSameClassSlot1(data[0].id);
          setSameClassSlot2('');
        } else {
          setSameClassSlot1('');
          setSameClassSlot2('');
        }
      })
      .catch(console.error)
      .finally(() => setLoadingSameClassEntries(false));
  }, [sameClassSectionId, swapDate]);

  // --- Fetch Faculty Timetable Entries for Cross-Class Swaps ---
  useEffect(() => {
    if (!swapFac1) { setFac1Entries([]); setSelectedEntry1(''); return; }
    fetch(`/api/v1/timetables/faculty/${swapFac1}/`)
      .then(r => r.json())
      .then(d => {
        setFac1Entries(d.entries || []);
        if (d.entries && d.entries.length > 0) setSelectedEntry1(d.entries[0].id);
      })
      .catch(console.error);
  }, [swapFac1]);

  useEffect(() => {
    if (!swapFac2) { setFac2Entries([]); setSelectedEntry2(''); return; }
    fetch(`/api/v1/timetables/faculty/${swapFac2}/`)
      .then(r => r.json())
      .then(d => {
        setFac2Entries(d.entries || []);
        if (d.entries && d.entries.length > 0) setSelectedEntry2(d.entries[0].id);
      })
      .catch(console.error);
  }, [swapFac2]);

  const handleValidateSwap = async () => {
    setSwapError('');
    setSwapSuccess('');
    setSwapValidation(null);

    let payload = {};
    if (swapMode === 'same_class') {
      if (!sameClassSectionId) {
        setSwapError('Please select a class/section first.');
        return;
      }
      if (!sameClassSlot1 || !sameClassSlot2) {
        setSwapError('Please select two class sessions within the section to swap.');
        return;
      }
      if (sameClassSlot1 === sameClassSlot2) {
        setSwapError('Please choose two distinct class sessions to swap.');
        return;
      }
      const e1 = sameClassEntries.find(e => e.id === sameClassSlot1);
      const e2 = sameClassEntries.find(e => e.id === sameClassSlot2);
      if (!e1 || !e2) {
        setSwapError('Selected class slots could not be found.');
        return;
      }
      payload = {
        swap_date: swapDate,
        entry_1_id: e1.id,
        faculty_1_id: e1.faculty_id,
        entry_2_id: e2.id,
        faculty_2_id: e2.faculty_id
      };
    } else {
      if (!swapFac1 || !swapFac2 || !selectedEntry1 || !selectedEntry2) {
        setSwapError('Please select both faculty members and their respective classes to swap.');
        return;
      }
      if (swapFac1 === swapFac2) {
        setSwapError('Please select two different faculty members to perform a mutual class swap.');
        return;
      }
      payload = {
        swap_date: swapDate,
        entry_1_id: selectedEntry1,
        faculty_1_id: swapFac1,
        entry_2_id: selectedEntry2,
        faculty_2_id: swapFac2
      };
    }

    setValidatingSwap(true);
    try {
      const res = await fetch('/api/v1/timetables/swaps/validate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setSwapValidation(data);
      if (!data.is_valid) {
        setSwapError((data.errors || []).join(' | ') || 'Swap validation failed.');
      }
    } catch (e) {
      setSwapError('Failed to validate class swap.');
    } finally {
      setValidatingSwap(false);
    }
  };

  const handleApproveSwap = async () => {
    setSwapError('');
    setSwapSuccess('');
    let payload = {};
    if (swapMode === 'same_class') {
      const e1 = sameClassEntries.find(e => e.id === sameClassSlot1);
      const e2 = sameClassEntries.find(e => e.id === sameClassSlot2);
      payload = {
        swap_date: swapDate,
        entry_1_id: sameClassSlot1,
        faculty_1_id: e1?.faculty_id,
        entry_2_id: sameClassSlot2,
        faculty_2_id: e2?.faculty_id,
        reason: swapReason || 'Same-class mutual period swap',
        approved_by: 'Academic Admin'
      };
    } else {
      payload = {
        swap_date: swapDate,
        entry_1_id: selectedEntry1,
        faculty_1_id: swapFac1,
        entry_2_id: selectedEntry2,
        faculty_2_id: swapFac2,
        reason: swapReason || 'Mutual faculty schedule exchange',
        approved_by: 'Academic Admin'
      };
    }

    try {
      const res = await fetch('/api/v1/timetables/swaps/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (res.ok) {
        setSwapSuccess('Class swap approved and committed to timetable successfully!');
        setSwapValidation(null);
        fetchSwaps();
        fetchAuditLogs();
      } else {
        setSwapError(data.error || 'Failed to approve swap.');
      }
    } catch (e) {
      setSwapError('Network error approving class swap.');
    }
  };

  const handleRevokeSwap = async (swapId) => {
    if (!window.confirm('Are you sure you want to revoke this approved class swap?')) return;
    try {
      const res = await fetch(`/api/v1/timetables/swaps/${swapId}/`, { method: 'DELETE' });
      if (res.ok) {
        fetchSwaps();
        fetchAuditLogs();
      }
    } catch (e) {
      console.error(e);
    }
  };

  // --- Fetch Entries for Absent Faculty in Substitution Tab ---
  useEffect(() => {
    if (!subAbsentFacultyId) { setAbsentFacultyEntries([]); setSelectedSubEntryId(''); setEligibleSubstitutesData(null); return; }
    fetch(`/api/v1/timetables/faculty/${subAbsentFacultyId}/`)
      .then(r => r.json())
      .then(d => {
        setAbsentFacultyEntries(d.entries || []);
        if (d.entries && d.entries.length > 0) setSelectedSubEntryId(d.entries[0].id);
      })
      .catch(console.error);
  }, [subAbsentFacultyId]);

  const handleAnalyzeSubstitutes = async () => {
    if (!selectedSubEntryId) {
      setSubError('Please select a timetable session to find substitutes for.');
      return;
    }
    setSubError('');
    setSubSuccess('');
    setLoadingEligible(true);
    try {
      const res = await fetch(`/api/v1/timetables/substitutions/eligible-faculty/?entry_id=${selectedSubEntryId}&date=${subDate}`);
      if (res.ok) {
        const data = await res.json();
        setEligibleSubstitutesData(data);
      } else {
        setSubError('Failed to fetch eligible substitutes.');
      }
    } catch (e) {
      setSubError('Network error evaluating substitutes.');
    } finally {
      setLoadingEligible(false);
    }
  };

  const handleConfirmSubstitution = async () => {
    if (!selectedSubstituteId) {
      setSubError('Please select an eligible substitute faculty member.');
      return;
    }
    setSubError('');
    setSubSuccess('');
    setSubmittingSub(true);

    try {
      const res = await fetch('/api/v1/timetables/exceptions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          timetable_entry_id: selectedSubEntryId,
          exception_date: subDate,
          exception_type: 'SUBSTITUTE',
          replacement_faculty_id: selectedSubstituteId,
          reason: subReason
        })
      });
      const data = await res.json();
      if (res.ok) {
        setSubSuccess('Faculty substitution successfully assigned and confirmed!');
        fetchExceptions();
        fetchAuditLogs();
        setSelectedSubstituteId('');
      } else {
        setSubError(data.error || 'Failed to assign substitute.');
      }
    } catch (e) {
      setSubError('Error saving substitution.');
    } finally {
      setSubmittingSub(false);
    }
  };

  // --- Search Timetable Entries for Exception Modal ---
  useEffect(() => {
    if (!isModalOpen) return;
    const fetchEntries = async () => {
      setLoadingEntries(true);
      try {
        const params = new URLSearchParams();
        if (exceptionDate) params.append('date', exceptionDate);
        if (departmentFilter && departmentFilter !== 'ALL') params.append('department', departmentFilter);
        if (entrySearch) params.append('q', entrySearch);

        const res = await fetch(`/api/v1/timetables/entries/search/?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          setAvailableEntries(data);
          if (data.length > 0 && !selectedEntryId) {
            setSelectedEntryId(data[0].id);
          }
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingEntries(false);
      }
    };

    const timer = setTimeout(fetchEntries, 250);
    return () => clearTimeout(timer);
  }, [isModalOpen, exceptionDate, departmentFilter, entrySearch]);

  const handleOpenModal = () => {
    setFormError('');
    setFormSuccess('');
    setSelectedEntryId('');
    setReason('');
    setReplacementFacultyId('');
    setReplacementResourceId('');
    setNewStartTime('');
    setNewEndTime('');
    setIsModalOpen(true);
  };

  const handleCreateException = async (e) => {
    e.preventDefault();
    setFormError('');
    setFormSuccess('');

    if (!selectedEntryId) {
      setFormError('Please select a timetable class session to modify.');
      return;
    }
    if (!exceptionDate) {
      setFormError('Please specify the exception date.');
      return;
    }
    if (!reason.trim()) {
      setFormError('Please provide a specific reason for this exception.');
      return;
    }
    if (exceptionType === 'SUBSTITUTE' && !replacementFacultyId) {
      setFormError('Please select a substitute replacement faculty member.');
      return;
    }
    if (exceptionType === 'RESOURCE_CHANGE' && !replacementResourceId) {
      setFormError('Please select a replacement classroom or laboratory.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        timetable_entry_id: selectedEntryId,
        exception_date: exceptionDate,
        exception_type: exceptionType,
        reason: reason.trim(),
        replacement_faculty_id: replacementFacultyId || null,
        replacement_resource_id: replacementResourceId || null,
        new_start_time: newStartTime || null,
        new_end_time: newEndTime || null
      };

      const res = await fetch('/api/v1/timetables/exceptions/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        setFormSuccess('Schedule exception applied and logged successfully.');
        fetchExceptions();
        fetchAuditLogs();
        setTimeout(() => setIsModalOpen(false), 800);
      } else {
        setFormError(data.error || 'Failed to create schedule exception.');
      }
    } catch (err) {
      setFormError('Network error connecting to API.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteException = async (id) => {
    if (!window.confirm('Revoke this schedule exception and restore normal timetable rules?')) return;
    try {
      const res = await fetch(`/api/v1/timetables/exceptions/${id}/`, { method: 'DELETE' });
      if (res.ok) {
        fetchExceptions();
        fetchAuditLogs();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const filteredExceptions = exceptions.filter(e => {
    if (typeFilter === 'ALL') return true;
    return e.exception_type === typeFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span>Department Administration & Governance</span>
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
          </h2>
          <p className="text-xs text-slate-500">
            Timetable version control, mutual class swaps, substitution eligibility engine, and clash detection
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => { fetchExceptions(); fetchAuditLogs(); fetchSwaps(); fetchClashesSummary(); fetchClashes(); }}
            className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3 py-1.5 rounded-lg shadow-2xs transition"
          >
            ↻ Refresh All Data
          </button>
          <button
            onClick={handleOpenModal}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-1.5 rounded-lg shadow-md transition flex items-center space-x-1.5"
          >
            <span>+</span>
            <span>Create Schedule Exception</span>
          </button>
        </div>
      </div>

      {/* Top Overview Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Active Version Card */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs">
          <div className="flex justify-between items-center mb-2">
            <span className="text-3xs font-bold text-slate-500 uppercase tracking-wider">Active Baseline</span>
            <span className="bg-emerald-100 text-emerald-800 text-3xs font-bold px-2 py-0.5 rounded-full">ACTIVE</span>
          </div>
          <h3 className="text-base font-extrabold text-slate-900">Version 7.0</h3>
          <p className="text-3xs text-slate-500 mt-0.5">W.e.f 17-08-2026 • 44 Cohorts</p>
          <div className="mt-3 pt-2 border-t border-slate-100 text-3xs text-slate-600 space-y-0.5">
            <p>• 628 Active Weekly Sessions</p>
            <p>• Deduplicated Faculty Roster</p>
          </div>
        </div>

        {/* Timetable Clash Audit Card */}
        <div
          onClick={() => setActiveAdminTab('clashes')}
          className="bg-white border border-slate-200 hover:border-indigo-300 rounded-xl p-4 shadow-2xs cursor-pointer transition"
        >
          <div className="flex justify-between items-center mb-2">
            <span className="text-3xs font-bold text-slate-500 uppercase tracking-wider">Clash Engine</span>
            <span className={`text-3xs font-bold px-2 py-0.5 rounded-full ${clashesSummary?.total_unresolved > 0 ? 'bg-rose-100 text-rose-800' : 'bg-emerald-100 text-emerald-800'}`}>
              {clashesSummary?.total_unresolved || 0} AUDITED
            </span>
          </div>
          <h3 className="text-base font-extrabold text-rose-600">
            {clashesSummary ? `${clashesSummary.total_unresolved} Detected Conflicts` : 'Auditing...'}
          </h3>
          <p className="text-3xs text-slate-500 mt-0.5">Interval overlap [Start1 &lt; End2 AND Start2 &lt; End1]</p>
          <div className="mt-3 pt-2 border-t border-slate-100 text-3xs text-slate-600 space-y-0.5">
            <p>• Faculty: {clashesSummary?.faculty_clashes || 0} | Rooms: {clashesSummary?.classroom_clashes || 0}</p>
            <p>• Labs: {clashesSummary?.laboratory_clashes || 0} | Resolved: {clashesSummary?.total_resolved || 0}</p>
          </div>
        </div>

        {/* Mutual Class Swap Card */}
        <div
          onClick={() => setActiveAdminTab('swaps')}
          className="bg-white border border-slate-200 hover:border-indigo-300 rounded-xl p-4 shadow-2xs cursor-pointer transition"
        >
          <div className="flex justify-between items-center mb-2">
            <span className="text-3xs font-bold text-slate-500 uppercase tracking-wider">Class Swaps</span>
            <span className="bg-indigo-100 text-indigo-800 text-3xs font-bold px-2 py-0.5 rounded-full">
              {swaps.length} LOGGED
            </span>
          </div>
          <h3 className="text-base font-extrabold text-slate-900">Mutual Class Swaps</h3>
          <p className="text-3xs text-slate-500 mt-0.5">Teacher-to-teacher class exchange</p>
          <div className="mt-3 pt-2 border-t border-slate-100 text-3xs text-slate-600 space-y-0.5">
            <p>• Same-day or Cross-class Swaps</p>
            <p>• Zero Time/Room Overlap Guard</p>
          </div>
        </div>

        {/* Substitution Engine Card */}
        <div
          onClick={() => setActiveAdminTab('substitutions')}
          className="bg-white border border-slate-200 hover:border-indigo-300 rounded-xl p-4 shadow-2xs cursor-pointer transition"
        >
          <div className="flex justify-between items-center mb-2">
            <span className="text-3xs font-bold text-slate-500 uppercase tracking-wider">Substitution</span>
            <span className="bg-purple-100 text-purple-800 text-3xs font-bold px-2 py-0.5 rounded-full">4TH YR GUARD</span>
          </div>
          <h3 className="text-base font-extrabold text-slate-900">Leave Substitutions</h3>
          <p className="text-3xs text-slate-500 mt-0.5">Smart eligibility matching</p>
          <div className="mt-3 pt-2 border-t border-slate-100 text-3xs text-slate-600 space-y-0.5">
            <p>• Exclusively 4th-Year Strict Check</p>
            <p>• Same Subject & Class Specialists</p>
          </div>
        </div>
      </div>

      {/* Main Admin Tab Navigation Bar */}
      <div className="flex items-center space-x-2 border-b border-slate-200 overflow-x-auto pb-1 text-xs font-bold">
        {[
          { id: 'exceptions', label: `Schedule Exceptions (${exceptions.length})` },
          { id: 'swaps', label: `Faculty Class Swaps (${swaps.length})` },
          { id: 'substitutions', label: 'Faculty Substitution Management' },
          { id: 'clashes', label: `Timetable Clash Detection (${clashesSummary?.total_unresolved || 0})` },
          { id: 'audit', label: `Audit Trail & Governance (${auditLogs.length})` }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveAdminTab(tab.id)}
            className={`px-3 py-2 border-b-2 whitespace-nowrap transition ${
              activeAdminTab === tab.id
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ======================================================== */}
      {/* TAB 1: SCHEDULE EXCEPTIONS REGISTRY                      */}
      {/* ======================================================== */}
      {activeAdminTab === 'exceptions' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
          <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wider">
                Active Schedule Exceptions Registry
              </h3>
              <p className="text-xs text-slate-500">Live operational adjustments overriding baseline timetable sessions</p>
            </div>
            <div className="flex items-center space-x-1.5 overflow-x-auto text-xs">
              {['ALL', 'CANCEL', 'SUBSTITUTE', 'RESOURCE_CHANGE', 'RESCHEDULE'].map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(t)}
                  className={`px-2.5 py-1 rounded-md text-3xs font-bold transition whitespace-nowrap ${
                    typeFilter === t
                      ? 'bg-indigo-600 text-white shadow-2xs'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {t === 'ALL' ? 'ALL EXCEPTIONS' : t}
                </button>
              ))}
            </div>
          </div>

          <div className="p-4 overflow-x-auto text-xs">
            {loadingExceptions ? (
              <div className="py-8 text-center text-slate-400">Loading schedule exceptions...</div>
            ) : filteredExceptions.length === 0 ? (
              <div className="py-10 text-center space-y-2">
                <p className="text-slate-500 font-medium">No schedule exceptions logged matching this filter.</p>
                <p className="text-3xs text-slate-400">All 628 weekly classes are operating on baseline allocations.</p>
                <button
                  onClick={handleOpenModal}
                  className="mt-2 inline-flex items-center px-3 py-1.5 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg text-xs font-semibold transition"
                >
                  + Log a Schedule Exception
                </button>
              </div>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-100 text-3xs uppercase tracking-wider">
                    <th className="pb-2">Date & Slot</th>
                    <th className="pb-2">Type</th>
                    <th className="pb-2">Affected Class</th>
                    <th className="pb-2">Adjustment Details</th>
                    <th className="pb-2">Reason</th>
                    <th className="pb-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredExceptions.map((ex) => (
                    <tr key={ex.id} className="hover:bg-slate-50 transition">
                      <td className="py-3 font-semibold text-slate-800">
                        <div>{ex.exception_date}</div>
                        <div className="text-3xs text-slate-500 font-normal">{ex.start_time} – {ex.end_time}</div>
                      </td>
                      <td className="py-3">
                        <span className={`px-2 py-0.5 rounded text-3xs font-bold uppercase ${
                          ex.exception_type === 'CANCEL' ? 'bg-rose-100 text-rose-800' :
                          ex.exception_type === 'SUBSTITUTE' ? 'bg-blue-100 text-blue-800' :
                          ex.exception_type === 'RESOURCE_CHANGE' ? 'bg-amber-100 text-amber-800' :
                          'bg-purple-100 text-purple-800'
                        }`}>
                          {ex.exception_type}
                        </span>
                      </td>
                      <td className="py-3">
                        <div className="font-bold text-slate-900">{ex.section_name}</div>
                        <div className="text-3xs text-slate-500">{ex.subject_name}</div>
                      </td>
                      <td className="py-3">
                        {ex.exception_type === 'SUBSTITUTE' && (
                          <div>
                            <span className="text-slate-400 text-3xs">Sub: </span>
                            <span className="font-bold text-blue-700">{ex.replacement_faculty_name || 'Assigned'}</span>
                          </div>
                        )}
                        {ex.exception_type === 'RESOURCE_CHANGE' && (
                          <div>
                            <span className="text-slate-400 text-3xs">Room: </span>
                            <span className="font-bold text-amber-700">Room {ex.replacement_resource_code}</span>
                          </div>
                        )}
                        {ex.exception_type === 'CANCEL' && (
                          <span className="text-rose-700 text-3xs font-semibold">Relieved (Room & Faculty free)</span>
                        )}
                        {ex.exception_type === 'RESCHEDULE' && (
                          <span className="text-purple-700 text-3xs font-semibold">Shifted to {ex.new_start_time}–{ex.new_end_time}</span>
                        )}
                      </td>
                      <td className="py-3 text-slate-600 max-w-xs truncate">{ex.reason}</td>
                      <td className="py-3 text-right">
                        <button
                          onClick={() => handleDeleteException(ex.id)}
                          className="text-rose-600 hover:text-rose-800 font-semibold text-3xs px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 transition"
                        >
                          Revoke
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 2: FACULTY CLASS SWAP (Dedicated Operational Tool)  */}
      {/* ======================================================== */}
      {activeAdminTab === 'swaps' && (
        <div className="space-y-6">
          {/* Swap Configuration Form */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-5">
            <div className="border-b border-slate-200 pb-3 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
              <div>
                <h3 className="font-bold text-base text-slate-900 flex items-center gap-1.5">
                  <span>Exchange Teaching Responsibilities (Class Swap)</span>
                  <button
                    type="button"
                    onClick={() => setShowInfoModal(true)}
                    title="Dynamic Availability Information"
                    className="text-slate-400 hover:text-indigo-600 transition inline-flex items-center justify-center p-0.5 rounded-full hover:bg-slate-100"
                  >
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </button>
                </h3>
                <p className="text-xs text-slate-500">
                  Allow two teachers to exchange periods with strict timetable overlap validation
                </p>
              </div>
              <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg">
                <button
                  type="button"
                  onClick={() => { setSwapMode('same_class'); setSwapValidation(null); }}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-md transition ${
                    swapMode === 'same_class' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  🔄 Same-Class Period Swap
                </button>
                <button
                  type="button"
                  onClick={() => { setSwapMode('cross_class'); setSwapValidation(null); }}
                  className={`text-xs font-semibold px-3 py-1.5 rounded-md transition ${
                    swapMode === 'cross_class' ? 'bg-indigo-600 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  🔀 Cross-Class Swap
                </button>
              </div>
            </div>

            {swapError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs flex items-center justify-between">
                <div>⚠️ {swapError}</div>
                <button onClick={() => setSwapError('')} className="text-rose-500 hover:text-rose-700 text-3xs font-bold">DISMISS</button>
              </div>
            )}
            {swapSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs flex items-center justify-between">
                <div>✓ {swapSuccess}</div>
                <button onClick={() => setSwapSuccess('')} className="text-emerald-500 hover:text-emerald-700 text-3xs font-bold">DISMISS</button>
              </div>
            )}

            {/* MODE 1: SAME-CLASS PERIOD SWAP */}
            {swapMode === 'same_class' && (
              <div className="space-y-4">
                <div className="p-3 bg-indigo-50/70 border border-indigo-100 rounded-xl text-xs text-indigo-900">
                  <span className="font-bold">Same-Class Period Swap:</span> Two teachers teaching the same section exchange periods on a specific date.
                  For example, if Arnab Sir swaps with Gurusamy Sir on Monday morning in Section III AIML-C:
                  <strong> Gurusamy Sir teaches Deep Learning in the Computer Vision slot (08:15–09:05)</strong>, and
                  <strong> Arnab Sir teaches Computer Vision in the Deep Learning slot (09:05–09:55)</strong>.
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      1. Swap Date
                    </label>
                    <input
                      type="date"
                      value={swapDate}
                      onChange={(e) => setSwapDate(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      2. Select Class / Section
                    </label>
                    <select
                      value={sameClassSectionId}
                      onChange={(e) => { setSameClassSectionId(e.target.value); setSwapValidation(null); }}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    >
                      <option value="">-- Choose Class / Section ({sections.length} available) --</option>
                      {sections.map(s => (
                        <option key={s.id} value={s.id}>
                          {s.full_name} ({s.department_code || 'AIML'})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {loadingSameClassEntries && (
                  <div className="py-4 text-center text-xs text-slate-500 animate-pulse">
                    Loading timetable schedule for selected class...
                  </div>
                )}

                {sameClassSectionId && !loadingSameClassEntries && sameClassEntries.length === 0 && (
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl text-amber-800 text-xs">
                    No scheduled periods found for this class on {swapDate}. Please select another date or section.
                  </div>
                )}

                {sameClassEntries.length > 0 && (
                  <div className="space-y-4 pt-1">
                    <div>
                      <div className="text-3xs font-bold uppercase tracking-wider text-slate-600 mb-2">
                        Scheduled Periods on {swapDate} (Select two periods to swap):
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
                        {sameClassEntries.map(e => {
                          const isSlot1 = sameClassSlot1 === e.id;
                          const isSlot2 = sameClassSlot2 === e.id;
                          return (
                            <div
                              key={e.id}
                              className={`p-3 rounded-lg border text-xs transition cursor-pointer ${
                                isSlot1
                                  ? 'bg-blue-50 border-blue-500 ring-2 ring-blue-200'
                                  : isSlot2
                                  ? 'bg-purple-50 border-purple-500 ring-2 ring-purple-200'
                                  : 'bg-white border-slate-200 hover:border-slate-300'
                              }`}
                              onClick={() => {
                                if (isSlot1) {
                                  // deselect slot 1
                                  setSameClassSlot1('');
                                } else if (isSlot2) {
                                  // deselect slot 2
                                  setSameClassSlot2('');
                                } else if (!sameClassSlot1) {
                                  setSameClassSlot1(e.id);
                                } else if (!sameClassSlot2) {
                                  setSameClassSlot2(e.id);
                                } else {
                                  // replace slot 1
                                  setSameClassSlot1(e.id);
                                }
                                setSwapValidation(null);
                              }}
                            >
                              <div className="flex justify-between items-center mb-1">
                                <span className="font-bold text-slate-800">{e.time_label}</span>
                                {isSlot1 && (
                                  <span className="text-3xs font-bold px-1.5 py-0.5 rounded bg-blue-600 text-white">
                                    SLOT 1
                                  </span>
                                )}
                                {isSlot2 && (
                                  <span className="text-3xs font-bold px-1.5 py-0.5 rounded bg-purple-600 text-white">
                                    SLOT 2
                                  </span>
                                )}
                              </div>
                              <div className="font-bold text-indigo-700">{e.subject}</div>
                              <div className="text-slate-600 text-3xs mt-1">👤 {e.faculty}</div>
                              <div className="text-slate-400 text-3xs">📍 {e.room}</div>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                      <div>
                        <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                          Slot 1 (Period A)
                        </label>
                        <select
                          value={sameClassSlot1}
                          onChange={(e) => { setSameClassSlot1(e.target.value); setSwapValidation(null); }}
                          className="w-full border border-blue-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-blue-50/30"
                        >
                          <option value="">-- Choose Slot 1 --</option>
                          {sameClassEntries.map(e => (
                            <option key={e.id} value={e.id}>
                              {e.time_label} | {e.subject} ({e.faculty})
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                          Slot 2 (Period B to Swap With)
                        </label>
                        <select
                          value={sameClassSlot2}
                          onChange={(e) => { setSameClassSlot2(e.target.value); setSwapValidation(null); }}
                          className="w-full border border-purple-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-purple-50/30"
                        >
                          <option value="">-- Choose Slot 2 --</option>
                          {sameClassEntries.map(e => (
                            <option key={e.id} value={e.id}>
                              {e.time_label} | {e.subject} ({e.faculty})
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Interactive Visual Exchange Card */}
                    {sameClassSlot1 && sameClassSlot2 && sameClassSlot1 !== sameClassSlot2 && (() => {
                      const e1 = sameClassEntries.find(e => e.id === sameClassSlot1);
                      const e2 = sameClassEntries.find(e => e.id === sameClassSlot2);
                      if (!e1 || !e2) return null;
                      return (
                        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
                              <span>🔄</span> Exchanged Teaching Responsibilities:
                            </span>
                            <span className="text-3xs font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-700">
                              Within Section {e1.section}
                            </span>
                          </div>

                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="bg-white p-3 rounded-lg border border-blue-200 shadow-2xs">
                              <div className="flex justify-between items-center text-3xs font-bold text-blue-800 mb-1">
                                <span>PERIOD 1: {e1.time_label}</span>
                                <span>ORIGINAL: {e1.subject}</span>
                              </div>
                              <div className="text-xs text-slate-500">Will now be taught by:</div>
                              <div className="font-bold text-slate-900 text-sm mt-0.5">{e2.faculty}</div>
                              <div className="font-semibold text-indigo-600 text-xs mt-1">
                                ➡️ Subject: {e2.subject}
                              </div>
                              <div className="text-3xs text-slate-400 mt-1">Room: {e1.room}</div>
                            </div>

                            <div className="bg-white p-3 rounded-lg border border-purple-200 shadow-2xs">
                              <div className="flex justify-between items-center text-3xs font-bold text-purple-800 mb-1">
                                <span>PERIOD 2: {e2.time_label}</span>
                                <span>ORIGINAL: {e2.subject}</span>
                              </div>
                              <div className="text-xs text-slate-500">Will now be taught by:</div>
                              <div className="font-bold text-slate-900 text-sm mt-0.5">{e1.faculty}</div>
                              <div className="font-semibold text-indigo-600 text-xs mt-1">
                                ➡️ Subject: {e1.subject}
                              </div>
                              <div className="text-3xs text-slate-400 mt-1">Room: {e2.room}</div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    <div>
                      <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                        Reason for Class Swap
                      </label>
                      <input
                        type="text"
                        value={swapReason}
                        onChange={(e) => setSwapReason(e.target.value)}
                        placeholder="e.g. Mutual schedule exchange between teachers"
                        className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* MODE 2: CROSS-CLASS FACULTY SWAP */}
            {swapMode === 'cross_class' && (
              <div className="space-y-4">
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-700">
                  <span className="font-bold">Cross-Class Faculty Swap:</span> Exchange scheduled classes between two teachers across different sections or times.
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      1. Swap Date
                    </label>
                    <input
                      type="date"
                      value={swapDate}
                      onChange={(e) => setSwapDate(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      2. First Faculty Member
                    </label>
                    <select
                      value={swapFac1}
                      onChange={(e) => setSwapFac1(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    >
                      <option value="">-- Select Teacher 1 --</option>
                      {allFaculty.map(f => (
                        <option key={f.id} value={f.id}>{f.name} ({f.department})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      3. First Faculty's Scheduled Class
                    </label>
                    <select
                      value={selectedEntry1}
                      onChange={(e) => setSelectedEntry1(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                      disabled={!fac1Entries.length}
                    >
                      <option value="">-- Choose Class Session ({fac1Entries.length}) --</option>
                      {fac1Entries.map(e => (
                        <option key={e.id} value={e.id}>
                          {e.section} | {e.subject} ({e.start_time}–{e.end_time})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      4. Reason for Class Swap
                    </label>
                    <input
                      type="text"
                      value={swapReason}
                      onChange={(e) => setSwapReason(e.target.value)}
                      placeholder="e.g. Mutual academic adjustment"
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    />
                  </div>

                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      5. Second Faculty Member
                    </label>
                    <select
                      value={swapFac2}
                      onChange={(e) => setSwapFac2(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                    >
                      <option value="">-- Select Teacher 2 --</option>
                      {allFaculty.map(f => (
                        <option key={f.id} value={f.id}>{f.name} ({f.department})</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                      6. Second Faculty's Scheduled Class
                    </label>
                    <select
                      value={selectedEntry2}
                      onChange={(e) => setSelectedEntry2(e.target.value)}
                      className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                      disabled={!fac2Entries.length}
                    >
                      <option value="">-- Choose Class Session ({fac2Entries.length}) --</option>
                      {fac2Entries.map(e => (
                        <option key={e.id} value={e.id}>
                          {e.section} | {e.subject} ({e.start_time}–{e.end_time})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Swap Preview & Action Bar */}
            <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div className="text-3xs text-slate-500">
                Preserves baseline timetable. Applies exchanged teaching responsibilities on {swapDate}.
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={handleValidateSwap}
                  disabled={validatingSwap}
                  className="bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-bold px-4 py-2 rounded-lg transition"
                >
                  {validatingSwap ? 'Validating...' : 'Validate Swap'}
                </button>
                {swapValidation && swapValidation.is_valid && (
                  <button
                    type="button"
                    onClick={handleApproveSwap}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition"
                  >
                    ✓ Confirm & Save Swap
                  </button>
                )}
              </div>
            </div>

            {/* Validation Preview Card */}
            {swapValidation && swapValidation.is_valid && swapValidation.preview && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-xs space-y-2">
                <div className="font-bold text-emerald-900 flex items-center gap-1.5">
                  <span>✓</span> Swap Validation Passed: No timetable overlaps detected!
                </div>
                {swapValidation.description && (
                  <div className="text-emerald-800 font-medium bg-emerald-100/60 p-2.5 rounded-lg border border-emerald-200">
                    ℹ️ {swapValidation.description}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-emerald-950 mt-2">
                  <div className="bg-white p-2.5 rounded-lg border border-emerald-200">
                    <span className="font-bold">{swapValidation.preview.faculty_1.name}</span>
                    <div className="text-3xs text-slate-600 mt-1">Will now teach:</div>
                    <div className="font-semibold text-indigo-700">{swapValidation.preview.faculty_1.exchanged_to_teach}</div>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-emerald-200">
                    <span className="font-bold">{swapValidation.preview.faculty_2.name}</span>
                    <div className="text-3xs text-slate-600 mt-1">Will now teach:</div>
                    <div className="font-semibold text-indigo-700">{swapValidation.preview.faculty_2.exchanged_to_teach}</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Swap History Table */}
          <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
            <div className="bg-slate-50 px-6 py-4 border-b border-slate-200 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wider">
                  Approved Faculty Class Swaps History
                </h3>
                <p className="text-xs text-slate-500">Record of exchanged class teaching duties across sections</p>
              </div>
              <span className="text-3xs font-bold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded">
                Total: {swaps.length}
              </span>
            </div>

            <div className="p-4 overflow-x-auto text-xs">
              {loadingSwaps ? (
                <div className="py-8 text-center text-slate-400">Loading class swaps...</div>
              ) : swaps.length === 0 ? (
                <div className="py-8 text-center text-slate-500">
                  No mutual faculty class swaps have been logged yet.
                </div>
              ) : (
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-slate-400 border-b border-slate-100 text-3xs uppercase tracking-wider">
                      <th className="pb-2">Date & Type</th>
                      <th className="pb-2">Section</th>
                      <th className="pb-2">Exchanged Teaching Duties</th>
                      <th className="pb-2">Status</th>
                      <th className="pb-2">Reason</th>
                      <th className="pb-2 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {swaps.map(s => (
                      <tr key={s.id} className="hover:bg-slate-50">
                        <td className="py-3">
                          <div className="font-semibold text-slate-900">{s.swap_date}</div>
                          <span className={`inline-block text-3xs font-bold px-1.5 py-0.5 rounded mt-1 ${
                            s.is_same_class ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                          }`}>
                            {s.is_same_class ? 'SAME-CLASS' : 'CROSS-CLASS'}
                          </span>
                        </td>
                        <td className="py-3 font-medium text-slate-700">
                          {s.section_name}
                        </td>
                        <td className="py-3 max-w-md">
                          <div className="text-xs text-slate-800 font-medium">
                            {s.summary || `${s.faculty_1?.name} ⇄ ${s.faculty_2?.name}`}
                          </div>
                        </td>
                        <td className="py-3">
                          <span className="bg-emerald-100 text-emerald-800 font-bold text-3xs px-2 py-0.5 rounded">
                            {s.status}
                          </span>
                        </td>
                        <td className="py-3 text-slate-600">{s.reason}</td>
                        <td className="py-3 text-right">
                          <button
                            onClick={() => handleRevokeSwap(s.id)}
                            className="text-rose-600 hover:text-rose-800 text-3xs font-semibold px-2 py-1 rounded bg-rose-50 hover:bg-rose-100 transition"
                          >
                            Revoke
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 3: FACULTY SUBSTITUTION (Smart Eligibility Engine)    */}
      {/* ======================================================== */}
      {activeAdminTab === 'substitutions' && (
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs space-y-5">
            <div className="border-b border-slate-200 pb-3 flex justify-between items-center">
              <div>
                <h3 className="font-bold text-base text-slate-900 flex items-center gap-1.5">
                  <span>Faculty Substitution Management</span>
                  <button
                    type="button"
                    onClick={() => setShowInfoModal(true)}
                    title="Dynamic Availability Information"
                    className="text-slate-400 hover:text-indigo-600 transition inline-flex items-center justify-center p-0.5 rounded-full hover:bg-slate-100"
                  >
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                  </button>
                </h3>
                <p className="text-xs text-slate-500">
                  Select an absent teacher and session. The engine automatically suggests qualified substitutes while strictly enforcing the Fourth-Year Exclusivity Policy.
                </p>
              </div>
              <span className="text-3xs font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                CRITICAL RESTRICTION ACTIVE
              </span>
            </div>

            {subError && (
              <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs">
                ⚠️ {subError}
              </div>
            )}
            {subSuccess && (
              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs">
                ✓ {subSuccess}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                  1. Leave Date
                </label>
                <input
                  type="date"
                  value={subDate}
                  onChange={(e) => setSubDate(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                />
              </div>

              <div>
                <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                  2. Absent Faculty Member
                </label>
                <select
                  value={subAbsentFacultyId}
                  onChange={(e) => setSubAbsentFacultyId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                >
                  <option value="">-- Choose Absent Faculty --</option>
                  {allFaculty.map(f => (
                    <option key={f.id} value={f.id}>{f.name} ({f.department})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-3xs font-bold uppercase tracking-wider text-slate-600 mb-1">
                  3. Affected Class / Period Session
                </label>
                <select
                  value={selectedSubEntryId}
                  onChange={(e) => setSelectedSubEntryId(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 bg-white"
                  disabled={!absentFacultyEntries.length}
                >
                  <option value="">-- Choose Session ({absentFacultyEntries.length}) --</option>
                  {absentFacultyEntries.map(e => (
                    <option key={e.id} value={e.id}>
                      {e.section} | {e.subject} ({e.start_time}–{e.end_time})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={handleAnalyzeSubstitutes}
                disabled={loadingEligible || !selectedSubEntryId}
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition disabled:opacity-50"
              >
                {loadingEligible ? 'Evaluating Faculty Availability & Constraints...' : '⚡ Find Eligible Substitutes'}
              </button>
            </div>

            {/* Categorized Substitute Suggestions Display */}
            {eligibleSubstitutesData && (
              <div className="mt-4 pt-4 border-t border-slate-200 space-y-4">
                <div className="flex justify-between items-center bg-indigo-50 p-3 rounded-lg text-xs text-indigo-950 font-bold">
                  <span>
                    Affected Session: {eligibleSubstitutesData.session.section} (Year {eligibleSubstitutesData.session.year}) • {eligibleSubstitutesData.session.subject}
                  </span>
                  <span className="text-emerald-700 bg-emerald-100 px-2 py-0.5 rounded text-3xs">
                    {eligibleSubstitutesData.total_eligible} Eligible Candidates Found
                  </span>
                </div>

                {/* Category 1: Same Subject Specialists */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                    1. Same Subject Specialists ({eligibleSubstitutesData.same_subject_specialists.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {eligibleSubstitutesData.same_subject_specialists.map(f => (
                      <div
                        key={f.id}
                        onClick={() => setSelectedSubstituteId(f.id)}
                        className={`p-3 rounded-lg border text-xs cursor-pointer transition flex justify-between items-center ${
                          selectedSubstituteId === f.id
                            ? 'border-indigo-600 bg-indigo-50 ring-2 ring-indigo-400'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <div>
                          <span className="font-bold text-slate-900">{f.name}</span>
                          <span className="text-3xs text-slate-500 block">{f.department} • Teaches same subject</span>
                        </div>
                        <span className="text-3xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">
                          Recommended
                        </span>
                      </div>
                    ))}
                    {eligibleSubstitutesData.same_subject_specialists.length === 0 && (
                      <p className="text-3xs text-slate-400 italic">No free same-subject specialists during this period.</p>
                    )}
                  </div>
                </div>

                {/* Category 2: Same Class Faculty */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-blue-500"></span>
                    2. Same Class / Cohort Faculty ({eligibleSubstitutesData.same_class_faculty.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {eligibleSubstitutesData.same_class_faculty.map(f => (
                      <div
                        key={f.id}
                        onClick={() => setSelectedSubstituteId(f.id)}
                        className={`p-3 rounded-lg border text-xs cursor-pointer transition flex justify-between items-center ${
                          selectedSubstituteId === f.id
                            ? 'border-indigo-600 bg-indigo-50 ring-2 ring-indigo-400'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <div>
                          <span className="font-bold text-slate-900">{f.name}</span>
                          <span className="text-3xs text-slate-500 block">Associated with {eligibleSubstitutesData.session.section}</span>
                        </div>
                        <span className="text-3xs bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded">
                          Same Cohort
                        </span>
                      </div>
                    ))}
                    {eligibleSubstitutesData.same_class_faculty.length === 0 && (
                      <p className="text-3xs text-slate-400 italic">No other free faculty currently assigned to this cohort.</p>
                    )}
                  </div>
                </div>

                {/* Category 3: Other Eligible Faculty */}
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full bg-slate-400"></span>
                    3. Other Qualified & Available Faculty ({eligibleSubstitutesData.other_eligible_faculty.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                    {eligibleSubstitutesData.other_eligible_faculty.slice(0, 12).map(f => (
                      <div
                        key={f.id}
                        onClick={() => setSelectedSubstituteId(f.id)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer transition ${
                          selectedSubstituteId === f.id
                            ? 'border-indigo-600 bg-indigo-50 ring-2 ring-indigo-400'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <span className="font-bold text-slate-900 block truncate">{f.name}</span>
                        <span className="text-3xs text-slate-500">{f.department}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Category 4: Ineligible Faculty (Explicit Policy Reasons) */}
                <div className="space-y-2 pt-2 border-t border-slate-100">
                  <h4 className="text-xs font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1.5">
                    <span>⛔</span>
                    Ineligible Faculty Sample (Enforcing Fourth-Year Exclusivity & Time Conflict Policies)
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-44 overflow-y-auto">
                    {eligibleSubstitutesData.ineligible_faculty.filter(f => f.status === 'RESTRICTED_FOURTH_YEAR').slice(0, 4).map(f => (
                      <div key={f.id} className="p-2.5 rounded-lg border border-purple-200 bg-purple-50/60 text-xs">
                        <div className="flex justify-between items-center font-bold text-purple-900">
                          <span>{f.name}</span>
                          <span className="text-4xs bg-purple-200 text-purple-900 px-1.5 py-0.5 rounded font-black">
                            4TH YR EXCLUSIVE
                          </span>
                        </div>
                        <div className="text-3xs text-purple-800 mt-1 leading-tight">{f.message}</div>
                      </div>
                    ))}
                    {eligibleSubstitutesData.ineligible_faculty.filter(f => f.status === 'SCHEDULE_CONFLICT').slice(0, 4).map(f => (
                      <div key={f.id} className="p-2.5 rounded-lg border border-rose-200 bg-rose-50/60 text-xs">
                        <div className="flex justify-between items-center font-bold text-rose-900">
                          <span>{f.name}</span>
                          <span className="text-4xs bg-rose-200 text-rose-900 px-1.5 py-0.5 rounded font-black">
                            SCHEDULE CONFLICT
                          </span>
                        </div>
                        <div className="text-3xs text-rose-800 mt-1 leading-tight">{f.message}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Confirmation Footer */}
                {selectedSubstituteId && (
                  <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div>
                      <span className="font-bold text-emerald-950 text-xs">
                        Selected Substitute: {allFaculty.find(f => f.id === selectedSubstituteId)?.name}
                      </span>
                      <p className="text-3xs text-emerald-800 mt-0.5">
                        Will be temporarily allocated to {eligibleSubstitutesData.session.section} on {subDate}.
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={handleConfirmSubstitution}
                      disabled={submittingSub}
                      className="bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-md transition disabled:opacity-50"
                    >
                      {submittingSub ? 'Saving Substitution...' : '✓ Confirm & Save Substitution'}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 4: TIMETABLE CLASH DETECTION (Audit & Resolution)    */}
      {/* ======================================================== */}
      {activeAdminTab === 'clashes' && (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { label: 'Total Unresolved', val: clashesSummary?.total_unresolved || 0, color: 'text-rose-600', bg: 'bg-rose-50' },
              { label: 'Faculty Clashes', val: clashesSummary?.faculty_clashes || 0, color: 'text-amber-600', bg: 'bg-amber-50' },
              { label: 'Classroom Clashes', val: clashesSummary?.classroom_clashes || 0, color: 'text-indigo-600', bg: 'bg-indigo-50' },
              { label: 'Lab Clashes', val: clashesSummary?.laboratory_clashes || 0, color: 'text-purple-600', bg: 'bg-purple-50' },
              { label: 'Section Clashes', val: clashesSummary?.section_clashes || 0, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'Resolved Clashes', val: clashesSummary?.total_resolved || 0, color: 'text-emerald-600', bg: 'bg-emerald-50' }
            ].map((stat, i) => (
              <div key={i} className={`p-3 rounded-xl border border-slate-200 ${stat.bg}`}>
                <span className="text-4xs font-bold uppercase tracking-wider text-slate-500 block">{stat.label}</span>
                <span className={`text-xl font-black ${stat.color} mt-0.5 block`}>{stat.val}</span>
              </div>
            ))}
          </div>

          {/* Action Bar & Filters */}
          <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-3xs font-bold text-slate-500 uppercase">Filters:</span>
              <select
                value={clashTypeFilter}
                onChange={(e) => setClashTypeFilter(e.target.value)}
                className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-800 bg-white"
              >
                <option value="ALL">All Clash Types</option>
                <option value="FACULTY_CLASH">Faculty Clashes</option>
                <option value="CLASSROOM_CLASH">Classroom Clashes</option>
                <option value="LAB_CLASH">Laboratory Clashes</option>
                <option value="SECTION_CLASH">Section Clashes</option>
              </select>

              <select
                value={clashStatusFilter}
                onChange={(e) => setClashStatusFilter(e.target.value)}
                className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs text-slate-800 bg-white"
              >
                <option value="UNRESOLVED">Unresolved Clashes</option>
                <option value="RESOLVED">Resolved Clashes</option>
                <option value="ALL">All Statuses</option>
              </select>
            </div>

            <button
              onClick={handleRunClashScan}
              disabled={scanningClashes}
              className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold px-4 py-2 rounded-lg transition shadow-xs flex items-center space-x-1.5 disabled:opacity-50"
            >
              <span>{scanningClashes ? 'Auditing Database...' : '⚡ Run Full Timetable Scan'}</span>
            </button>
          </div>

          {/* Clash Cards Grid */}
          {loadingClashes ? (
            <div className="p-12 text-center text-slate-400 text-sm">Loading timetable conflicts...</div>
          ) : clashes.length === 0 ? (
            <div className="p-12 text-center bg-white border border-slate-200 rounded-xl text-slate-500 text-sm">
              No timetable clashes found matching the selected filters.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {clashes.map((c) => (
                <div
                  key={c.id}
                  className={`border rounded-xl p-4 shadow-2xs space-y-3 transition ${
                    c.status === 'RESOLVED' ? 'bg-slate-50 border-slate-200 opacity-75' : 'bg-white border-rose-200'
                  }`}
                >
                  <div className="flex justify-between items-start gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-3xs font-extrabold uppercase px-2 py-0.5 rounded ${
                        c.clash_type === 'FACULTY_CLASH' ? 'bg-amber-100 text-amber-900' :
                        c.clash_type === 'CLASSROOM_CLASH' ? 'bg-indigo-100 text-indigo-900' :
                        c.clash_type === 'LAB_CLASH' ? 'bg-purple-100 text-purple-900' :
                        'bg-blue-100 text-blue-900'
                      }`}>
                        {c.clash_type.replace('_', ' ')}
                      </span>
                      <span className="text-3xs font-bold text-slate-600">
                        {c.day_name} • {c.overlap_label}
                      </span>
                    </div>

                    <span className={`text-3xs font-bold px-2 py-0.5 rounded ${
                      c.status === 'RESOLVED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'
                    }`}>
                      {c.status}
                    </span>
                  </div>

                  {/* Conflicting Entries Comparison */}
                  <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                      <span className="text-4xs font-bold text-slate-400 uppercase block mb-1">Session 1</span>
                      <div className="font-bold text-slate-900 truncate">{c.entry_1.section}</div>
                      <div className="text-3xs text-slate-600 truncate">{c.entry_1.subject}</div>
                      <div className="text-3xs text-indigo-600 font-semibold mt-1">
                        Prof: {c.entry_1.faculty} • Room: {c.entry_1.room}
                      </div>
                      <div className="text-4xs text-slate-400 mt-0.5">{c.entry_1.time}</div>
                    </div>

                    <div className="bg-slate-50 p-2.5 rounded-lg border border-slate-200">
                      <span className="text-4xs font-bold text-slate-400 uppercase block mb-1">Session 2</span>
                      <div className="font-bold text-slate-900 truncate">{c.entry_2.section}</div>
                      <div className="text-3xs text-slate-600 truncate">{c.entry_2.subject}</div>
                      <div className="text-3xs text-indigo-600 font-semibold mt-1">
                        Prof: {c.entry_2.faculty} • Room: {c.entry_2.room}
                      </div>
                      <div className="text-4xs text-slate-400 mt-0.5">{c.entry_2.time}</div>
                    </div>
                  </div>

                  {/* Explanation Note */}
                  <div className="text-3xs text-rose-800 bg-rose-50/60 p-2 rounded border border-rose-200">
                    <strong>Conflict Reason:</strong> {c.explanation}
                  </div>

                  {/* Resolution Controls */}
                  {c.status === 'UNRESOLVED' && (
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      {resolvingClashId === c.id ? (
                        <div className="w-full flex items-center gap-2">
                          <input
                            type="text"
                            placeholder="Resolution notes (e.g. Swapped to Room 608)..."
                            value={resolutionNotes}
                            onChange={(e) => setResolutionNotes(e.target.value)}
                            className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
                          />
                          <button
                            onClick={() => handleResolveClash(c.id)}
                            className="bg-emerald-600 text-white text-3xs font-bold px-3 py-1.5 rounded"
                          >
                            Save
                          </button>
                          <button
                            onClick={() => setResolvingClashId(null)}
                            className="text-slate-500 text-3xs px-2"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setResolvingClashId(c.id)}
                          className="text-xs font-bold text-indigo-600 hover:text-indigo-800 ml-auto"
                        >
                          Resolve Conflict →
                        </button>
                      )}
                    </div>
                  )}

                  {c.status === 'RESOLVED' && c.resolution_notes && (
                    <div className="text-3xs text-emerald-800 bg-emerald-50 p-2 rounded">
                      <strong>Resolution:</strong> {c.resolution_notes}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ======================================================== */}
      {/* TAB 5: AUDIT LOGS & GOVERNANCE                           */}
      {/* ======================================================== */}
      {activeAdminTab === 'audit' && (
        <div className="bg-white border border-slate-200 rounded-xl shadow-2xs overflow-hidden">
          <div className="bg-slate-50 px-6 py-4 border-b border-slate-200">
            <h3 className="font-bold text-sm text-slate-800 uppercase tracking-wider">
              Immutable Governance & Operational Audit Log
            </h3>
            <p className="text-xs text-slate-500">Chronological history of timetable scans, swaps, exceptions, and resolutions</p>
          </div>
          <div className="p-4 overflow-x-auto text-xs">
            {loadingAudit ? (
              <div className="py-8 text-center text-slate-400">Loading audit trail...</div>
            ) : auditLogs.length === 0 ? (
              <div className="py-8 text-center text-slate-500">No system events logged.</div>
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="text-slate-400 border-b border-slate-100 text-3xs uppercase tracking-wider">
                    <th className="pb-2">Timestamp</th>
                    <th className="pb-2">Actor</th>
                    <th className="pb-2">Action</th>
                    <th className="pb-2">Target Entity</th>
                    <th className="pb-2">Details</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {auditLogs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50">
                      <td className="py-2.5 font-mono text-3xs text-slate-500">{log.timestamp}</td>
                      <td className="py-2.5 font-bold text-slate-800">{log.actor}</td>
                      <td className="py-2.5">
                        <span className="font-mono text-3xs px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
                          {log.action}
                        </span>
                      </td>
                      <td className="py-2.5 text-slate-700">{log.target_entity}</td>
                      <td className="py-2.5 text-slate-500 text-3xs truncate max-w-xs">
                        {log.changes ? JSON.stringify(log.changes) : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* MODAL: CREATE SCHEDULE EXCEPTION                         */}
      {/* ======================================================== */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl border border-slate-200 relative overflow-hidden max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center pb-4 border-b border-slate-100">
              <div>
                <h3 className="font-extrabold text-slate-900 text-base">Create Schedule Exception</h3>
                <p className="text-xs text-slate-500">Record a leave cancellation, substitution, or room reallocation</p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 font-bold text-lg p-1"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="mt-3 p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl">
                ⚠️ {formError}
              </div>
            )}
            {formSuccess && (
              <div className="mt-3 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl">
                ✓ {formSuccess}
              </div>
            )}

            <form onSubmit={handleCreateException} className="mt-4 space-y-4">
              {/* 1. Exception Type */}
              <div>
                <label className="block text-3xs font-extrabold text-slate-500 uppercase tracking-wider mb-2">
                  1. Exception Type
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { id: 'CANCEL', label: 'Cancellation', desc: 'Free room & faculty' },
                    { id: 'SUBSTITUTE', label: 'Substitution', desc: 'Faculty leave swap' },
                    { id: 'RESOURCE_CHANGE', label: 'Room Change', desc: 'Reallocate room/lab' },
                    { id: 'RESCHEDULE', label: 'Reschedule', desc: 'Shift time slot' }
                  ].map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => setExceptionType(item.id)}
                      className={`p-2.5 rounded-xl border text-left transition ${
                        exceptionType === item.id
                          ? 'border-indigo-600 bg-indigo-50/70 text-indigo-950 font-bold shadow-2xs ring-1 ring-indigo-500'
                          : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <span className="block text-xs">{item.label}</span>
                      <span className="block text-4xs text-slate-400 font-normal mt-0.5">{item.desc}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* 2. Date & Department Filter */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-3xs font-extrabold text-slate-500 uppercase tracking-wider mb-1">
                    2. Exception Date
                  </label>
                  <input
                    type="date"
                    value={exceptionDate}
                    onChange={(e) => setExceptionDate(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-3xs font-extrabold text-slate-500 uppercase tracking-wider mb-1">
                    Filter Branch / Dept
                  </label>
                  <select
                    value={departmentFilter}
                    onChange={(e) => setDepartmentFilter(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="ALL">All Departments</option>
                    <option value="AIML">AIML</option>
                    <option value="CS">Computer Science (CS)</option>
                    <option value="DS">Data Science (DS)</option>
                    <option value="CSBS">CSBS</option>
                    <option value="IOT">Internet of Things (IoT)</option>
                  </select>
                </div>
              </div>

              {/* 3. Class Session Selector */}
              <div>
                <label className="block text-3xs font-extrabold text-slate-500 uppercase tracking-wider mb-1">
                  3. Select Timetable Class Session to Modify
                </label>
                <div className="mb-1.5">
                  <input
                    type="text"
                    placeholder="Quick search by subject, faculty, or section code..."
                    value={entrySearch}
                    onChange={(e) => setEntrySearch(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400"
                  />
                </div>

                {loadingEntries ? (
                  <p className="text-3xs text-slate-400 italic py-2">Searching scheduled sessions...</p>
                ) : availableEntries.length === 0 ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-3xs">
                    No scheduled timetable entries found for {exceptionDate}. Make sure the date corresponds to a normal campus working day (Monday through Saturday).
                  </div>
                ) : (
                  <select
                    value={selectedEntryId}
                    onChange={(e) => setSelectedEntryId(e.target.value)}
                    className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
                    required
                  >
                    <option value="">-- Choose a Class Session ({availableEntries.length} found) --</option>
                    {availableEntries.map((entry) => (
                      <option key={entry.id} value={entry.id}>
                        {entry.display_label}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Conditional Fields based on Exception Type */}
              {exceptionType === 'SUBSTITUTE' && (
                <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl space-y-2">
                  <label className="block text-3xs font-extrabold text-blue-900 uppercase tracking-wider">
                    Replacement Substitute Faculty
                  </label>
                  <select
                    value={replacementFacultyId}
                    onChange={(e) => setReplacementFacultyId(e.target.value)}
                    className="w-full border border-blue-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    required
                  >
                    <option value="">-- Select Substitute Faculty ({allFaculty.length} available) --</option>
                    {allFaculty.map((f) => (
                      <option key={f.id} value={f.id}>
                        {f.name} ({f.department})
                      </option>
                    ))}
                  </select>
                  <p className="text-4xs text-blue-700">
                    Original teacher will be relieved to 'Available'. Substitute teacher will be marked 'Occupied' for this slot. Fourth-Year exclusive faculty restrictions will be enforced on save.
                  </p>
                </div>
              )}

              {exceptionType === 'RESOURCE_CHANGE' && (
                <div className="p-3.5 bg-amber-50/70 border border-amber-200 rounded-xl space-y-2">
                  <label className="block text-3xs font-extrabold text-amber-900 uppercase tracking-wider">
                    Replacement Classroom / Lab
                  </label>
                  <select
                    value={replacementResourceId}
                    onChange={(e) => setReplacementResourceId(e.target.value)}
                    className="w-full border border-amber-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-amber-500 bg-white"
                    required
                  >
                    <option value="">-- Select Replacement Resource ({allResources.length} available) --</option>
                    {allResources.map((r) => (
                      <option key={r.id} value={r.id}>
                        Room {r.code} - {r.name} ({r.capacity} seats, {r.type})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {exceptionType === 'RESCHEDULE' && (
                <div className="p-3.5 bg-purple-50/70 border border-purple-200 rounded-xl space-y-2">
                  <label className="block text-3xs font-extrabold text-purple-900 uppercase tracking-wider">
                    New Rescheduled Time Slot
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <span className="text-4xs text-slate-500 block mb-1">New Start Time</span>
                      <input
                        type="time"
                        value={newStartTime}
                        onChange={(e) => setNewStartTime(e.target.value)}
                        className="w-full border border-purple-300 rounded-lg px-3 py-1.5 text-xs text-slate-800"
                        required
                      />
                    </div>
                    <div>
                      <span className="text-4xs text-slate-500 block mb-1">New End Time</span>
                      <input
                        type="time"
                        value={newEndTime}
                        onChange={(e) => setNewEndTime(e.target.value)}
                        className="w-full border border-purple-300 rounded-lg px-3 py-1.5 text-xs text-slate-800"
                        required
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* 4. Reason */}
              <div>
                <label className="block text-3xs font-extrabold text-slate-500 uppercase tracking-wider mb-1">
                  4. Reason for Schedule Exception
                </label>
                <input
                  type="text"
                  placeholder="e.g. Faculty medical leave, Lab projector maintenance, Guest lecture"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>

              {/* Modal Footer */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-end space-x-2.5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-4 py-2 rounded-xl transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-5 py-2 rounded-xl shadow-md transition disabled:opacity-50"
                >
                  {submitting ? 'Applying Exception...' : 'Save & Apply Exception'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dynamic Availability Information Modal */}
      <AvailabilityInfoModal
        isOpen={showInfoModal}
        onClose={() => setShowInfoModal(false)}
      />
    </div>
  );
}
