'use client';

import React, { useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { fetchRun } from '../../../lib/api';
import { Loader2, AlertCircle, XCircle } from 'lucide-react';
import RunStepper from '../../../components/RunStepper';

export default function RunStatusRouter() {
  const params = useParams();
  const router = useRouter();
  const runId = params.id as string;

  const { data: run, error, isLoading } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => fetchRun(runId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'validating' || status === 'running') return 1500;
      return false;
    },
  });

  useEffect(() => {
    if (!run) return;
    if (run.status === 'awaiting_approval') {
      router.replace(`/runs/${runId}/review`);
    } else if (run.status === 'completed') {
      router.replace(`/runs/${runId}/summary`);
    }
  }, [run, runId, router]);

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-verdigris" />
        <p className="text-sm font-mono text-ink-soft">Loading audit case file {runId}...</p>
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="py-16 max-w-lg mx-auto bg-sheet border border-oxide/30 rounded p-6 text-center space-y-3">
        <AlertCircle className="w-8 h-8 text-oxide mx-auto" />
        <h2 className="text-base font-bold text-ink">Audit Run Not Found</h2>
        <p className="text-xs text-ink-soft">
          Unable to retrieve run record with identifier <span className="font-mono">{runId}</span>.
        </p>
        <button
          onClick={() => router.push('/')}
          className="mt-2 px-4 py-2 bg-paper border border-rule text-xs font-semibold rounded hover:bg-sheet text-ink"
        >
          Return to Upload
        </button>
      </div>
    );
  }

  // Running state with live stage progress
  if (run.status === 'running' || run.status === 'validating') {
    return (
      <div className="space-y-6">
        <RunStepper currentStep="results" />
        <div className="max-w-xl mx-auto py-16 bg-sheet border border-rule rounded p-8 text-center space-y-5">
          <div className="w-12 h-12 rounded-full bg-verdigris/10 border border-verdigris/30 flex items-center justify-center mx-auto text-verdigris">
            <Loader2 className="w-6 h-6 animate-spin" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-ink">Executing Audit Pipeline</h2>
            <p className="text-xs text-ink-soft font-mono">Run ID: {run.run_id}</p>
          </div>

          <div className="p-3 bg-paper border border-rule rounded text-left space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-ink-soft">Active Stage:</span>
              <span className="font-semibold text-verdigris capitalize font-mono">
                {run.stage || 'Initializing Statistical Engines...'}
              </span>
            </div>
            <div className="w-full bg-rule/50 h-1.5 rounded-full overflow-hidden">
              <div className="bg-verdigris h-full w-2/3 animate-pulse" />
            </div>
          </div>

          <p className="text-xs text-ink-soft">
            Testing disparity metrics, computing z-score anomaly clusters, and mapping NIST AI RMF controls...
          </p>
        </div>
      </div>
    );
  }

  // Rejected or failed state
  return (
    <div className="space-y-6">
      <RunStepper currentStep="review" />
      <div className="max-w-xl mx-auto py-12 bg-sheet border border-oxide/30 rounded p-8 text-center space-y-4">
        <XCircle className="w-10 h-10 text-oxide mx-auto" />
        <div className="space-y-1">
          <h2 className="text-lg font-bold text-ink">
            Audit Run {run.status === 'rejected' ? 'Rejected' : 'Halted with Error'}
          </h2>
          <p className="text-xs text-ink-soft font-mono">Run ID: {run.run_id}</p>
        </div>
        <div className="p-3 bg-oxide/5 border border-oxide/20 rounded text-xs text-oxide text-left">
          {run.error_message || 'The human reviewer declined approval for this run configuration.'}
        </div>
        <button
          onClick={() => router.push('/')}
          className="px-4 py-2 bg-verdigris text-white text-xs font-semibold rounded hover:bg-verdigris-hover"
        >
          Start New Audit Run
        </button>
      </div>
    </div>
  );
}
