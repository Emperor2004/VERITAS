import React from 'react';
import { BookOpen, Scale, Activity, ShieldCheck, CheckCircle2 } from 'lucide-react';

export default function MethodologyPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-8 py-2">
      <div className="space-y-2 pb-4 border-b border-rule">
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center space-x-2">
          <BookOpen className="w-6 h-6 text-verdigris" />
          <span>Audit Methodology & Statistical Foundations</span>
        </h1>
        <p className="text-sm text-ink-soft leading-relaxed">
          How VERITAS evaluates algorithmic fairness, isolates feature drift, and maps findings to the
          NIST Artificial Intelligence Risk Management Framework (NIST AI RMF 1.0).
        </p>
      </div>

      {/* 1. Deterministic Statistical Boundary */}
      <section className="bg-sheet border border-rule rounded p-6 space-y-3">
        <h2 className="text-base font-bold text-ink flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-verdigris" />
          <span>1. The Deterministic Statistical Boundary</span>
        </h2>
        <p className="text-xs text-ink-soft leading-relaxed font-serif">
          In high-stakes regulatory auditing, non-deterministic AI generation must never decide
          quantitative metrics, z-scores, p-values, or compliance outcomes. VERITAS enforces an
          architectural boundary: deterministic statistical engines calculate all metrics, and all
          pipeline outputs are verifiable via cryptographic SHA-256 fingerprints. Agentic components
          only assist by proposing configurations, clustering multivariate findings, and rewriting
          findings behind strict verification gates.
        </p>
      </section>

      {/* 2. Fairness & Disparity Metrics */}
      <section className="bg-sheet border border-rule rounded p-6 space-y-4">
        <h2 className="text-base font-bold text-ink flex items-center space-x-2">
          <Scale className="w-5 h-5 text-verdigris" />
          <span>2. Algorithmic Bias & Parity Testing</span>
        </h2>

        <div className="space-y-3 text-xs text-ink-soft">
          <div>
            <h3 className="font-semibold text-ink">Disparate Impact Ratio (4/5ths Rule)</h3>
            <p className="mt-0.5 font-serif leading-relaxed">
              Calculates the ratio of the selection rate of a protected demographic group compared to the
              selection rate of the highest-selected reference group. Ratios below 0.80 (80%) constitute
              actionable disparate impact under Equal Employment Opportunity Commission (EEOC) and
              NIST Measure-2.1 standards.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-ink">Demographic Parity Difference</h3>
            <p className="mt-0.5 font-serif leading-relaxed">
              Evaluates whether model decisions are statistically independent of protected attributes.
              Measures the maximum absolute difference in positive prediction rates between any two groups.
            </p>
          </div>

          <div>
            <h3 className="font-semibold text-ink">Equalized Odds</h3>
            <p className="mt-0.5 font-serif leading-relaxed">
              Assesses whether the model exhibits equal True Positive Rates (TPR) and False Positive Rates
              (FPR) across groups, ensuring prediction accuracy does not systematically penalize protected
              classes.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Anomaly & Outlier Detection */}
      <section className="bg-sheet border border-rule rounded p-6 space-y-3">
        <h2 className="text-base font-bold text-ink flex items-center space-x-2">
          <Activity className="w-5 h-5 text-amber" />
          <span>3. Multivariate Anomaly Detection & Clustering</span>
        </h2>
        <p className="text-xs text-ink-soft leading-relaxed font-serif">
          Features are scaled with median-and-IQR Robust Scalers to resist distortion from extreme
          values. An Isolation Forest ensemble flags observations in sparse feature space. Outlier
          records are then clustered by dominant feature z-score signatures (Agent-2), providing
          per-cluster precision and recall breakdowns.
        </p>
      </section>

      {/* 4. NIST AI RMF Core Functions */}
      <section className="bg-sheet border border-rule rounded p-6 space-y-4">
        <h2 className="text-base font-bold text-ink flex items-center space-x-2">
          <ShieldCheck className="w-5 h-5 text-cobalt" />
          <span>4. NIST AI RMF Core Functions (NIST AI 100-1)</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
          <div className="p-3 bg-paper/60 border border-rule rounded space-y-1">
            <span className="font-mono font-bold text-ink uppercase">GOVERN</span>
            <p className="text-ink-soft font-serif">
              Cultivates risk management culture, policies, and human-in-the-loop oversight.
            </p>
          </div>
          <div className="p-3 bg-paper/60 border border-rule rounded space-y-1">
            <span className="font-mono font-bold text-ink uppercase">MAP</span>
            <p className="text-ink-soft font-serif">
              Categorizes AI context, impacts, and potential demographic harms.
            </p>
          </div>
          <div className="p-3 bg-paper/60 border border-rule rounded space-y-1">
            <span className="font-mono font-bold text-ink uppercase">MEASURE</span>
            <p className="text-ink-soft font-serif">
              Analyzes, assesses, and tracks quantitative AI risks and trustworthiness metrics.
            </p>
          </div>
          <div className="p-3 bg-paper/60 border border-rule rounded space-y-1">
            <span className="font-mono font-bold text-ink uppercase">MANAGE</span>
            <p className="text-ink-soft font-serif">
              Prioritizes risk treatment, monitoring, and documented remediation playbooks.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
