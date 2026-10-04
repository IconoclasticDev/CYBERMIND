import React from "react";
import {
  Home, Activity, TrendingUp, GitBranch, Share2, PlayCircle, FileText,
  BookOpen, Settings, Zap, Database, BarChart2,
} from "lucide-react";
import type { HealthResponse, ScenarioInfo } from "../lib/api";

export type SidebarTab =
  | "command-center" | "attack-lab" | "live-monitor" | "threat-forecast" | "parallel-forecast"
  | "attack-graph" | "scenario-lab" | "replay-analysis" | "reports"
  | "knowledge-base" | "settings" | "flagged-flows" | "benchmark";

interface SidebarProps {
  currentTab: SidebarTab;
  onTabChange: (tab: SidebarTab) => void;
  health: HealthResponse | null;
  scenarios: ScenarioInfo[];
  activeScenarioId?: string | null;
  scenarioRunning: boolean;
  onStartScenario: (id: string) => void;
  onStopScenario: () => void;
  onResetScenario: () => void;
  onLoadTestCase?: (id: string) => void;
  activeTestCaseId?: string | null;
  testCaseBusy?: boolean;
}

type NavGroup = {
  label: string;
  items: Array<{ id: SidebarTab; label: string; icon: React.FC<{ className?: string }>; badge?: string }>;
};

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Core",
    items: [
      { id: "command-center", label: "Command Center", icon: Home },
      { id: "live-monitor", label: "Live Monitor", icon: Activity },
      { id: "flagged-flows", label: "Flagged Flows", icon: Database, badge: "B.2" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { id: "threat-forecast", label: "Threat Forecast", icon: TrendingUp },
      { id: "parallel-forecast", label: "Parallel Futures", icon: GitBranch },
      { id: "attack-graph", label: "Attack Graph", icon: Share2 },
      { id: "benchmark", label: "Benchmark", icon: BarChart2, badge: "Track A" },
    ],
  },
  {
    label: "Labs",
    items: [
      { id: "attack-lab", label: "Attack Labs (Strix)", icon: Zap, badge: "AI PATCH" },
      { id: "replay-analysis", label: "Replay & Analysis", icon: PlayCircle },
    ],
  },
  {
    label: "Config",
    items: [
      { id: "reports", label: "Reports", icon: FileText },
      { id: "knowledge-base", label: "Knowledge Base", icon: BookOpen },
      { id: "settings", label: "Settings", icon: Settings },
    ],
  },
];

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab, onTabChange,
}) => {
  return (
    <aside className="w-64 bg-[#F7F5F0] border-r border-[#EAE6DF] h-[calc(100vh-61px)] sticky top-[61px] overflow-y-auto flex flex-col justify-between p-3 select-none shrink-0">
      <div className="space-y-3">

        {/* Grouped Nav */}
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="text-[9px] font-bold text-[#A0AAB8] px-2.5 mb-1 uppercase tracking-widest">
              {group.label}
            </div>
            <nav className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const isActive = currentTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => onTabChange(item.id)}
                    aria-current={isActive ? "page" : undefined}
                    className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? "bg-[#EAE2D8] text-[#1A222B] shadow-[0_1px_2px_rgba(0,0,0,0.04)] font-semibold"
                        : "text-[#586474] hover:bg-[#EFECE5] hover:text-[#1A222B]"
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-[#DE5B49]" : item.id === "attack-lab" ? "text-[#DE5B49]" : "text-[#7C8898]"}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="text-[8px] font-mono font-bold bg-[#FAF0ED] text-[#C54737] border border-[#F4D0C9] px-1 py-0.5 rounded shrink-0">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>
        ))}


      </div>

    </aside>
  );
};
