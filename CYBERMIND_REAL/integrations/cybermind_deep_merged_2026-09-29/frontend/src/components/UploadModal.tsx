import React, { useState, useRef, useEffect } from "react";
import { X, Upload, FileText, CheckCircle2, AlertCircle, Loader2, ArrowRight, Table } from "lucide-react";
import { api } from "../lib/api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (data: any) => void;
  onViewFlaggedFlows?: () => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  onViewFlaggedFlows,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [clearPrevious, setClearPrevious] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setFile(null);
    setResult(null);
    setError(null);
  }, [isOpen]);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (f: File) => {
    const ext = f.name.toLowerCase();
    if (ext.endsWith(".csv") || ext.endsWith(".pcap") || ext.endsWith(".pcapng") || ext.endsWith(".cap")) {
      setFile(f);
      setError(null);
      setResult(null);
    } else {
      setError("Supported file types: .CSV, .PCAP, .PCAPNG");
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await api.uploadFlows(file, clearPrevious);
      setResult(res);
      onSuccess(res);
    } catch (err: any) {
      setError(err.message || "Failed to process uploaded file");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white border border-[#EAE6DF] rounded-3xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#F0EBE1] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-[#FAF0ED] border border-[#F4D0C9] flex items-center justify-center text-[#DE5B49]">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-extrabold text-[#171F27]">
                Upload Network Flows (PCAP / CSV)
              </h2>
              <p className="text-[11px] text-[#707C8C]">
                PS Element B.1: Ingest Wireshark captures or CICFlowMeter exports
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-[#8C95A3] hover:text-[#171F27] hover:bg-[#FAF8F5] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Dropzone Area */}
        {!result ? (
          <div className="space-y-4">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
                dragActive
                  ? "border-[#DE5B49] bg-[#FAF4EE]"
                  : file
                  ? "border-emerald-400 bg-emerald-50/30"
                  : "border-[#DDD6CC] bg-[#FAF8F5] hover:border-[#BDB5A6]"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.pcap,.pcapng,.cap"
                className="hidden"
                onChange={handleFileChange}
              />
              <div className="flex flex-col items-center gap-2">
                <div className="w-10 h-10 rounded-2xl bg-white border border-[#DDD6CC] flex items-center justify-center text-[#707C8C] shadow-2xs">
                  {file ? <FileText className="w-5 h-5 text-emerald-600" /> : <Upload className="w-5 h-5" />}
                </div>
                {file ? (
                  <div>
                    <div className="text-xs font-bold text-[#1C232B]">{file.name}</div>
                    <div className="text-[10px] text-[#707C8C] font-mono mt-0.5">
                      {(file.size / 1024).toFixed(1)} KB &bull; Ready for inference
                    </div>
                  </div>
                ) : (
                  <div>
                    <div className="text-xs font-bold text-[#1C232B]">
                      Drag & Drop PCAP or CSV flow export
                    </div>
                    <div className="text-[10px] text-[#707C8C] mt-0.5">
                      or click to browse from your filesystem
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Supported Formats info */}
            <div className="flex items-center justify-between text-[10px] font-mono text-[#8C95A3]">
              <div className="flex items-center gap-1.5">
                <span className="bg-[#F0ECE1] px-1.5 py-0.5 rounded text-[#556171]">.PCAP / .PCAPNG</span>
                <span className="bg-[#F0ECE1] px-1.5 py-0.5 rounded text-[#556171]">.CSV (CICFlowMeter)</span>
              </div>
              <span>Fuzzy column matching</span>
            </div>

            {/* Toggle clear previous state */}
            <label className="flex items-center gap-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={clearPrevious}
                onChange={(e) => setClearPrevious(e.target.checked)}
                className="rounded border-[#DDD6CC] text-[#DE5B49] focus:ring-0"
              />
              <span className="text-xs text-[#556171]">Clear previous network state before ingest</span>
            </label>

            {error && (
              <div className="bg-[#FDF2F0] border border-[#F9DCD7] text-[#B33A2B] text-xs p-3 rounded-xl flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Upload Action */}
            <button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full py-2.5 rounded-xl bg-[#DE5B49] hover:bg-[#C54737] disabled:opacity-40 text-white font-bold text-xs tracking-wider uppercase transition-all shadow-sm flex items-center justify-center gap-2 cursor-pointer"
            >
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Processing & Running GNN Inference...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  <span>Ingest & Run World Model</span>
                </>
              )}
            </button>
          </div>
        ) : (
          /* Result Confirmation */
          <div className="space-y-4 py-2">
            <div className="bg-[#EBF7EE] border border-[#C3E8CA] text-[#1E7B3E] p-4 rounded-2xl flex items-start gap-3">
              <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-600 mt-0.5" />
              <div>
                <div className="text-xs font-bold text-emerald-900">
                  Network Flows Ingested Successfully!
                </div>
                <div className="text-[11px] text-emerald-700 mt-1">
                  <strong>{result.flows_ingested}</strong> flow events parsed from{" "}
                  <strong>{result.filename}</strong> and mapped to canonical graph states. {result.forecast ? "World-model forecast generated." : "More time-spaced flow windows are needed before forecasting."}
                </div>
                {result.time_basis === "assumed_60s_spacing" && <div className="text-[10px] text-amber-800 mt-1">No source timestamps were found; 60-second spacing was assumed for this upload.</div>}
              </div>
            </div>

            {result.forecast?.current && (
              <div className="rounded-2xl border border-[#EAE6DF] bg-[#FAF8F5] p-4 text-xs text-[#3C4755]">
                <div className="font-bold text-[#171F27]">World-model forecast from the imported traffic</div>
                <div className="mt-1.5">
                  Current model stage: <strong>{result.forecast.current.stage}</strong> ·
                  risk <strong>{Math.round(result.forecast.current.risk * 100)}%</strong> ·
                  {" "}{result.forecast.observation_windows} observed windows
                </div>
                {result.filename?.toLowerCase().match(/\.(pcap|pcapng|cap)$/) && (
                  <p className="mt-2 text-[11px] text-[#7A8696] leading-relaxed">
                    A raw PCAP has no attack ground-truth labels. Flow-stage hints may say Unknown/Ambiguous;
                    the stage and risk above are model forecasts for the graph window, not verified per-flow labels.
                  </p>
                )}
              </div>
            )}

            <div className="flex items-center gap-2 pt-2">
              {onViewFlaggedFlows && (
                <button
                  onClick={() => {
                    onClose();
                    onViewFlaggedFlows();
                  }}
                  className="flex-1 py-2 px-3 rounded-xl bg-white hover:bg-[#FAF8F5] border border-[#DDD6CC] text-[#333E4D] text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Table className="w-3.5 h-3.5 text-cyan-600" />
                  <span>Inspect Flagged Flows</span>
                </button>
              )}

              <button
                onClick={onClose}
                className="flex-1 py-2 px-3 rounded-xl bg-[#DE5B49] hover:bg-[#C54737] text-white text-xs font-bold transition-all shadow-xs flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <span>View Live Graph</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
