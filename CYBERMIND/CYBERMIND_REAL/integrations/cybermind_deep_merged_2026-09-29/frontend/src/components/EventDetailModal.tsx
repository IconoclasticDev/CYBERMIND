import React from 'react';
import { X, Terminal, Shield, AlertTriangle, ArrowRight, Copy, Check } from 'lucide-react';
import { LiveEvent } from '../types';

interface EventDetailModalProps {
  event: LiveEvent | null;
  onClose: () => void;
  onSelectTechnique: (techId: string) => void;
}

export const EventDetailModal: React.FC<EventDetailModalProps> = ({
  event,
  onClose,
  onSelectTechnique
}) => {
  const [copied, setCopied] = React.useState(false);

  if (!event) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(event, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#DE5B49] flex items-center justify-center text-white">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-[#1C232B]">{event.event}</h3>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                  event.severity === 'High' ? 'bg-[#FDF2F0] text-[#DE5B49] border border-[#F9DCD7]' :
                  event.severity === 'Medium' ? 'bg-[#FEF6EE] text-[#E58B44] border border-[#FCE6D0]' :
                  'bg-[#F1F4F8] text-[#556375] border border-[#DCE3EC]'
                }`}>
                  {event.severity}
                </span>
              </div>
              <div className="font-mono text-xs text-[#7A8696]">{event.time} UTC · {event.source}</div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2] hover:text-[#1C232B] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          {/* Analysis Note */}
          <div className="bg-[#FAF6F0] p-3.5 rounded-xl border border-[#E9E1D5]">
            <div className="font-bold text-[#1C242E] mb-1 flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-[#DE5B49]" />
              <span>Forensic Narrative</span>
            </div>
            <p className="text-[#4E5B6B] leading-relaxed">
              {event.details || 'Anomalous process activity detected with heuristics indicative of credential staging and lateral traversal.'}
            </p>
          </div>

          {/* Key Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 border border-[#EDE7DE] rounded-xl p-3 bg-white">
            <div>
              <span className="text-[#7A8696] block text-[11px]">Source Host / IP:</span>
              <span className="font-mono font-bold text-[#202935]">{event.source}</span>
            </div>
            <div>
              <span className="text-[#7A8696] block text-[11px]">Target Destination:</span>
              <span className="font-mono font-bold text-[#202935]">{event.destination || 'Local Endpoint'}</span>
            </div>
            <div>
              <span className="text-[#7A8696] block text-[11px]">Protocol / Port:</span>
              <span className="font-mono font-bold text-[#202935]">{event.protocol || 'TCP / RPC'}</span>
            </div>
            <div>
              <span className="text-[#7A8696] block text-[11px]">User Security Context:</span>
              <span className="font-mono font-bold text-[#202935]">{event.user || 'SYSTEM'}</span>
            </div>
          </div>

          {/* Command Line / Payload */}
          {event.commandLine && (
            <div>
              <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-1.5 flex items-center justify-between">
                <span>Observed Command Execution</span>
                <span className="font-mono text-[10px]">PID: {event.pid || 4892}</span>
              </div>
              <div className="bg-[#192026] text-[#E0E6ED] p-3 rounded-xl font-mono text-[11px] break-all border border-[#2D3748]">
                {event.commandLine}
              </div>
            </div>
          )}

          {/* MITRE Mapping */}
          {event.mitreTactic && (
            <div className="flex items-center justify-between p-3 bg-white border border-[#EDE7DE] rounded-xl">
              <div>
                <span className="text-[#7A8696] text-[11px] block">MITRE ATT&amp;CK Mapping</span>
                <span className="font-bold text-[#202935]">{event.mitreTactic}</span>
              </div>
              <button
                onClick={() => {
                  const match = event.mitreTactic?.match(/T\d+(\.\d+)?/);
                  if (match) onSelectTechnique(match[0].split('.')[0]);
                  onClose();
                }}
                className="px-2.5 py-1 bg-[#FAF6F2] hover:bg-[#EFEAE2] border border-[#DFD8CC] rounded-lg text-xs font-semibold text-[#DE5B49] flex items-center gap-1"
              >
                <span>Technique Details</span>
                <ArrowRight className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs text-[#5C6A7B] hover:text-[#1C232B] font-semibold"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied JSON' : 'Copy Raw Telemetry'}</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                alert(`Alert escalated to Priority 1 Incident. Assigned to Tier 2 Responder.`);
                onClose();
              }}
              className="px-3 py-1.5 bg-[#DE5B49] hover:bg-[#C84737] text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
            >
              Escalate to Tier 2
            </button>
            <button
              onClick={onClose}
              className="px-3 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 text-[#353F4C] rounded-lg text-xs font-bold"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
