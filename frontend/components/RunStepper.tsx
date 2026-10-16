import React from 'react';
import { Check, ShieldCheck, Sparkles } from 'lucide-react';

interface RunStepperProps {
  currentStep: 'upload' | 'review' | 'results';
}

export default function RunStepper({ currentStep }: RunStepperProps) {
  const steps = [
    { id: 'upload', number: '01', title: 'Upload & Ingest', desc: 'Schema discovery & dry-run' },
    { id: 'review', number: '02', title: 'Pre-flight Approval', desc: 'AI rationale & human sign-off' },
    { id: 'results', number: '03', title: 'Case File & Audit', desc: 'Fairness, drift & NIST controls' },
  ];

  const getStepIndex = (step: string) => {
    if (step === 'upload') return 0;
    if (step === 'review') return 1;
    return 2;
  };

  const currentIndex = getStepIndex(currentStep);

  return (
    <nav aria-label="Audit Pipeline Progress" className="w-full pb-6 mb-6 border-b border-rule">
      <ol className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {steps.map((step, idx) => {
          const isDone = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          return (
            <li
              key={step.id}
              className={`p-3.5 rounded-xl border transition-all flex items-center space-x-3.5 ${
                isCurrent
                  ? 'bg-emerald-500/[0.08] border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/30'
                  : isDone
                  ? 'bg-white/[0.02] border-emerald-500/20 text-ink-soft'
                  : 'bg-white/[0.01] border-rule opacity-60 text-ink-soft'
              }`}
            >
              <div
                className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono text-xs font-bold transition-all shrink-0 ${
                  isDone
                    ? 'bg-emerald-500 text-slate-950 shadow-[0_0_12px_rgba(16,185,129,0.4)]'
                    : isCurrent
                    ? 'bg-gradient-to-tr from-emerald-500 to-cyan-400 text-slate-950 font-extrabold shadow-[0_0_15px_rgba(16,185,129,0.5)]'
                    : 'bg-slate-800 border border-white/10 text-slate-400'
                }`}
              >
                {isDone ? <Check className="w-4 h-4 stroke-[3]" /> : step.number}
              </div>
              <div className="flex flex-col">
                <span
                  className={`text-xs font-bold tracking-tight ${
                    isCurrent ? 'text-white' : isDone ? 'text-slate-300' : 'text-slate-400'
                  }`}
                >
                  {step.title}
                </span>
                <span className="text-[11px] text-ink-soft">{step.desc}</span>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
