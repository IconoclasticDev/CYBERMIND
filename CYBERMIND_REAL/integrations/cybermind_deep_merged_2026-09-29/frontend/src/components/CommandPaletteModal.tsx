import React, { useState, useEffect } from 'react';
import { Search, X, Shield, Terminal, Server, FileText, ArrowRight, Zap, Database } from 'lucide-react';
import { NetworkNode, LiveEvent } from '../types';

interface CommandPaletteModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodes: NetworkNode[];
  events: LiveEvent[];
  onSelectNode: (node: NetworkNode) => void;
  onSelectEvent: (event: LiveEvent) => void;
  onSelectTechnique: (techId: string) => void;
}

export const CommandPaletteModal: React.FC<CommandPaletteModalProps> = ({
  isOpen,
  onClose,
  nodes,
  events,
  onSelectNode,
  onSelectEvent,
  onSelectTechnique
}) => {
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (isOpen) {
      setQuery('');
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredNodes = nodes.filter(
    (n) =>
      n.name.toLowerCase().includes(query.toLowerCase()) ||
      n.ip.toLowerCase().includes(query.toLowerCase()) ||
      n.role.toLowerCase().includes(query.toLowerCase())
  );

  const filteredEvents = events.filter(
    (e) =>
      e.event.toLowerCase().includes(query.toLowerCase()) ||
      e.source.toLowerCase().includes(query.toLowerCase()) ||
      (e.process && e.process.toLowerCase().includes(query.toLowerCase()))
  );

  const quickActions = [
    { label: 'Isolate Host 10.0.0.25 (Workstation)', action: () => alert('Workstation 10.0.0.25 isolated from LAN.') },
    { label: 'Run MITRE ATT&CK T1021 Simulation', action: () => onSelectTechnique('T1021') },
    { label: 'Block Outbound Port 445 on Firewall', action: () => alert('Firewall ACL rule #4092 applied: Drop inbound/outbound TCP 445.') },
    { label: 'Trigger Sandbox Malware Sandbox Trace', action: () => alert('Docker sandbox spun up container sandbox-instance-818.') }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-[#E0D9CE] overflow-hidden flex flex-col max-h-[80vh]">
        {/* Search Input Bar */}
        <div className="p-4 border-b border-[#EDE6DC] flex items-center gap-3 bg-[#FAF8F5]">
          <Search className="w-5 h-5 text-[#8893A2]" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search hosts, IPs, processes, MITRE techniques, or ask CYBERMIND AI..."
            className="w-full bg-transparent text-sm text-[#1C232B] placeholder-[#8893A2] focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-[#EFEAE2] text-[#8893A2] hover:text-[#1C232B] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Results Body */}
        <div className="p-4 overflow-y-auto space-y-4 text-xs">
          {/* Quick AI Suggestions */}
          {query.length > 0 && (
            <div className="bg-[#FAF6F0] p-3 rounded-xl border border-[#E9E1D5]">
              <div className="flex items-center gap-2 text-[#DE5B49] font-bold text-xs mb-1">
                <Zap className="w-4 h-4" />
                <span>CYBERMIND Copilot Analysis</span>
              </div>
              <p className="text-[#4E5B6B]">
                Query <span className="font-mono font-semibold text-[#1F2731]">"{query}"</span>: Correlated across 8 nodes, 1 active SMB lateral session, and 5 ATT&CK techniques. Recommended immediate action: Contain Workstation 10.0.0.25.
              </p>
            </div>
          )}

          {/* Hosts / Nodes */}
          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2">
              Network Hosts ({filteredNodes.length})
            </div>
            <div className="space-y-1">
              {filteredNodes.slice(0, 4).map((node) => (
                <div
                  key={node.id}
                  onClick={() => {
                    onSelectNode(node);
                    onClose();
                  }}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-[#F7F4EE] cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Server className="w-4 h-4 text-[#7C8898]" />
                    <div>
                      <div className="font-bold text-[#1F2731]">{node.name}</div>
                      <div className="font-mono text-[11px] text-[#768292]">{node.ip} · {node.role}</div>
                    </div>
                  </div>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    node.status === 'compromised' ? 'bg-red-100 text-red-700' :
                    node.status === 'medium-risk' ? 'bg-amber-100 text-amber-700' :
                    'bg-stone-100 text-stone-700'
                  }`}>
                    {node.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Events */}
          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2">
              Correlated Security Events ({filteredEvents.length})
            </div>
            <div className="space-y-1">
              {filteredEvents.slice(0, 3).map((evt) => (
                <div
                  key={evt.id}
                  onClick={() => {
                    onSelectEvent(evt);
                    onClose();
                  }}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-[#F7F4EE] cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <Terminal className="w-4 h-4 text-[#DE5B49]" />
                    <div>
                      <div className="font-semibold text-[#1F2731]">{evt.event}</div>
                      <div className="font-mono text-[11px] text-[#768292]">{evt.time} · {evt.source} {evt.destination ? `→ ${evt.destination}` : ''}</div>
                    </div>
                  </div>
                  <span className="font-semibold text-[#DE5B49] text-[11px]">{evt.severity}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions */}
          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2">
              Automated Response Actions
            </div>
            <div className="space-y-1">
              {quickActions.map((qa, i) => (
                <button
                  key={i}
                  onClick={() => {
                    qa.action();
                    onClose();
                  }}
                  className="w-full flex items-center justify-between p-2 rounded-lg hover:bg-[#F7F4EE] text-left text-xs font-medium text-[#384351] transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-[#DE5B49]" />
                    <span>{qa.label}</span>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-[#98A3B2]" />
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#FAF8F5] border-t border-[#EDE6DC] flex items-center justify-between text-[11px] text-[#7F8B99]">
          <span>Navigation: <kbd className="bg-white border px-1.5 py-0.5 rounded font-mono">↑</kbd> <kbd className="bg-white border px-1.5 py-0.5 rounded font-mono">↓</kbd> to select, <kbd className="bg-white border px-1.5 py-0.5 rounded font-mono">Esc</kbd> to dismiss</span>
          <span className="font-semibold text-[#DE5B49]">CYBERMIND v1.0.0</span>
        </div>
      </div>
    </div>
  );
};
