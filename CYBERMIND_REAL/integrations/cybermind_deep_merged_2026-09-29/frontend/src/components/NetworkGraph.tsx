import React, { useMemo, useState } from "react";
import { Share2, Maximize2, Minimize2, GitBranch, Zap, ShieldCheck, ShieldAlert, ArrowRight, Check } from "lucide-react";
import type { UINode, UILink } from "../lib/adapters";

interface NetworkGraphProps {
  nodes: UINode[];
  links: UILink[];
  onSelectNode: (node: UINode) => void;
  selectedNodeId?: string | null;
  windowLabel?: string;
  onTakeToParallelFutures?: (node: UINode) => void;
  onAttackWithStrix?: (node: UINode) => void;
  onSuggestPatch?: (node: UINode) => void;
  defendedNodeIds?: Set<string>;
}

const STATUS_COLORS: Record<string, { bg: string; border: string; glow: string }> = {
  compromised: { bg: "#DE5B49", border: "#C74534", glow: "rgba(222,91,73,0.4)" },
  "high-risk": { bg: "#D9654C", border: "#C1523B", glow: "rgba(217,101,76,0.35)" },
  "medium-risk": { bg: "#E58B44", border: "#CB732E", glow: "rgba(229,139,68,0.35)" },
  normal: { bg: "#2B3B4C", border: "#1E2C3A", glow: "transparent" },
};

