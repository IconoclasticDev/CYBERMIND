import React, { useState } from 'react';
import { X, Download, Printer, Copy, Check, ShieldCheck, FileText } from 'lucide-react';

interface ExportReportModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExportReportModal: React.FC<ExportReportModalProps> = ({
  isOpen,
  onClose
}) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#DE5B49] flex items-center justify-center text-white">
              <FileText className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-[#1C232B]">CYBERMIND SOC Incident Brief</h3>
              <div className="font-mono text-[11px] text-[#7A8696]">Ref: INC-2025-0912-887B · Automated Synthesis</div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2] hover:text-[#1C232B] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Report Content */}
        <div className="p-6 overflow-y-auto space-y-4 text-xs font-sans">
          {/* Executive Summary */}
          <div className="p-4 rounded-xl bg-[#FAF9F6] border border-[#EDE7DE]">
            <div className="flex items-center justify-between mb-2">
              <span className="font-editorial text-lg font-bold text-stone-900 tracking-tight">Executive Incident Brief</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-red-100 text-red-700">Risk Score 72/100 (HIGH)</span>
            </div>
            <p className="text-[#4A5768] leading-relaxed">
              At 14:21 UTC, the CYBERMIND predictive engine flagged an active multi-stage intrusion traversing the internal subnet. Following an initial spear-phishing ingress, adversaries executed PowerShell scripts, bypassed memory protections, and initiated lateral movement over SMB (port 445) toward core corporate databases.
            </p>
          </div>

          {/* Incident Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 bg-white border border-[#EAE3D7] rounded-xl">
              <span className="text-[10px] uppercase font-bold text-[#8A95A4]">Threat Stage</span>
              <div className="font-bold text-stone-900 text-sm mt-0.5">Lateral Movement</div>
              <span className="text-[11px] text-[#2EAA58] font-medium">Confidence: 78%</span>
            </div>
            <div className="p-3 bg-white border border-[#EAE3D7] rounded-xl">
              <span className="text-[10px] uppercase font-bold text-[#8A95A4]">Predicted Next</span>
              <div className="font-bold text-stone-900 text-sm mt-0.5">Persistence (Service)</div>
              <span className="text-[11px] text-[#E58B44] font-medium">Confidence: 81%</span>
            </div>
            <div className="p-3 bg-white border border-[#EAE3D7] rounded-xl">
              <span className="text-[10px] uppercase font-bold text-[#8A95A4]">Impacted Assets</span>
              <div className="font-bold text-stone-900 text-sm mt-0.5">3 Systems</div>
              <span className="text-[11px] text-[#DE5B49] font-medium">10.0.0.25, 10.0.0.15, 10.0.0.1</span>
            </div>
          </div>

          {/* Key Findings */}
          <div>
            <h4 className="font-bold text-stone-900 text-xs uppercase tracking-wide mb-2">Observed Indicators &amp; MITRE Techniques</h4>
            <div className="space-y-1.5 font-mono text-[11px]">
              <div className="p-2 bg-stone-50 border border-stone-200 rounded flex justify-between">
                <span>[T1021.002] SMB/Windows Admin Shares</span>
                <span className="text-stone-500">10.0.0.25 → 10.0.0.15:445</span>
              </div>
              <div className="p-2 bg-stone-50 border border-stone-200 rounded flex justify-between">
                <span>[T1059.001] PowerShell Script Block</span>
                <span className="text-stone-500">Process PID: 4892</span>
              </div>
              <div className="p-2 bg-stone-50 border border-stone-200 rounded flex justify-between">
                <span>[T1003.001] LSASS Memory Dump Attempt</span>
                <span className="text-stone-500">CORP\r.henderson Context</span>
              </div>
            </div>
          </div>

          {/* Prescribed Remediations */}
          <div>
            <h4 className="font-bold text-stone-900 text-xs uppercase tracking-wide mb-2 text-[#2EAA58] flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" />
              <span>Prescribed Containment Actions</span>
            </h4>
            <ul className="list-disc pl-5 space-y-1 text-[#465363] leading-relaxed">
              <li>Isolate host 10.0.0.25 (Workstation) immediately from LAN.</li>
              <li>Terminate all open SMB sessions targeting 10.0.0.15 (DB Server).</li>
              <li>Force password reset and Kerberos ticket revocation for user CORP\r.henderson.</li>
              <li>Apply firewall ACL to restrict TCP 445 cross-workstation traffic.</li>
            </ul>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="px-3 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 rounded-lg text-xs font-semibold text-[#353F4C] flex items-center gap-1.5"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Brief</span>
            </button>
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 rounded-lg text-xs font-semibold text-[#353F4C] flex items-center gap-1.5"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Text'}</span>
            </button>
          </div>

          <button
            onClick={() => {
              alert('Downloading CYBERMIND_Incident_Report_INC-2025-0912.pdf ...');
              onClose();
            }}
            className="px-4 py-1.5 bg-[#DE5B49] hover:bg-[#C94838] text-white rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-sm"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Incident Package</span>
          </button>
        </div>
      </div>
    </div>
  );
};
