import React from 'react';

export default function AvailabilityInfoModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fadeIn">
      <div 
        className="bg-white rounded-2xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4 animate-scaleUp"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-sm">
              ℹ️
            </div>
            <h3 className="font-extrabold text-slate-900 text-base">
              Dynamic Availability Information
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 text-lg font-bold p-1 rounded-lg hover:bg-slate-100 transition"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <div className="text-sm text-slate-700 leading-relaxed bg-slate-50 border border-slate-200/80 p-4 rounded-xl">
          Faculty and classroom availability are automatically updated based on the latest timetable changes, including swaps, substitutions, cancellations, room changes, and rescheduling. Availability always represents the current assignments, not the original timetable.
        </div>

        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-sm transition"
          >
            Understood
          </button>
        </div>
      </div>
    </div>
  );
}
