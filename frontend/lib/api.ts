// VERITAS API Client & Type Definitions

export interface ConfigBound {
  min: number;
  max: number;
  default: number;
}

export interface ConfigBounds {
  significance_level: ConfigBound;
  min_group_size: ConfigBound;
  permutations: ConfigBound;
}

export interface ColumnInspection {
  detected_roles: {
    prediction?: string;
    actual?: string;
    protected?: string[];
    protected_attributes?: string[];
    features?: string[];
    feature_columns?: string[];
    ignored?: string[];
    record_id?: string;
    timestamp?: string;
    [key: string]: unknown;
  };
  total_rows?: number;
  row_count: number;
  column_count: number;
  preview_rows: Record<string, unknown>[];
  errors: string[];
  columns: string[];
}

export interface RunReviewPayload {
  run_id: string;
  row_count: number;
  column_names: string[];
  detected_protected_candidates: string[];
  proposed_config: {
    protected_attributes?: string[];
    significance_level?: number;
    min_group_size?: number;
    permutations?: number;
    [key: string]: unknown;
  };
  rationale?: {
    recommendations?: Record<string, string>;
    risks_identified?: string[];
    proxy_features_detected?: string[];
    significance_justification?: string;
    sample_size_stability?: string;
  };
  config_fingerprint?: string;
}

export interface RunSummary {
  run_id: string;
  timestamp: string;
  total_records: number;
  anomalies_detected: number;
  fairness_violations: number;
  nist_violations: number;
  nist_informational: number;
  config_fingerprint?: string;
  status: string;
}

export interface AnomalyFinding {
  record_id: string | number;
  anomaly_score?: number;
  z_score?: number;
  dominant_feature?: string;
  dominant_z?: number;
  outlier_features?: string[];
  [key: string]: unknown;
}

export interface FairnessFinding {
  attribute?: string;
  protected_attribute?: string;
  metric?: string;
  value?: number;
  threshold?: number;
  disparity_ratio?: number;
  selection_rate?: number;
  disparate_impact_violation?: boolean;
  demographic_parity_violation?: boolean;
  equalized_odds_violation?: boolean;
  group_metrics?: Record<string, { selection_rate?: number; count?: number; tpr?: number; fpr?: number }>;
  group_selection_rates?: Record<string, number>;
  reference_group?: string;
  disparity?: number;
  status?: string;
  violation?: boolean;
  [key: string]: unknown;
}

export interface MappedFinding {
  finding_id?: string;
  control_id: string;
  control_title?: string;
  nist_function?: string;
  category?: string;
  severity_tier: 'violation' | 'informational';
  risk_statement?: string;
  remediation_playbook?: string;
  remediation_id?: string;
  plain_explanation?: {
    summary: string;
    plain_title?: string;
    what_happened: string;
    why_it_matters: string;
    recommended_action: string;
    verified?: boolean;
  };
  [key: string]: unknown;
}

export interface AnomalyCluster {
  cluster_name: string;
  cluster_description?: string;
  dominant_feature: string;
  record_count: number;
  avg_anomaly_score?: number;
  sample_record_ids?: (string | number)[];
  precision_estimate?: number;
  recall_estimate?: number;
}

export interface RunRecord {
  run_id: string;
  status: 'validating' | 'awaiting_approval' | 'running' | 'completed' | 'rejected' | 'failed';
  stage?: string;
  error_message?: string;
  config_fingerprint?: string;
  approved_by?: string;
  approved_at?: string;
  rejected_by?: string;
  rejected_at?: string;
  created_at?: string;
  updated_at?: string;
  review?: RunReviewPayload;
  summary?: RunSummary;
  agentic_artifacts?: {
    schema_inference?: Record<string, unknown>;
    config_proposal?: Record<string, unknown>;
    anomaly_clusters?: AnomalyCluster[];
    [key: string]: unknown;
  };
}

export interface QAResponse {
  question: string;
  answer: string;
  citations: string[];
  tokens_used?: number;
  fallback_used?: boolean;
}

const API_BASE = '/api';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchConfigBounds(): Promise<ConfigBounds> {
  const res = await fetch(`${API_BASE}/config-bounds`);
  if (!res.ok) throw new Error('Failed to fetch config bounds');
  return res.json();
}

export async function validateDataset(file: File): Promise<ColumnInspection> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/validate`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Validation failed');
  }
  return res.json();
}

export async function createRun(file: File, approverEmail?: string, approverName?: string): Promise<{ run_id: string; status: string; config_fingerprint?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  const headers: Record<string, string> = {};
  if (approverEmail) headers['X-User-Email'] = approverEmail;
  if (approverName) headers['X-User-Name'] = approverName;

  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers,
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create audit run');
  }
  return res.json();
}

export async function fetchRun(id: string): Promise<RunRecord> {
  const res = await fetch(`${API_BASE}/runs/${id}`);
  if (!res.ok) {
    throw new Error(`Run ${id} not found`);
  }
  return res.json();
}

export async function fetchRuns(limit = 20, offset = 0): Promise<{ runs: RunRecord[]; total: number }> {
  const res = await fetch(`${API_BASE}/runs?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error('Failed to fetch runs');
  return res.json();
}

export async function approveRun(
  id: string,
  config: {
    protected_attributes: string[];
    significance_level: number;
    min_group_size: number;
    permutations: number;
  },
  user?: { email?: string; name?: string }
): Promise<{ status: string; message: string }> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (user?.email) headers['X-User-Email'] = user.email;
  if (user?.name) headers['X-User-Name'] = user.name;

  const res = await fetch(`${API_BASE}/runs/${id}/approve`, {
    method: 'POST',
    headers,
    body: JSON.stringify(config),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to approve run');
  }
  return res.json();
}

export async function rejectRun(id: string, reason: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/runs/${id}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to reject run');
  }
  return res.json();
}

export async function fetchAnomalies(id: string, page = 1, size = 50): Promise<{ total: number; items: AnomalyFinding[]; page: number; size: number }> {
  const res = await fetch(`${API_BASE}/runs/${id}/anomalies?page=${page}&size=${size}`);
  if (!res.ok) throw new Error('Failed to fetch anomalies');
  return res.json();
}

export async function fetchFairness(id: string): Promise<{ total: number; items: FairnessFinding[] }> {
  const res = await fetch(`${API_BASE}/runs/${id}/fairness`);
  if (!res.ok) throw new Error('Failed to fetch fairness findings');
  return res.json();
}

export async function fetchFindings(id: string, severityTier?: 'violation' | 'informational'): Promise<{ total: number; items: MappedFinding[] }> {
  const url = severityTier
    ? `${API_BASE}/runs/${id}/findings?severity_tier=${severityTier}`
    : `${API_BASE}/runs/${id}/findings`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch findings');
  return res.json();
}

export async function fetchAnomalyClusters(id: string): Promise<{ clusters: AnomalyCluster[] }> {
  const res = await fetch(`${API_BASE}/runs/${id}/anomaly-clusters`);
  if (!res.ok) throw new Error('Failed to fetch anomaly clusters');
  return res.json();
}

export async function askQuestion(id: string, question: string): Promise<QAResponse> {
  const res = await fetch(`${API_BASE}/runs/${id}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Audit Q&A error');
  }
  return res.json();
}

export async function deleteRun(id: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/runs/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete run');
  return res.json();
}
