import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Table, ShieldAlert, ShieldCheck, ArrowLeft, RefreshCw, Search, Filter,
  ExternalLink, Zap, AlertTriangle, ArrowUpDown, ChevronRight, Activity
} from "lucide-react";
import type { FlaggedFlow, FlaggedFlowsResponse } from "../lib/api";
import { api } from "../lib/api";

interface FlaggedFlowsViewProps {
  onBack?: () => void;
  onIsolateHost?: (host: string) => void;
  onProbeInSandbox?: (host: string, port: number, vectorId?: string) => void;
}

export const FlaggedFlowsView: React.FC<FlaggedFlowsViewProps> = ({
  onBack,
  onIsolateHost,
  onProbeInSandbox,
}) => {
  const [flows, setFlows] = useState<FlaggedFlow[]>([]);
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [selectedBand, setSelectedBand] = useState<string>("ALL");
  const [sortField, setSortField] = useState<keyof FlaggedFlow>("risk_score");
  const [sortAsc, setSortAsc] = useState(false);

  const fetchFlows = useCallback(async () => {
    setLoading(true);
    try {
      const res: FlaggedFlowsResponse = await api.flaggedFlows(250, 0.0);
      setFlows(res.flows || []);
      setSummary(res.summary || null);
    } catch (err) {
      console.error("Failed to fetch flagged flows", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFlows();
    const interval = setInterval(fetchFlows, 3500);
    return () => clearInterval(interval);
  }, [fetchFlows]);

  // Filter & Sort
  const filteredFlows = useMemo(() => {
    return flows
      .filter((f) => {
        const matchesBand = selectedBand === "ALL"
          || f.risk_band === selectedBand
          || (selectedBand === "BENIGN" && f.risk_band === "LOW");
        if (!matchesBand) return false;
        if (search.trim()) {
          const q = search.toLowerCase();
          return (
            f.src.toLowerCase().includes(q) ||
            f.dst.toLowerCase().includes(q) ||
            f.label.toLowerCase().includes(q) ||
            f.predicted_stage.toLowerCase().includes(q) ||
            f.technique_id.toLowerCase().includes(q) ||
            String(f.dst_port).includes(q)
          );
        }
        return true;
      })
      .sort((a, b) => {
        const valA = a[sortField];
        const valB = b[sortField];
        if (typeof valA === "number" && typeof valB === "number") {
          return sortAsc ? valA - valB : valB - valA;
        }
        return sortAsc
          ? String(valA).localeCompare(String(valB))
          : String(valB).localeCompare(String(valA));
      });
  }, [flows, selectedBand, search, sortField, sortAsc]);

  const handleSort = (field: keyof FlaggedFlow) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const getBandBadgeClass = (band: string) => {
    switch (band) {
      case "UNASSESSED":
        return "bg-[#F4F1EB] text-[#687586] border border-[#DDD6CC]";
      case "CRITICAL":
        return "bg-[#FDF2F0] text-[#B33A2B] border border-[#F9DCD7]";
      case "HIGH":
        return "bg-[#FAF0ED] text-[#C54737] border border-[#F4D0C9]";
      case "MEDIUM":
        return "bg-[#FEF6EE] text-[#B54708] border border-[#F9DBAF]";
      default:
        return "bg-[#EBF7EE] text-[#1E7B3E] border border-[#C3E8CA]";
    }
  };

  return (
    <div className="space-y-4 animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            {onBack && (
              <button
                onClick={onBack}
                className="p-1.5 rounded-lg hover:bg-[#FAF8F5] text-[#556171] hover:text-[#1C232B] transition-colors"
                title="Back to Command Center"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
            )}
            <h1 className="text-xl font-extrabold text-[#171F27] flex items-center gap-2">
              <Table className="w-5 h-5 text-[#DE5B49]" />
              Flagged-Flows Risk Telemetry Table
            </h1>
            <span className="bg-[#FAF0ED] text-[#C54737] border border-[#F4D0C9] text-[10px] font-bold px-2 py-0.5 rounded-full font-mono uppercase">
              PS Element B.2
            </span>
          </div>
          <p className="text-xs text-[#707C8C] mt-1">
            Packet and flow features with rule-based triage hints. Scores and stage hints below are not model predictions; the model forecasts graph windows in Threat Forecast.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchFlows}
            disabled={loading}
            className="py-1.5 px-3 rounded-xl bg-[#FAF8F5] hover:bg-[#F2EDE4] border border-[#DDD6CC] text-[#333E4D] text-xs font-bold transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-[#DE5B49]" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {(summary?.unassessed_count ?? 0) > 0 && (
        <div className="rounded-xl border border-[#EBD9BC] bg-[#FCF7EC] px-4 py-3 text-xs text-[#85572D]">
          {summary.unassessed_count} raw-PCAP flows have no attack ground-truth labels, so their per-flow risk is unassessed.
          Inspect the separate world-model forecast for graph-window predictions.
        </div>
      )}

      {/* Summary KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3.5 shadow-2xs">
          <div className="text-[10px] font-bold uppercase text-[#8C95A3] font-mono">Active Ingested Flows</div>
          <div className="text-2xl font-extrabold text-[#1C232B] font-mono mt-0.5">{flows.length}</div>
          <div className="text-[10px] text-[#707C8C] mt-0.5">Audited flow windows</div>
        </div>

        <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3.5 shadow-2xs">
          <div className="text-[10px] font-bold uppercase text-[#B33A2B] font-mono">Critical / High Risk</div>
          <div className="text-2xl font-extrabold text-[#C54737] font-mono mt-0.5">
            {(summary?.critical_count || 0) + (summary?.high_count || 0)}
          </div>
          <div className="text-[10px] text-[#707C8C] mt-0.5">Flow heuristic score &ge; 65%</div>
        </div>

        <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3.5 shadow-2xs">
          <div className="text-[10px] font-bold uppercase text-[#B54708] font-mono">Medium Risk Flows</div>
          <div className="text-2xl font-extrabold text-[#B54708] font-mono mt-0.5">
            {summary?.medium_count || 0}
          </div>
          <div className="text-[10px] text-[#707C8C] mt-0.5">Threat score 30–64%</div>
        </div>

        <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3.5 shadow-2xs">
          <div className="text-[10px] font-bold uppercase text-[#1E7B3E] font-mono">Benign / Secured</div>
          <div className="text-2xl font-extrabold text-[#1E7B3E] font-mono mt-0.5">
            {summary?.low_or_benign_count || 0}
          </div>
          <div className="text-[10px] text-[#707C8C] mt-0.5">Threat score &lt; 30%</div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white border border-[#EAE6DF] rounded-2xl p-3 shadow-2xs flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="min-w-0 flex flex-wrap items-center gap-2 flex-1">
          <div className="relative min-w-[180px] flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#8C95A3]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by IP, port, technique, or attack label..."
              className="w-full pl-8 pr-3 py-1.5 rounded-xl border border-[#DDD6CC] bg-[#FAF8F5] text-xs text-[#1C232B] placeholder:text-[#8C95A3] focus:outline-hidden focus:border-[#DE5B49]"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1">
            {["ALL", "CRITICAL", "HIGH", "MEDIUM", "BENIGN", "UNASSESSED"].map((band) => (
              <button
                key={band}
                onClick={() => setSelectedBand(band)}
                className={`px-2.5 py-1 rounded-lg text-[10px] font-mono font-bold transition-all ${
                  selectedBand === band
                    ? "bg-[#1C232B] text-white"
                    : "bg-[#FAF8F5] text-[#556171] hover:bg-[#F2EDE4]"
                }`}
              >
                {band}
              </button>
            ))}
          </div>
        </div>

        <div className="text-[11px] font-mono text-[#707C8C]">
          Showing {filteredFlows.length} of {flows.length} flows
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-white border border-[#EAE6DF] rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-[#FAF8F5] border-b border-[#EAE6DF] text-[#707C8C] font-mono text-[10px] uppercase">
                <th
                  onClick={() => handleSort("risk_score")}
                  className="py-3 px-4 font-bold cursor-pointer hover:text-[#1C232B]"
                >
                  <div className="flex items-center gap-1">
                    <span>Flow Heuristic</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4 font-bold">Source Host &rarr; Destination Host</th>
                <th
                  onClick={() => handleSort("protocol")}
                  className="py-3 px-4 font-bold cursor-pointer hover:text-[#1C232B]"
                >
                  Proto / Port
                </th>
                <th
                  onClick={() => handleSort("tot_bytes")}
                  className="py-3 px-4 font-bold cursor-pointer hover:text-[#1C232B]"
                >
                  <div className="flex items-center gap-1">
                    <span>Volume</span>
                    <ArrowUpDown className="w-3 h-3" />
                  </div>
                </th>
                <th className="py-3 px-4 font-bold">Source Label / Stage Hint</th>
                <th className="py-3 px-4 font-bold text-right">Countermeasure Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F0EBE1]">
              {filteredFlows.length > 0 ? (
                filteredFlows.map((flow) => {
                  const isCritical = flow.risk_band === "CRITICAL" || flow.risk_band === "HIGH";
                  return (
                    <tr key={flow.flow_id} className="hover:bg-[#FAF8F5] transition-colors">
                      {/* Risk Score */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[9px] font-mono font-bold px-2 py-0.5 rounded uppercase ${getBandBadgeClass(
                              flow.risk_band
                            )}`}
                          >
                            {flow.risk_band === "UNASSESSED" ? "Unassessed" : `${flow.risk_pct.toFixed(1)}%`}
                          </span>
                          {flow.risk_band !== "UNASSESSED" && <div className="w-16 bg-[#EAE5DC] h-1.5 rounded-full overflow-hidden hidden sm:block">
                            <div
                              className={`h-full rounded-full ${
                                isCritical ? "bg-[#DE5B49]" : flow.risk_band === "MEDIUM" ? "bg-[#E58B44]" : "bg-emerald-500"
                              }`}
                              style={{ width: `${Math.min(100, Math.max(5, flow.risk_pct))}%` }}
                            />
                          </div>}
                        </div>
                      </td>

                      {/* Source & Destination */}
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-[#1C232B]">{flow.src}</span>
                          <span className="text-[#8C95A3]">&rarr;</span>
                          <span className="font-bold text-[#1C232B]">{flow.dst}</span>
                        </div>
                        <div className="text-[10px] text-[#707C8C]">
                          Label: <span className="text-[#DE5B49] font-medium">{flow.label}</span>
                        </div>
                      </td>

                      {/* Proto / Port */}
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div>
                          <span className="font-bold text-[#1C232B]">{flow.protocol}</span>
                          <span className="text-[#8C95A3]"> / {flow.dst_port}</span>
                        </div>
                        <div className="text-[10px] text-[#707C8C]">{flow.duration}s duration</div>
                      </td>

                      {/* Volume */}
                      <td className="py-3 px-4 font-mono text-[11px]">
                        <div className="font-bold text-[#1C232B]">
                          {(flow.tot_bytes / 1024).toFixed(1)} KB
                        </div>
                        <div className="text-[10px] text-[#707C8C]">
                          {flow.packets_fwd + flow.packets_bwd} pkts
                        </div>
                      </td>

                      {/* Predicted Stage */}
                      <td className="py-3 px-4">
                        <div className="text-xs font-bold text-[#1C232B]">
                          {flow.predicted_stage}
                        </div>
                        {flow.technique_id && (
                          <div className="text-[10px] font-mono text-cyan-700 bg-cyan-50 px-1.5 py-0.5 rounded inline-block mt-0.5">
                            {flow.technique_id}
                          </div>
                        )}
                      </td>

                      {/* Quick Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {onIsolateHost && (
                            <button
                              onClick={() => onIsolateHost(flow.src)}
                              className="px-2.5 py-1 rounded-lg bg-[#FAF8F5] hover:bg-[#F0EBE1] border border-[#DDD6CC] text-[#333E4D] text-[10px] font-bold font-mono transition-all"
                              title="Simulate isolating this host"
                            >
                              Isolate Host
                            </button>
                          )}

                          {onProbeInSandbox && (
                            <button
                              onClick={() => {
                                const vec = flow.dst_port === 8081 ? "sqli_probe" : flow.dst_port === 445 ? "smb_lateral" : "ssh_bruteforce";
                                onProbeInSandbox(flow.dst, flow.dst_port, vec);
                              }}
                              className="px-2.5 py-1 rounded-lg bg-[#FAF0ED] hover:bg-[#F5DFDA] border border-[#F4D0C9] text-[#C54737] text-[10px] font-bold font-mono transition-all flex items-center gap-1"
                              title="Probe this vector non-destructively in isolated sandbox"
                            >
                              <Zap className="w-3 h-3" />
                              <span>Probe Sandbox</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-xs text-[#707C8C]">
                    No network flows matching current filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
