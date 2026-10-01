import React, { useEffect, useState } from "react";
import { Award, Info, X } from "lucide-react";
import { api, type BenchmarkComparison } from "../lib/api";

type EvidenceComparison = BenchmarkComparison & { source?: string; checkpoint_sha256?: string };
export const BenchmarkModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
  const [bench, setBench] = useState<EvidenceComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    api.benchmarkComparison().then((comparison) => {
      if (!active) return;
      setBench(comparison);
      setError(null);
    }).catch((e) => {
      if (!active) return;
      setBench(null);
      setError(e instanceof Error ? e.message : String(e));
    });
    return () => { active = false; };
  }, [isOpen]);
  if (!isOpen) return null;
  const loading = bench === null && error === null;
  const cm = bench?.models.cybermind_world_model;
  const lr = bench?.models.logistic_baseline;
  const pct = (v: number | undefined) => v == null ? "—" : `${(v * 100).toFixed(2)}%`;
  const metricRows: Array<[string, "f1" | "precision" | "recall" | "fpr" | "ap", string | undefined]> = [
    ["F1 Score", "f1", bench?.deltas_vs_logistic.f1_delta],
    ["Precision", "precision", bench?.deltas_vs_logistic.precision_delta],
    ["Recall", "recall", bench?.deltas_vs_logistic.recall_delta],
    ["False Positive Rate", "fpr", bench?.deltas_vs_logistic.fpr_reduction],
    ["Average Precision", "ap", bench?.deltas_vs_logistic.ap_delta],
  ];
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="CYBERMIND model benchmark">
    <div className="bg-white border border-[#EAE6DF] rounded-3xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto custom-scroll">
      <div className="flex items-center justify-between border-b border-[#F0EBE1] pb-3 gap-3">
        <div className="flex items-center gap-2.5 min-w-0"><div className="w-8 h-8 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-700 shrink-0"><Award className="w-4 h-4" /></div>
          <div><h2 className="text-sm font-extrabold text-[#171F27]">CYBERMIND Model Benchmark &amp; Baseline</h2><p className="text-[11px] text-[#707C8C]">Saved held-out comparison for the loaded checkpoint</p></div>
        </div>
        <button onClick={onClose} aria-label="Close benchmark" className="p-1 rounded-lg text-[#8C95A3] hover:text-[#171F27] hover:bg-[#FAF8F5]"><X className="w-4 h-4" /></button>
      </div>
      {loading && <div className="text-xs text-[#707C8C]">Loading verified comparison…</div>}
      {error && <div className="bg-[#FDF2F0] border border-[#F9DCD7] rounded-xl p-3 text-xs text-[#B33A2B]">Benchmark unavailable: {error}</div>}
      {bench && cm && lr && <>
        <div className="bg-[#FAF8F5] border border-[#E2DBD0] rounded-xl p-3 text-[11px] text-[#333E4D] space-y-1">
          <div className="flex items-center gap-2"><Info className="w-4 h-4 text-cyan-600 shrink-0" /><strong>{bench.calibration_constraint}</strong></div>
          <div>{bench.dataset}: {bench.dataset_flows_evaluated.toLocaleString()} future-window decisions.</div>
          <div>{bench.source}</div><div className="font-mono text-[10px] break-all">Checkpoint SHA-256: {bench.checkpoint_sha256}</div>
        </div>
        <div className="border border-[#EAE6DF] rounded-2xl overflow-x-auto shadow-2xs"><table className="w-full min-w-[540px] text-left text-xs border-collapse font-mono">
          <thead><tr className="bg-[#FAF8F5] border-b border-[#EAE6DF] text-[#707C8C] text-[10px] uppercase"><th className="py-2.5 px-3">Metric</th><th className="py-2.5 px-3 text-[#DE5B49]">CYBERMIND best.pt</th><th className="py-2.5 px-3">Feature-matched logistic</th><th className="py-2.5 px-3 text-right">Difference</th></tr></thead>
          <tbody className="divide-y divide-[#F0EBE1] text-[11px]">{metricRows.map(([label, key, delta]) => <tr key={label} className="hover:bg-[#FAF8F5]"><td className="py-2.5 px-3 font-bold text-[#1C232B]">{label}</td><td className="py-2.5 px-3 font-bold text-[#DE5B49]">{pct(cm.metrics[key])}</td><td className="py-2.5 px-3 text-[#556171]">{pct(lr.metrics[key])}</td><td className="py-2.5 px-3 text-right font-bold text-[#333E4D]">{delta ?? "—"}</td></tr>)}</tbody>
        </table></div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{[["CYBERMIND", cm.confusion_matrix], ["Feature-matched logistic", lr.confusion_matrix]].map(([name, counts]) => {
          const c = counts as typeof cm.confusion_matrix;
          return <div key={name as string} className="bg-[#FAF8F5] border border-[#E8E2D7] rounded-xl p-3 font-mono text-[10px]"><div className="font-bold text-[#1C232B] uppercase mb-1">{name as string}</div><div>TP {c.tp} · FP {c.fp} · TN {c.tn} · FN {c.fn}</div></div>;
        })}</div>
        <div className="bg-[#FAF6F2] border border-[#EBE3D7] text-[#556171] p-3 rounded-xl text-xs leading-relaxed">{bench.verdict}</div>
      </>}
    </div>
  </div>;
};
