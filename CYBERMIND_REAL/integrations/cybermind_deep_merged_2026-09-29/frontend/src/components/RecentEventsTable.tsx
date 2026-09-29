import React from 'react';
import { Activity, ArrowRight } from 'lucide-react';
import { RecentEvent, Severity } from '../types';

interface RecentEventsTableProps {
  events: RecentEvent[];
  onViewAll: () => void;
  onSelectEvent: (event: RecentEvent) => void;
}

export const RecentEventsTable: React.FC<RecentEventsTableProps> = ({
  events,
  onViewAll,
  onSelectEvent
}) => {
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
            <Activity className="w-4 h-4" />
          </div>
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">
            Recent Events
          </h2>
        </div>

        <button
          onClick={onViewAll}
          className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors"
        >
          <span>View All</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#F0ECE4] text-[11px] font-semibold text-[#8C96A3] bg-[#FAF8F5]/60">
              <th className="py-2.5 px-4 font-semibold">Time</th>
              <th className="py-2.5 px-3 font-semibold">Event</th>
              <th className="py-2.5 px-3 font-semibold">Source &rarr; Destination</th>
              <th className="py-2.5 px-4 font-semibold text-right">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F4F1EA] text-xs">
            {events.map((evt) => (
              <tr
                key={evt.id}
                onClick={() => onSelectEvent(evt)}
                className="hover:bg-[#FAF8F5] transition-colors cursor-pointer group"
              >
                <td className="py-2.5 px-4 font-mono text-[11px] text-[#717E8E] whitespace-nowrap">
                  {evt.time}
                </td>
                <td className="py-2.5 px-3 text-[#222B35] font-medium group-hover:text-[#DE5B49] transition-colors whitespace-nowrap">
                  {evt.event}
                </td>
                <td className="py-2.5 px-3 font-mono text-[11px] text-[#556170] whitespace-nowrap truncate max-w-[170px]">
                  {evt.sourceDestination}
                </td>
                <td className="py-2.5 px-4 text-right whitespace-nowrap">
                  {getSeverityBadge(evt.severity)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
