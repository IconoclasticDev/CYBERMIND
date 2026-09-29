import React from "react";
import { Activity, FileText, ArrowRight, Inbox } from "lucide-react";
import type { UIEvent } from "../lib/adapters";
import type { Severity } from "../lib/adapters";

const SEV_BADGE: Record<Severity, string> = {
  High: "font-semibold text-[#DE5B49] bg-[#FDF2F0] border border-[#F9DCD7] px-2 py-0.5 rounded text-[11px]",
  Medium: "font-semibold text-[#E58B44] bg-[#FEF6EE] border border-[#FCE6D0] px-2 py-0.5 rounded text-[11px]",
  Low: "font-semibold text-[#5B6C82] bg-[#F1F4F8] border border-[#DCE3EC] px-2 py-0.5 rounded text-[11px]",
};

const Empty: React.FC<{ title: string; hint: string }> = ({ title, hint }) => (
  <div className="flex-1 flex flex-col items-center justify-center text-center p-6">
    <Inbox className="w-8 h-8 text-[#D4CBBF] mb-2" />
    <div className="text-xs font-bold text-[#3C4755]">{title}</div>
    <div className="text-[11px] text-[#7A8696] mt-1 max-w-[260px] leading-relaxed">{hint}</div>
  </div>
);

export const LiveEventFeed: React.FC<{ events: UIEvent[]; onSelectEvent: (e: UIEvent) => void; onViewAll: () => void }> = ({
  events, onSelectEvent, onViewAll,
}) => {
  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between overflow-hidden h-full">
      <div className="px-5 py-3.5 border-b border-[#F0ECE4] flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex items-center gap-2">
          <FileText className="w-4 h-4 text-[#DE5B49]" />
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Live Event Feed</h2>
        </div>
        <button onClick={onViewAll} className="shrink-0 flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors">
          <span>View All</span><ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>
      {events.length ? (
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
              {events.slice(0, 14).map((evt) => (
                <tr key={evt.id} onClick={() => onSelectEvent(evt)} className="hover:bg-[#FAF8F5] transition-colors cursor-pointer group">
                  <td className="py-2.5 px-4 font-mono text-[11px] text-[#717E8E] whitespace-nowrap">{evt.time}</td>
                  <td className="py-2.5 px-3 font-mono text-[11px] text-[#424D5B] font-medium whitespace-nowrap">{evt.source}</td>
                  <td className="py-2.5 px-3 text-[#222B35] font-medium group-hover:text-[#DE5B49] transition-colors truncate max-w-[180px]">
                    {evt.event}{evt.destination ? <span className="text-[#98A2AF]"> → {evt.destination}</span> : null}
                  </td>
                  <td className="py-2.5 px-4 text-right whitespace-nowrap"><span className={SEV_BADGE[evt.severity]}>{evt.severity}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty title="No telemetry yet" hint="Start a scenario in the Scenario Lab, or POST events to /api/telemetry. Events appear here the moment they are ingested." />
      )}
      <div className="px-4 py-2 border-t border-[#F0ECE4] bg-[#FAF8F5]/40 flex items-center justify-between text-[11px] text-[#8591A0]">
        <span>latest {Math.min(events.length, 14)} of stream</span>
        <span className="font-mono text-[10px]">pipeline: telemetry → state → forecast</span>
      </div>
    </div>
  );
};

export const RecentEventsTable: React.FC<{ events: UIEvent[]; onSelectEvent: (e: UIEvent) => void; onViewAll: () => void }> = ({
  events, onSelectEvent, onViewAll,
}) => (
  <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between overflow-hidden h-full">
    <div className="px-5 py-3.5 border-b border-[#F0ECE4] flex items-center justify-between">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-[#DE5B49]" />
        <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Recent Events</h2>
      </div>
      <button onClick={onViewAll} className="flex items-center gap-1 text-xs font-semibold text-[#576475] hover:text-[#DE5B49] transition-colors">
        <span>View All</span><ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
    {events.length ? (
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-[#F0ECE4] text-[11px] font-semibold text-[#8C96A3] bg-[#FAF8F5]/60">
              <th className="py-2.5 px-4 font-semibold">Time</th>
              <th className="py-2.5 px-3 font-semibold">Event</th>
              <th className="py-2.5 px-3 font-semibold">Source → Destination</th>
              <th className="py-2.5 px-4 font-semibold text-right">Severity</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F4F1EA] text-xs">
            {events.slice(0, 8).map((evt) => (
              <tr key={evt.id} onClick={() => onSelectEvent(evt)} className="hover:bg-[#FAF8F5] transition-colors cursor-pointer group">
                <td className="py-2.5 px-4 font-mono text-[11px] text-[#717E8E] whitespace-nowrap">{evt.time}</td>
                <td className="py-2.5 px-3 text-[#222B35] font-medium group-hover:text-[#DE5B49] transition-colors whitespace-nowrap">{evt.event}</td>
                <td className="py-2.5 px-3 font-mono text-[11px] text-[#556170] whitespace-nowrap truncate max-w-[170px]">
                  {evt.source} → {evt.destination ?? "—"}
                </td>
                <td className="py-2.5 px-4 text-right whitespace-nowrap"><span className={SEV_BADGE[evt.severity]}>{evt.severity}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty title="Waiting for events" hint="The timeline fills as the state engine builds observation windows." />
    )}
  </div>
);
