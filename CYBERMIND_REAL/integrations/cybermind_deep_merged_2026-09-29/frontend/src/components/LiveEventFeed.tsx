import React, { useState } from 'react';
import { FileText, ArrowRight, Pause, Play, Filter } from 'lucide-react';
import { LiveEvent, Severity } from '../types';

interface LiveEventFeedProps {
  events: LiveEvent[];
  onSelectEvent: (event: LiveEvent) => void;
  onViewAll: () => void;
}

export const LiveEventFeed: React.FC<LiveEventFeedProps> = ({
  events,
  onSelectEvent,
  onViewAll
}) => {
  const [isLiveStreaming, setIsLiveStreaming] = useState<boolean>(true);
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');

  const filteredEvents = events.filter((e) => {
    if (selectedSeverity === 'all') return true;
    return e.severity.toLowerCase() === selectedSeverity.toLowerCase();
  });

  const getSeverityBadge = (severity: Severity) => {
    switch (severity) {
      case 'High':
        return (
          <span className="font-semibold text-[#DE5B49] bg-[#FDF2F0] border border-[#F9DCD7] px-2 py-0.5 rounded text-[11px]">
            High
          </span>
        );
      case 'Medium':
        return (
          <span className="font-semibold text-[#E58B44] bg-[#FEF6EE] border border-[#FCE6D0] px-2 py-0.5 rounded text-[11px]">
            Medium
          </span>
        );
      case 'Low':
      default:
        return (
          <span className="font-semibold text-[#5B6C82] bg-[#F1F4F8] border border-[#DCE3EC] px-2 py-0.5 rounded text-[11px]">
            Low
          </span>
        );
    }
  };

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between overflow-hidden h-full">
      {/* Header */}
      <div className="px-5 py-3.5 border-b border-[#F0ECE4] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-[#DE5B49]">
            <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">
            Live Event Feed
          </h2>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLiveStreaming(!isLiveStreaming)}
            className="flex items-center gap-1.5 text-xs text-[#2EAA58] font-semibold hover:opacity-80 transition-opacity"
            title={isLiveStreaming ? "Stream live (click to pause)" : "Stream paused (click to resume)"}
          >
            <span className={`w-2 h-2 rounded-full ${isLiveStreaming ? 'bg-[#2EAA58] animate-pulse' : 'bg-stone-400'}`} />
            <span>{isLiveStreaming ? 'Live' : 'Paused'}</span>
          </button>

          <button
            onClick={onViewAll}
            className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors"
          >
            <span>View All</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Events Table */}
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#F0ECE4] text-[11px] font-semibold text-[#8C96A3] bg-[#FAF8F5]/60">
              <th className="py-2.5 px-4 font-semibold">Time</th>
              <th className="py-2.5 px-3 font-semibold">Source</th>
              <th className="py-2.5 px-3 font-semibold">Event</th>
              <th className="py-2.5 px-4 font-semibold text-right">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F4F1EA] text-xs">
            {filteredEvents.map((evt) => (
              <tr
                key={evt.id}
                onClick={() => onSelectEvent(evt)}
                className="hover:bg-[#FAF8F5] transition-colors cursor-pointer group"
              >
                <td className="py-2.5 px-4 font-mono text-[11px] text-[#717E8E] whitespace-nowrap">
                  {evt.time}
                </td>
                <td className="py-2.5 px-3 font-mono text-[11px] text-[#424D5B] font-medium whitespace-nowrap">
                  {evt.source}
                </td>
                <td className="py-2.5 px-3 text-[#222B35] font-medium group-hover:text-[#DE5B49] transition-colors truncate max-w-[180px]">
                  {evt.event}
                </td>
                <td className="py-2.5 px-4 text-right whitespace-nowrap">
                  {getSeverityBadge(evt.severity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer subtle counter */}
      <div className="px-4 py-2 border-t border-[#F0ECE4] bg-[#FAF8F5]/40 flex items-center justify-between text-[11px] text-[#8591A0]">
        <span>Showing latest {filteredEvents.length} events</span>
        <span className="font-mono text-[10px]">Buffer: 500 / 500 EPS</span>
      </div>
    </div>
  );
};
