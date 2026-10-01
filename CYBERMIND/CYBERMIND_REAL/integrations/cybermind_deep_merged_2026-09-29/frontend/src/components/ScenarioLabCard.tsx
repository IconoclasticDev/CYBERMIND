import React from 'react';
import { FlaskConical, Check, Play, Square, RotateCcw } from 'lucide-react';

interface ScenarioLabCardProps {
  scenarioName?: string;
  timer?: string;
  isRunning: boolean;
  onToggleRunning: () => void;
  onReset: () => void;
}

export const ScenarioLabCard: React.FC<ScenarioLabCardProps> = ({
  scenarioName = 'Lateral Movement (SMB)',
  timer = '4m 32s',
  isRunning,
  onToggleRunning,
  onReset
}) => {
  const steps = [
    { id: 'setup', label: 'Setup', status: 'completed' },
    { id: 'attack', label: 'Attack', status: 'completed' },
    { id: 'telemetry', label: 'Telemetry', status: 'completed' },
    { id: 'analysis', label: 'Analysis', status: isRunning ? 'active' : 'pending' }
  ];

  return (
    <div className="bg-white border border-[#EAE6DF] rounded-2xl p-5 shadow-[0_1px_3px_rgba(0,0,0,0.02)] flex flex-col justify-between h-full">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-[#DE5B49]">
              <FlaskConical className="w-4 h-4" />
            </div>
            <h2 className="text-sm font-bold text-[#1C232B] tracking-tight">
              Scenario Lab
            </h2>
          </div>

          <div className="flex items-center gap-1.5 bg-[#E8F7ED] border border-[#C6EBD1] px-2 py-0.5 rounded-full text-[10px] font-semibold text-[#248B47]">
            <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? 'bg-[#2EAA58] animate-pulse' : 'bg-stone-400'}`} />
            <span>{isRunning ? 'Active' : 'Paused'}</span>
          </div>
        </div>

        {/* Scenario status details */}
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#2EAA58]" />
            <span className="text-xs font-bold text-[#1F2731]">
              {scenarioName}
            </span>
          </div>
          <div className="text-[11px] text-[#7A8696] font-mono mt-0.5 ml-4">
            {isRunning ? 'Running' : 'Paused'} <span className="mx-1">·</span> {timer}
          </div>
        </div>

        {/* 4-step progress track */}
        <div className="relative mt-5 px-1">
          {/* Background horizontal line */}
          <div className="absolute top-2.5 left-4 right-4 h-0.5 bg-[#E6E0D5] z-0" />
          
          <div className="relative z-10 grid grid-cols-4 gap-1 text-center">
            {steps.map((step) => {
              const isCompleted = step.status === 'completed';
              const isActive = step.status === 'active';
              return (
                <div key={step.id} className="flex flex-col items-center">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold transition-all ${
                      isCompleted
                        ? 'bg-[#2EAA58] text-white'
                        : isActive
                        ? 'border-2 border-[#2EAA58] bg-white text-[#2EAA58] animate-pulse'
                        : 'border-2 border-[#D1C9BE] bg-white text-[#A0AAB8]'
                    }`}
                  >
                    {isCompleted ? <Check className="w-3 h-3 stroke-[3]" /> : ''}
                  </div>
                  <span className="text-[10px] font-medium text-[#7C8898] mt-1.5">
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-2 gap-2.5 mt-5 pt-3 border-t border-[#F2ECE4]">
        <button
          onClick={onToggleRunning}
          className={`py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors ${
            isRunning
              ? 'bg-[#DE5B49] hover:bg-[#C94735] text-white'
              : 'bg-[#2EAA58] hover:bg-[#25944B] text-white'
          }`}
        >
          {isRunning ? (
            <>
              <Square className="w-3 h-3 fill-current" />
              <span>Stop Scenario</span>
            </>
          ) : (
            <>
              <Play className="w-3 h-3 fill-current" />
              <span>Resume Scenario</span>
            </>
          )}
        </button>

        <button
          onClick={onReset}
          className="py-2 px-3 bg-[#FAF8F5] hover:bg-[#EFEAE2] border border-[#DDD6CC] text-[#424F60] rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset</span>
        </button>
      </div>
    </div>
  );
};
