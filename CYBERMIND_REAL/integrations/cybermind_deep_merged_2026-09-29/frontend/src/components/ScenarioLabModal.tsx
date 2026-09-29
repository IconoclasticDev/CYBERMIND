import React, { useState } from 'react';
import { X, FlaskConical, Play, CheckCircle2, AlertOctagon, RotateCcw, Shield } from 'lucide-react';

interface ScenarioLabModalProps {
  isOpen: boolean;
  onClose: () => void;
  isRunning: boolean;
  onToggleRunning: () => void;
  onReset: () => void;
  currentScenario: string;
  onSelectScenario: (name: string) => void;
}

export const ScenarioLabModal: React.FC<ScenarioLabModalProps> = ({
  isOpen,
  onClose,
  isRunning,
  onToggleRunning,
  onReset,
  currentScenario,
  onSelectScenario
}) => {
  if (!isOpen) return null;

  const scenarios = [
    {
      id: 'smb-lateral',
      name: 'Lateral Movement (SMB)',
      tactics: ['Initial Access', 'Execution', 'Lateral Movement'],
      complexity: 'Medium',
      duration: '6m 30s',
      description: 'Simulates spear-phishing ingress followed by PowerShell memory injection and SMB administrative share traversal.'
    },
    {
      id: 'ransomware',
      name: 'Ransomware Pre-deployment (Cobalt Strike)',
      tactics: ['Execution', 'Persistence', 'Defense Evasion', 'Impact'],
      complexity: 'High',
      duration: '12m 00s',
      description: 'Simulates beaconing across C2, shadow copy deletion (vssadmin), and multi-host file encryption canary staging.'
    },
    {
      id: 'kerberoast',
      name: 'Active Directory Kerberoasting & Privilege Escalation',
      tactics: ['Credential Access', 'Privilege Escalation'],
      complexity: 'High',
      duration: '8m 45s',
      description: 'Requests service tickets for service principal names (SPNs) with RC4 encryption to crack offline passwords.'
    },
    {
      id: 'exfil',
      name: 'Covert Cloud Exfiltration via Encrypted DNS',
      tactics: ['Exfiltration', 'Command & Control'],
      complexity: 'Low',
      duration: '4m 15s',
      description: 'Encodes database records into DNS queries to simulate stealthy outbound data theft past egress proxies.'
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#DE5B49] flex items-center justify-center text-white">
              <FlaskConical className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-[#1C232B]">CYBERMIND Scenario Simulation Lab</h3>
              <div className="text-[11px] text-[#7A8696]">Adversary Emulation &amp; Automated Detection Verification</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2] hover:text-[#1C232B] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          <div className="bg-[#FAF9F6] border border-[#EDE7DE] rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8796]">Active Emulation Target</span>
              <div className="font-bold text-stone-900 text-sm mt-0.5">{currentScenario}</div>
              <div className="text-[11px] text-[#556172] mt-0.5">
                Status: <span className={isRunning ? 'text-[#2EAA58] font-bold' : 'text-stone-500 font-bold'}>
                  {isRunning ? 'Running in Sandbox' : 'Paused'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={onToggleRunning}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-colors ${
                  isRunning ? 'bg-[#DE5B49] hover:bg-[#C94735]' : 'bg-[#2EAA58] hover:bg-[#25944B]'
                }`}
              >
                {isRunning ? 'Pause Sandbox' : 'Start Sandbox'}
              </button>
              <button
                onClick={onReset}
                className="px-3 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 text-stone-700 rounded-lg text-xs font-bold"
              >
                Reset
              </button>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2.5">
              Select Preset Attack Scenario
            </div>
            <div className="space-y-2.5">
              {scenarios.map((sc) => {
                const isSelected = currentScenario === sc.name;
                return (
                  <div
                    key={sc.id}
                    onClick={() => onSelectScenario(sc.name)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#FAF6F2] border-[#DE5B49] shadow-xs'
                        : 'bg-white border-[#EDE7DE] hover:border-[#D9CFBF] hover:bg-[#FAF9F6]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-[#1C232B] text-xs flex items-center gap-2">
                        {isSelected && <span className="w-2 h-2 rounded-full bg-[#DE5B49]" />}
                        <span>{sc.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-medium text-stone-500 font-mono">{sc.duration}</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          sc.complexity === 'High' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                        }`}>
                          {sc.complexity}
                        </span>
                      </div>
                    </div>
                    <p className="mt-1.5 text-[#556171] leading-relaxed text-[11px]">
                      {sc.description}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {sc.tactics.map((t) => (
                        <span key={t} className="bg-stone-100 text-stone-600 px-2 py-0.5 rounded text-[10px] font-medium">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <span className="text-[11px] text-[#768292]">Sandbox Environment: Docker Isolated VPC</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-[#DE5B49] hover:bg-[#C94838] text-white rounded-lg text-xs font-bold shadow-xs"
          >
            Apply &amp; Return to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
};