export const NetworkGraph: React.FC<NetworkGraphProps> = ({
  nodes, links, onSelectNode, selectedNodeId, windowLabel,
  onTakeToParallelFutures, onAttackWithStrix, onSuggestPatch, defendedNodeIds,
}) => {
  const [isLive, setIsLive] = useState(true);
  const [filter, setFilter] = useState("All Nodes");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);
  const [snapshot, setSnapshot] = useState<{ nodes: UINode[]; links: UILink[]; windowLabel?: string } | null>(null);
  const sourceNodes = isLive ? nodes : snapshot?.nodes ?? nodes;
  const sourceLinks = isLive ? links : snapshot?.links ?? links;
  const shownWindowLabel = isLive ? windowLabel : snapshot?.windowLabel;

  // A capture can contain thousands of endpoints. Draw a deterministic, bounded
  // overview; all endpoints remain available to the rest of the application.
  const { graphNodes, graphLinks, eligibleCount } = useMemo(() => {
    const degree = new Map<string, number>();
    for (const link of sourceLinks) {
      degree.set(link.source, (degree.get(link.source) ?? 0) + 1);
      degree.set(link.target, (degree.get(link.target) ?? 0) + 1);
    }
    const eligible = sourceNodes.filter((node) =>
      filter === "At Risk Nodes" ? node.status !== "normal" :
      filter === "High Traffic" ? (degree.get(node.id) ?? 0) > 0 : true
    );
    const score = (node: UINode) =>
      (degree.get(node.id) ?? 0) * 3 + node.threatScore / 10 + Math.log1p(Math.max(0, node.activity));
    const ranked = [...eligible].sort((a, b) => score(b) - score(a) || a.id.localeCompare(b.id));
    const eligibleById = new Map(eligible.map((node) => [node.id, node]));
    const rankedLinks = sourceLinks.filter((link) =>
      link.source !== link.target && eligibleById.has(link.source) && eligibleById.has(link.target)
    ).sort((a, b) => {
      const linkScore = (link: UILink) =>
        score(eligibleById.get(link.source)!) + score(eligibleById.get(link.target)!) +
        (link.type === "suspicious" ? 20 : 0);
      return linkScore(b) - linkScore(a) || a.id.localeCompare(b.id);
    });
    // Pick connected endpoints together so the overview actually contains
    // observed communication, even when most endpoints have only one edge.
    const picked: UINode[] = [];
    const pickedIds = new Set<string>();
    for (const link of rankedLinks) {
      const additions = [link.source, link.target].filter((id) => !pickedIds.has(id));
      if (picked.length + additions.length > 12) continue;
      for (const id of additions) { picked.push(eligibleById.get(id)!); pickedIds.add(id); }
      if (picked.length === 12) break;
    }
    for (const node of ranked) {
      if (picked.length === 12) break;
      if (!pickedIds.has(node.id)) { picked.push(node); pickedIds.add(node.id); }
    }
    // Keep the selected host visible even when it is outside the top ranks.
    if (selectedNodeId && !picked.some((node) => node.id === selectedNodeId)) {
      const selected = eligible.find((node) => node.id === selectedNodeId);
      if (selected) picked.splice(Math.max(0, picked.length - 1), 1, selected);
    }
    const central = picked.find((node) => (degree.get(node.id) ?? 0) >= 3);
    if (central && picked[0].id !== central.id) {
      picked.splice(picked.indexOf(central), 1);
      picked.unshift(central);
    }
    const placed = picked.map((node, index) => {
      if (picked.length === 1) return { ...node, x: 425, y: 195 };
      if (picked.length <= 3) return { ...node, x: picked.length === 2 ? [215, 635][index] : [160, 425, 690][index], y: 195 };
      if (central && index === 0) return { ...node, x: 425, y: 195 };
      const ringIndex = central ? index - 1 : index;
      const ringCount = central ? picked.length - 1 : picked.length;
      const angle = 2 * Math.PI * ringIndex / ringCount - Math.PI / 2;
      return { ...node, x: 425 + 300 * Math.cos(angle), y: 195 + 125 * Math.sin(angle) };
    });
    const visibleIds = new Set(placed.map((node) => node.id));
    const unique = new Set<string>();
    const visibleLinks = sourceLinks.filter((link) => {
      if (!visibleIds.has(link.source) || !visibleIds.has(link.target) || link.source === link.target) return false;
      const key = `${link.source}|${link.target}|${link.protocol}|${link.port ?? ""}`;
      if (unique.has(key)) return false;
      unique.add(key);
      return true;
    }).sort((a, b) => Number(b.type === "suspicious") - Number(a.type === "suspicious"))
      .slice(0, 24);
    return { graphNodes: placed, graphLinks: visibleLinks, eligibleCount: eligible.length };
  }, [sourceNodes, sourceLinks, filter, selectedNodeId]);
  const nodeById = useMemo(() => new Map(graphNodes.map((node) => [node.id, node])), [graphNodes]);

  const fmtBytes = (n: number) => {
    if (n > 1e9) return `${(n / 1e9).toFixed(1)}GB`;
    if (n > 1e6) return `${(n / 1e6).toFixed(1)}MB`;
    if (n > 1e3) return `${(n / 1e3).toFixed(1)}KB`;
    return `${Math.round(n)}B`;
  };

  return (
    <div className={`bg-white border border-[#EAE6DF] rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between overflow-hidden transition-all ${
      isFullscreen ? "fixed inset-6 z-50 shadow-2xl" : "h-full min-h-[460px]"}`}>
      <div className="px-5 py-3.5 border-b border-[#F0ECE4] flex flex-wrap items-center justify-between gap-2">
        <div className="min-w-0 flex flex-wrap items-center gap-2.5">
          <Share2 className="w-4 h-4 text-[#DE5B49]" />
          <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Network &amp; System View</h2>
          {shownWindowLabel && <span className="text-[10px] text-[#98A2AF] font-mono">{shownWindowLabel}</span>}
        </div>
        <div className="min-w-0 flex flex-wrap items-center gap-2.5">
          <div className="flex items-center bg-[#F4F1EB] p-0.5 rounded-lg border border-[#E4DFD6] text-xs font-semibold">
            <button onClick={() => setIsLive(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md transition-all ${isLive ? "bg-white text-[#1C232B] shadow-sm" : "text-[#7C8898] hover:text-[#1C232B]"}`}>
              <span className={`w-2 h-2 rounded-full ${isLive ? "bg-[#2EAA58] animate-pulse" : "bg-stone-400"}`} />
              <span>Live</span>
            </button>
            <button onClick={() => { setSnapshot({ nodes, links, windowLabel }); setIsLive(false); }}
              className={`px-2.5 py-1 rounded-md transition-all ${!isLive ? "bg-white text-[#1C232B] shadow-sm" : "text-[#7C8898] hover:text-[#1C232B]"}`}>
              Snapshot
            </button>
          </div>
          <select value={filter} onChange={(e) => setFilter(e.target.value)}
            className="bg-[#FAF8F5] border border-[#DDD6CC] text-xs font-semibold text-[#3C4755] px-2.5 py-1.5 rounded-lg focus:outline-none focus:ring-1 focus:ring-[#DE5B49]"
            aria-label="Filter nodes">
            <option>All Nodes</option>
            <option>At Risk Nodes</option>
            <option>High Traffic</option>
          </select>
          <button onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 text-[#7C8898] hover:text-[#1C232B] hover:bg-[#F4F1EB] rounded-lg transition-colors"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}>
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="relative flex-1 w-full bg-[#FAF9F6]/50 min-h-[340px] flex items-center justify-center p-2 overflow-hidden">
        {graphNodes.length === 0 ? (
          <div className="text-center max-w-sm">
            <Share2 className="w-10 h-10 text-[#D4CBBF] mx-auto mb-3" />
            <div className="text-sm font-bold text-[#3C4755]">{sourceNodes.length ? "No nodes match this filter" : "No network state yet"}</div>
            <p className="text-xs text-[#7A8696] mt-1 leading-relaxed">
              {sourceNodes.length ? "Choose another node filter to inspect this window." : "Import a PCAP or CSV to display the latest observed communication window."}
            </p>
          </div>
        ) : (
          <svg viewBox="0 0 850 480" className="w-full h-full max-h-[440px] select-none" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Network topology">
            <defs>
              <marker id="arrow-traffic" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#9BA5B2" />
              </marker>
              <marker id="arrow-suspicious" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#DE5B49" />
              </marker>
            </defs>

            {graphLinks.map((link) => {
              const start = nodeById.get(link.source);
              const end = nodeById.get(link.target);
              if (!start || !end) return null;
              const suspicious = link.type === "suspicious";
              const isHovered = hovered === link.source || hovered === link.target;
              const pathData = `M ${start.x} ${start.y} L ${end.x} ${end.y}`;
              return (
                <g key={link.id}>
                  <path d={pathData} fill="none" stroke={suspicious ? "#DE5B49" : "#A9B3BE"}
                    strokeWidth={isHovered ? 2.8 : suspicious ? 2 : 1.5}
                    strokeDasharray={suspicious ? "6,5" : "none"}
                    strokeOpacity={isHovered ? 1 : suspicious ? 0.95 : 0.65}
                    markerEnd={suspicious ? "url(#arrow-suspicious)" : "url(#arrow-traffic)"}
                    />
                </g>
              );
            })}

            {graphNodes.map((node) => {
              const isDefended = defendedNodeIds?.has(node.id);
              const effectiveStatus = isDefended ? "normal" : node.status;
              const effectiveThreatScore = isDefended ? 5 : node.threatScore;
              const colors = isDefended
                ? { bg: "#1E7A43", border: "#166534", glow: "rgba(30,122,67,0.3)" }
                : (STATUS_COLORS[effectiveStatus] ?? STATUS_COLORS.normal);
              const isCompromised = effectiveStatus === "compromised";
              const isSelected = selectedNodeId === node.id;
              const isHovered = hovered === node.id;
              const hasGravity = node.gravity !== undefined && node.gravity > 0.02;
              return (
                <g key={node.id} transform={`translate(${node.x}, ${node.y})`} className="cursor-pointer group"
                  onClick={() => onSelectNode(node)} onMouseEnter={() => setHovered(node.id)} onMouseLeave={() => setHovered(null)}>
                  {(isCompromised || isSelected || hasGravity || isDefended) && (
                    <circle r="28" fill={isDefended ? colors.glow : (hasGravity && !isCompromised ? "rgba(229,139,68,0.25)" : colors.glow)} />
                  )}
                  {isSelected && <circle r="26" fill="none" stroke={isDefended ? "#1E7A43" : "#DE5B49"} strokeWidth="2" strokeDasharray="4,2" />}
                  <circle r={hasGravity ? 23 : 21} fill={colors.bg} stroke={colors.border} strokeWidth="2.5"
                    className="filter drop-shadow-md" />
                  <text y="5" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#F7F5F0" className="pointer-events-none select-none font-mono">
                    {node.id.includes(".") ? node.id.split(".").at(-1) : node.id.slice(0, 4)}
                  </text>
                  <text y="38" textAnchor="middle" className="pointer-events-none select-none" fontSize="11" fontWeight="bold" fill="#19222C">
                    {node.name}
                  </text>
                  <text y="51" textAnchor="middle" className="pointer-events-none select-none font-mono" fontSize="9.5" fill={isDefended ? "#1E7A43" : "#717E8E"}>
                    {isDefended ? "defended (5)" : `risk ${effectiveThreatScore}`}
                    {!isDefended && node.gravity !== undefined && node.gravity > 0.02 ? ` · grav ${node.gravity.toFixed(2)}` : ""}
                  </text>
                  {isCompromised && !isDefended && (
                    <g transform="translate(14, -17)">
                      <circle r="7" fill="#DE5B49" stroke="#FFFFFF" strokeWidth="1.5" />
                      <text y="3" textAnchor="middle" fill="#FFFFFF" fontSize="9" fontWeight="bold">!</text>
                    </g>
                  )}
                  {isDefended && (
                    <g transform="translate(14, -17)">
                      <circle r="7.5" fill="#1E7A43" stroke="#FFFFFF" strokeWidth="1.5" />
                      <path d="M -3 0 L -1 2 L 3 -2" fill="none" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </g>
                  )}
                  {isHovered && (
                    <g transform="translate(0, -34)" className="pointer-events-none">
                      <rect x="-46" y="-14" width="92" height="18" rx="5" fill="#1C2229" opacity="0.92" />
                      <text y="-2" textAnchor="middle" fontSize="9" fill="#F7F5F0" className="font-mono">
                        {fmtBytes(node.activity * 1e6)}
                      </text>
                    </g>
                  )}
                </g>
              );
            })}
          </svg>
        )}

        {/* Floating Quick Action HUD for compromised / high-risk target node */}
        {(() => {
          const targetNode =
            graphNodes.find((n) => n.id === selectedNodeId) ||
            graphNodes.find((n) => n.id === hovered) ||
            graphNodes.find((n) => (n.status === "compromised" || n.threatScore >= 50) && !defendedNodeIds?.has(n.id));
          if (!targetNode || (targetNode.threatScore < 45 && targetNode.status === "normal")) return null;
          const isDefended = defendedNodeIds?.has(targetNode.id);

          return (
            <div className="absolute bottom-2 left-3 right-3 bg-white/95 backdrop-blur-md border border-[#EAE2D8] rounded-xl p-2 shadow-lg flex flex-wrap items-center justify-between gap-2 z-10 animate-in fade-in slide-in-from-bottom-1">
              <div className="flex items-center gap-2 min-w-0">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-mono text-[11px] font-bold shrink-0 ${isDefended ? "bg-[#E9F6EC] border border-[#C8E6CF] text-[#1E7A43]" : "bg-[#FAF0ED] border border-[#F4D0C9] text-[#DE5B49]"}`}>
                  {targetNode.id.split('.').slice(-1)[0]}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-mono font-bold text-xs text-[#1C232B]">{targetNode.id}</span>
                    {isDefended ? (
                      <span className="px-1.5 py-0.2 rounded text-[8px] font-bold uppercase bg-[#E9F6EC] text-[#1E7A43] border border-[#C8E6CF]">
                        DEFENDED · RISK 5
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.2 rounded text-[8px] font-bold uppercase bg-[#FDF2F0] text-[#DE5B49] border border-[#F9DCD7]">
                        RISK {targetNode.threatScore}/100 · {targetNode.status.toUpperCase()}
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-[#7A8696] truncate">
                    High-risk node &bull; Take to Parallel Futures, attack with Strix in sandbox, or 1-click defend with AI patch.
                  </div>
                </div>
              </div>

              <div className="min-w-0 flex flex-wrap items-center gap-1.5">
                <button
                  onClick={(e) => { e.stopPropagation(); onTakeToParallelFutures?.(targetNode); }}
                  className="px-2 py-1 bg-[#FAF6F2] hover:bg-[#F4ECE2] text-[#4F5968] border border-[#DDD6CC] rounded-lg text-[11px] font-semibold flex items-center gap-1 transition-colors cursor-pointer"
                  title="Simulate isolating this host in Parallel Futures"
                >
                  <GitBranch className="w-3 h-3 text-[#E58B44]" />
                  <span>Parallel Futures</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onAttackWithStrix?.(targetNode); }}
                  className="px-2 py-1 bg-[#FAF0ED] hover:bg-[#F7DDD7] text-[#DE5B49] border border-[#F4D0C9] rounded-lg text-[11px] font-bold flex items-center gap-1 transition-colors cursor-pointer"
                  title="Attack this host in isolated sandbox with Strix"
                >
                  <Zap className="w-3 h-3 fill-[#DE5B49]" />
                  <span>Strix Sandbox</span>
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); onSelectNode(targetNode); onSuggestPatch?.(targetNode); }}
                  className="px-2.5 py-1 bg-[#1E7A43] hover:bg-[#176636] text-white rounded-lg text-[11px] font-bold flex items-center gap-1 shadow-sm transition-colors cursor-pointer"
                  title="Suggest AI patch and defend"
                >
                  <ShieldCheck className="w-3 h-3" />
                  <span>Suggest Patch &amp; Defend</span>
                </button>
              </div>
            </div>
          );
        })()}

        <div className="absolute top-3 left-4 right-4 sm:right-auto bg-white/90 border border-[#E8E2D8] px-2.5 py-1 rounded-md text-[10px] text-[#7A8492] shadow-xs pointer-events-none">
          {eligibleCount > graphNodes.length
            ? `Showing ${graphNodes.length} of ${eligibleCount} matching endpoints · ${graphLinks.length} representative flows`
            : "Click any node to inspect it, run the explainer, or simulate containment"}
        </div>
      </div>

      <div className="px-5 py-3 border-t border-[#F0ECE4] bg-white flex flex-wrap items-center justify-between text-xs text-[#505C6B]">
        <div className="flex flex-wrap items-center gap-2 sm:gap-5">
          {[["#DE5B49", "Critical"], ["#D9654C", "High Risk"], ["#E58B44", "Medium Risk"], ["#2B3B4C", "Normal"]].map(([c, label]) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />
              <span className="text-[11px] font-medium text-[#29323D]">{label}</span>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-6 mt-1 sm:mt-0">
          <div className="flex items-center gap-2">
            <div className="w-6 h-0.5 bg-[#8E99A8] relative"><span className="absolute -right-1 -top-[3px] border-solid border-l-[#8E99A8] border-l-4 border-y-transparent border-y-2 border-r-0" /></div>
            <span className="text-[11px] font-medium text-[#505C6B]">Observed Flow</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-7 h-0.5 border-t-2 border-dashed border-[#DE5B49] relative"><span className="absolute -right-1 -top-[4px] border-solid border-l-[#DE5B49] border-l-4 border-y-transparent border-y-2 border-r-0" /></div>
            <span className="text-[11px] font-medium text-[#DE5B49] font-semibold">Sensitive Port (22/445/3389)</span>
          </div>
        </div>
      </div>
    </div>
  );
};
