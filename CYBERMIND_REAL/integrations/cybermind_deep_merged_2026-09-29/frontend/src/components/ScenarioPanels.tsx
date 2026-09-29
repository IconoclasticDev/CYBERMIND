import React, { useEffect, useRef, useState } from "react";
import { FlaskConical, Check, ChevronDown, Play, Square, RotateCcw, X } from "lucide-react";
import type { HealthResponse, ScenarioInfo } from "../lib/api";

const DURATION = "5s / tick";

export const ScenarioLabCard: React.FC<{
  health: HealthResponse | null;
  scenarios: ScenarioInfo[];
  isRunning: boolean;
  currentId: string | null;
  onToggleRunning: () => void;
  onReset: () => void;
  onPick: (id: string) => void;
}> = ({ health, scenarios, isRunning, currentId, onToggleRunning, onReset, onPick }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menuOpen) return;
    const closeOutside = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) setMenuOpen(false);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [menuOpen]);
  const current = scenarios.find((s) => s.id === currentId);
  const steps = [
    { id: "setup", label: "Setup", done: true },
    { id: "attack", label: "Telemetry", done: (health?.telemetry_events ?? 0) > 0 },
    { id: "telemetry", label: "Windows", done: (health?.state_windows ?? 0) >= 3 },
    { id: "analysis", label: "Forecast", done: (health?.state_windows ?? 0) >= 3 && !!health?.model?.available },
  ];
  return (
    <div className={`relative bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between min-h-[270px] h-full ${menuOpen ? "z-30" : "z-0"}`}>
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-[#DE5B49]"><FlaskConical className="w-4 h-4" /></div>
            <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">Scenario Lab</h2>
          </div>
          <div className={`flex items-center gap-1.5 border px-2 py-0.5 rounded-full text-[10px] font-semibold ${
            isRunning ? "bg-[#E8F7ED] border-[#C6EBD1] text-[#248B47]" : "bg-stone-100 border-stone-200 text-stone-500"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-[#2EAA58] animate-pulse" : "bg-stone-400"}`} />
            <span>{isRunning ? "Active" : "Idle"}</span>
          </div>
        </div>

        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${isRunning ? "bg-[#2EAA58]" : "bg-stone-300"}`} />
            <span className="text-xs font-bold text-[#1F2731]">{current?.name ?? "No scenario selected"}</span>
          </div>
          <div className="text-[11px] text-[#7A8696] font-mono mt-0.5 ml-4">
            SYNTHETIC LAB · tick {health?.scenario?.tick ?? 0} · {DURATION}
          </div>
        </div>

        <div className="relative mt-5 px-1">
          <div className="absolute top-2.5 left-4 right-4 h-0.5 bg-[#E6E0D5] z-0" />
          <div className="relative z-10 grid grid-cols-4 gap-1 text-center">
            {steps.map((step) => (
              <div key={step.id} className="flex flex-col items-center">
                <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
                  step.done ? "bg-[#2EAA58] text-white" : "border-2 border-[#D1C9BE] bg-white text-[#A0AAB8]"}`}>
                  {step.done ? <Check className="w-3 h-3 stroke-[3]" /> : ""}
                </div>
                <span className="text-[10px] font-medium text-[#7C8898] mt-1.5">{step.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2.5 mt-5 pt-3 border-t border-[#F2ECE4]">
        <button onClick={onToggleRunning}
          className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors ${
            isRunning ? "bg-[#DE5B49] hover:bg-[#C94735] text-white" : "bg-[#2EAA58] hover:bg-[#25944B] text-white"}`}>
          {isRunning ? <><Square className="w-3 h-3 fill-current" /><span>Stop Scenario</span></> : <><Play className="w-3 h-3 fill-current" /><span>Resume Scenario</span></>}
        </button>
        <button onClick={onReset} className="py-2 px-3 bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#424F60] rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors">
          <RotateCcw className="w-3 h-3" /><span>Reset</span>
        </button>
      </div>
      <div ref={menuRef} className="relative mt-2">
        <button ref={triggerRef} type="button" aria-label="Select scenario" aria-haspopup="listbox" aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
          className="w-full flex items-center justify-between gap-2 bg-[#FAF8F5] border border-[#DDD6CC] text-xs font-semibold text-[#3C4755] px-2.5 py-1.5 rounded-lg hover:border-[#C9BBA9] focus:outline-none focus:ring-1 focus:ring-[#DE5B49]">
          <span className="truncate">{current?.name ?? "Choose a scenario…"}</span>
          <ChevronDown className={`w-3.5 h-3.5 shrink-0 transition-transform ${menuOpen ? "rotate-180" : ""}`} />
        </button>
        {menuOpen && <div role="listbox" aria-label="Scenarios"
          className="absolute z-40 bottom-full left-0 right-0 mb-1 max-h-56 overflow-y-auto rounded-lg border border-[#DDD6CC] bg-white p-1 shadow-lg">
          {scenarios.map((scenario) => <button key={scenario.id} type="button" role="option" aria-selected={currentId === scenario.id}
            onClick={() => { onPick(scenario.id); setMenuOpen(false); triggerRef.current?.focus(); }}
            className={`block w-full rounded-md px-2.5 py-2 text-left text-xs font-medium leading-tight ${currentId === scenario.id ? "bg-[#FAF0EC] text-[#B94736]" : "text-[#3C4755] hover:bg-[#FAF8F5]"}`}>
            {scenario.name}
          </button>)}
        </div>}
      </div>
      <div className="mt-3 pt-3 border-t border-[#F2ECE4] flex flex-wrap items-center justify-between gap-2">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8796]">Real Flow Samples</span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => onPick("botnet_ares_real")}
            title="Stream real Ares Botnet logs"
            className="text-[10px] font-bold bg-[#FAF6F2] hover:bg-[#F5ECE0] text-[#DE5B49] border border-[#EBD8C6] px-2 py-0.5 rounded transition-colors"
          >
            Botnet Ares
          </button>
          <button
            onClick={() => onPick("ssh_bruteforce_real")}
            title="Stream real SSH Brute Force logs"
            className="text-[10px] font-bold bg-[#FAF8F5] hover:bg-[#F2ECE0] text-[#8C5424] border border-[#E8DCCB] px-2 py-0.5 rounded transition-colors"
          >
            SSH Brute
          </button>
        </div>
      </div>
    </div>
  );
};

export const ScenarioLabModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  scenarios: ScenarioInfo[];
  isRunning: boolean;
  currentId: string | null;
  onStart: (id: string, interval: number) => void;
  onStop: () => void;
  onReset: () => void;
}> = ({ isOpen, onClose, scenarios, isRunning, currentId, onStart, onStop, onReset }) => {
  const [interval, setInterval] = useState(1.5);
  useEffect(() => { if (!isOpen) return; }, [isOpen]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" role="dialog" aria-modal="true">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-[#DFD8CC] overflow-hidden flex flex-col max-h-[88vh]">
        <div className="p-4 border-b border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#DE5B49] flex items-center justify-center text-white"><FlaskConical className="w-4 h-4" /></div>
            <div>
              <h3 className="font-bold text-sm text-[#1C232B]">CYBERMIND Scenario Simulation Lab</h3>
              <div className="text-[11px] text-[#7A8696]">CIC-IDS2018 attack emulation · real trained model verification</div>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#EFEAE2] text-[#8692A2] hover:text-[#1C232B] transition-colors" aria-label="Close"><X className="w-4 h-4" /></button>
        </div>

        <div className="p-6 overflow-y-auto space-y-4 text-xs">
          <div className="bg-[#FAF9F6] border border-[#EDE7DE] rounded-xl p-4 flex items-center justify-between">
            <div>
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#7C8796]">Active Emulation</span>
              <div className="font-bold text-stone-900 text-sm mt-0.5">
                {scenarios.find((s) => s.id === currentId)?.name ?? "None"}
              </div>
              <div className="text-[11px] text-[#556172] mt-0.5">
                Status: <span className={isRunning ? "text-[#2EAA58] font-bold" : "text-stone-500 font-bold"}>{isRunning ? "Running (SYNTHETIC LAB)" : "Idle"}</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-[10px] font-semibold text-[#7C8796] uppercase">tick
                <input type="range" min="0.4" max="4" step="0.2" value={interval} onChange={(e) => setInterval(parseFloat(e.target.value))} className="ml-2 accent-[#DE5B49]" />
                <span className="ml-1 font-mono">{interval}s</span>
              </label>
              {isRunning ? (
                <button onClick={onStop} className="px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-colors bg-[#DE5B49] hover:bg-[#C94735]">Stop</button>
              ) : (
                currentId && <button onClick={() => onStart(currentId, interval)} className="px-3 py-1.5 rounded-lg text-xs font-bold text-white transition-colors bg-[#2EAA58] hover:bg-[#25944B]">Start</button>
              )}
              <button onClick={onReset} className="px-3 py-1.5 bg-white border border-[#DDD6CC] hover:bg-stone-50 text-stone-700 rounded-lg text-xs font-bold">Reset</button>
            </div>
          </div>

          <div>
            <div className="text-[11px] font-semibold text-[#8C96A3] uppercase tracking-wider mb-2.5">Preset Scenarios (CIC-IDS2018 Kill Chains)</div>
            <div className="space-y-2.5">
              {scenarios.map((sc) => {
                const isSelected = currentId === sc.id;
                return (
                  <button key={sc.id} onClick={() => onStart(sc.id, interval)} disabled={isRunning}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all cursor-pointer disabled:cursor-not-allowed ${
                      isSelected ? "bg-[#FAF6F2] border-[#DE5B49] shadow-xs" : "bg-white border-[#EDE7DE] hover:border-[#D9CFBF] hover:bg-[#FAF9F6]"} ${isRunning && !isSelected ? "opacity-50" : ""}`}>
                    <div className="flex items-center justify-between">
                      <div className="font-bold text-[#1C232B] text-xs flex items-center gap-2">
                        {isSelected && <span className="w-2 h-2 rounded-full bg-[#DE5B49]" />}
                        <span>{sc.name}</span>
                      </div>
                      <span className="text-[10px] font-medium text-stone-500 font-mono">{sc.duration_ticks} ticks</span>
                    </div>
                    <p className="mt-1.5 text-[#556171] leading-relaxed text-[11px]">{sc.description}</p>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        <div className="p-4 border-t border-[#EDE6DC] bg-[#FAF8F5] flex items-center justify-between">
          <span className="text-[11px] text-[#768292]">Active telemetry pipeline · local only · SYNTHETIC LAB</span>
          <button onClick={onClose} className="px-4 py-1.5 bg-[#DE5B49] hover:bg-[#C94838] text-white rounded-lg text-xs font-bold shadow-xs">Apply &amp; Return</button>
        </div>
      </div>
    </div>
  );
};
