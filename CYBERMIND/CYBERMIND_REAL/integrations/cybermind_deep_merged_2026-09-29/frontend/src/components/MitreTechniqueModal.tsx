import React from 'react';
import { X, Shield, BookOpen, ExternalLink, CheckCircle } from 'lucide-react';
import { MITRE_TECHNIQUES } from '../data/initialData';

interface MitreTechniqueModalProps {
  techniqueId: string | null;
  onClose: () => void;
}

export const MitreTechniqueModal: React.FC<MitreTechniqueModalProps> = ({
  techniqueId,
  onClose
}) => {
  if (!techniqueId) return null;

  const technique = MITRE_TECHNIQUES[techniqueId] || {
    id: techniqueId,
    name: 'Adversary Technique: ' + techniqueId,
    tactic: 'Tactical Traversal',
    description: 'MITRE ATT&CK framework technique mapped to enterprise defensive telemetry.',
    detection: 'Correlate host telemetry, Windows security events (Event ID 4624/4688), and network flow.',
    mitigation: 'Implement principle of least privilege, enforce network segmentation, and enable behavioral blocking.',
    severity: 'High'
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#DE5B49] flex items-center justify-center text-white font-mono font-bold text-xs">
              {technique.id}
            </div>
            <div>
              <h3 className="font-bold text-sm text-[#1C232B]">{technique.name}</h3>
              <div className="text-[11px] text-[#7A8696] font-medium">Tactic: {technique.tactic}</div>
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
        <div className="p-5 overflow-y-auto space-y-4 text-xs">
          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-1">
              Technique Description
            </div>
            <p className="text-[#3E4A59] leading-relaxed bg-[#FAF9F6] p-3 rounded-xl border border-[#EDE7DE]">
              {technique.description}
            </p>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-1 flex items-center gap-1.5 text-[#2EAA58]">
              <CheckCircle className="w-3.5 h-3.5" />
              <span>Detection Strategies</span>
            </div>
            <p className="text-[#3E4A59] leading-relaxed bg-[#F3FAF5] p-3 rounded-xl border border-[#D5EEDB]">
              {technique.detection}
            </p>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-1 flex items-center gap-1.5 text-[#DE5B49]">
              <Shield className="w-3.5 h-3.5" />
              <span>Mitigation &amp; Defense Hardening</span>
            </div>
            <p className="text-[#3E4A59] leading-relaxed bg-[#FDF5F4] p-3 rounded-xl border border-[#F8D8D4]">
              {technique.mitigation}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <a
            href={`https://attack.mitre.org/techniques/${technique.id}/`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-[#DE5B49] font-bold hover:underline"
          >
            <span>View on MITRE ATT&amp;CK Matrix</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 rounded-lg text-xs font-bold text-[#353F4C]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
