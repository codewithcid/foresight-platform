export type LedgerEntry = {
  id: number;
  ts: number;
  status: "acted" | "held" | "proven";
  customer_id: string;
  first_name: string;
  segment: string;
  intervention: string | null;
  intervention_label?: string;
  channel: string | null;
  predicted_rel_lift: number;
  predicted_revenue: number;
  cost: number;
  roi?: number;
  message: string | null;
  message_source: string | null;
  reason?: string;
  actual_rel_lift: number | null;
  error: number | null;
  resolved: boolean;
  product_id?: string | null;
  product_name?: string | null;
  occasion_key?: string | null;
};

export type Persona = { customer_id: string; first_name: string; segment: string; segment_label: string };
export type BanditArm = { segment: string; intervention: string; mean_reliability: number; trials: number; alpha: number; beta: number };
export type AgentOpsTrace = { step: number; tool: string; args: Record<string, any>; result: any };
export type AgentOpsResponse = { answer: string; trace: AgentOpsTrace[] };

export type Calibration = {
  mae: number | null;
  n: number;
  acted: number;
  held: number;
  total_spent?: number;
  total_projected_revenue?: number;
  correction_factors?: Record<string, number>;
};

export type Meta = {
  segments: { key: string; label: string }[];
  interventions: { key: string; label: string; channel: string; cost_per_contact: number }[];
  concierge_channels: string[];
  guardrails: { max_actions_per_day: number; daily_budget_usd: number; min_rel_lift_to_act: number };
  llm_mode: string;
};

// ---- Self-testing creative loop ----
export type CreativeVariant = {
  id: string; angle: string; headline: string; body: string; copy: string;
  copy_source: string; image_prompt: string; image_url: string;
};
export type PersonaScore = { name: string; score: number; reaction: string };
export type VariantScore = { variant_id: string; angle: string; mean_score: number; per_persona: PersonaScore[] };
export type Pretest = {
  personas: { name: string; blurb: string }[];
  scores: VariantScore[];
  winner_id: string; winner_angle: string; winner_score: number; spread: number; method: string;
};
export type Preflight = {
  intervention: string; intervention_label: string; segment: string; segment_label: string;
  occasion_key: string | null; occasion_theme: string | null;
  product_id: string | null; product_name: string | null;
  variants: CreativeVariant[]; pretest: Pretest;
};

const BASE = "";

export async function getMeta(): Promise<Meta> {
  return fetch(`${BASE}/api/meta`).then((r) => r.json());
}

export async function getLedger(limit = 60): Promise<{ entries: LedgerEntry[]; calibration: Calibration }> {
  return fetch(`${BASE}/api/ledger?limit=${limit}`).then((r) => r.json());
}

export async function getCalibration(): Promise<Calibration> {
  return fetch(`${BASE}/api/calibration`).then((r) => r.json());
}
export async function getDashboardBrief(): Promise<{ text: string; model: string }> {
  return fetch(`${BASE}/api/dashboard/brief`).then((r) => r.json());
}

// ---- Model Card + Qini ----
export type ModelCardData = {
  name: string; version: string; model_type: string; library: string; objective: string;
  features: string[]; training_data: string; interventions: string[];
  metrics: { cell_mae_pp: number; n_validation_cells: number; mean_qini: number; qini_by_intervention: Record<string, number> };
  validation: string[]; assumptions: string[]; limitations: string[]; responsible_ai: string[];
};
export type Qini = { intervention: string; intervention_label: string; curve: { frac: number; model: number; random: number }[]; qini: number };
export async function getModelCard(): Promise<ModelCardData> {
  return fetch(`${BASE}/api/model/card`).then((r) => r.json());
}
export async function getQini(intervention: string): Promise<Qini> {
  return fetch(`${BASE}/api/model/qini?intervention=${intervention}`).then((r) => r.json());
}

export async function simStart() {
  return fetch(`${BASE}/api/sim/start`, { method: "POST" }).then((r) => r.json());
}
export async function simPause() {
  return fetch(`${BASE}/api/sim/pause`, { method: "POST" }).then((r) => r.json());
}
export async function simSpeed(speed: number) {
  return fetch(`${BASE}/api/sim/speed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ speed }),
  }).then((r) => r.json());
}

export async function getDemoPersonas(): Promise<{ personas: Persona[] }> {
  return fetch(`${BASE}/api/demo/personas`).then((r) => r.json());
}

export async function getExplain(entryId: number) {
  return fetch(`${BASE}/api/explain/${entryId}`).then((r) => r.json());
}

export async function getBanditStatus(): Promise<{ arms: BanditArm[] }> {
  return fetch(`${BASE}/api/bandit/status`).then((r) => r.json());
}

export async function askAgentOps(question: string): Promise<AgentOpsResponse> {
  return fetch(`${BASE}/api/agent_ops/ask`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }),
  }).then((r) => r.json());
}

export async function runPreflight(intervention: string, segment: string, product_id?: string): Promise<Preflight> {
  return fetch(`${BASE}/api/creative/preflight`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ intervention, segment, product_id }),
  }).then((r) => r.json());
}

export type CreativeProofEntry = {
  id: number; ts: number; intervention: string; intervention_label: string;
  segment: string; segment_label: string; variant_id: string; angle: string;
  copy: string; image_url: string; predicted_resonance: number; actual_engagement: number; error: number;
  relayed_to?: string | null;
};
export type CreativeCalibration = { mae: number | null; n: number; accuracy: number | null };

export async function shipCreative(payload: {
  intervention: string; segment: string; variant_id: string; angle: string;
  copy: string; image_url: string; predicted_resonance: number;
}): Promise<{ entry: CreativeProofEntry; calibration: CreativeCalibration }> {
  return fetch(`${BASE}/api/creative/ship`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
  }).then((r) => r.json());
}

export async function getCreativeLedger(limit = 20): Promise<{ entries: CreativeProofEntry[]; calibration: CreativeCalibration }> {
  return fetch(`${BASE}/api/creative/ledger?limit=${limit}`).then((r) => r.json());
}

// ---- Spend Planner ----
export type PlanLine = {
  segment: string; segment_label: string; intervention: string; intervention_label: string;
  channel: string; reach_funded: number; cost: number; pred_incr_conversions: number;
  pred_incr_revenue: number; roi: number;
};
export type Plan = {
  budget: number; max_useful_budget: number; spend: number; pred_incr_revenue: number;
  pred_incr_revenue_ci: [number, number];
  pred_incr_conversions: number; blended_roi: number; plan: PlanLine[];
  curve: { budget: number; incr_revenue: number }[];
  incrementality: { predicted_incr_revenue: number; actual_incr_revenue: number; error: number; accuracy: number | null };
  baselines: { foresight: number; even_split: number; biggest_segment: number; uplift_vs_even_pct: number | null; uplift_vs_even_abs: number };
  aov: number;
};
export async function getPlannerDefaults(): Promise<{ max_useful_budget: number; suggested_budget: number; aov: number }> {
  return fetch(`${BASE}/api/planner/defaults`).then((r) => r.json());
}
export async function optimizePlan(budget: number): Promise<Plan> {
  return fetch(`${BASE}/api/planner/optimize`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ budget }),
  }).then((r) => r.json());
}
export async function getPlannerAnalyst(budget: number): Promise<{ text: string; model: string }> {
  return fetch(`${BASE}/api/planner/analyst?budget=${budget}`).then((r) => r.json());
}

// ---- Audience & Uplift (Bring-Your-Own-CSV) ----
export type ByoCell = {
  segment: string; treatment: string; n: number; n_treated: number;
  pred_abs_lift: number; pred_rel_lift: number | null;
  obs_abs_lift: number | null; obs_rel_lift: number | null; abs_error_pp: number | null;
};
export type ByoDecile = { bucket: number; avg_pred_uplift: number; obs_uplift: number | null; n: number };
export type ByoAnalysis = {
  dataset: {
    rows: number; customers: number; conversion_rate: number;
    segments: { name: string; n: number }[];
    treatments: { name: string; n: number; is_control: boolean }[];
    columns_detected: Record<string, string | null>;
    features_used: { numeric: string[]; categorical: string[] };
  };
  model: { type: string; library: string; n_train: number; n_test: number; n_features: number };
  validation: {
    cell_mae_pp: number | null;
    incrementality: { predicted_incr_conversions: number; observed_incr_conversions: number; accuracy_pct: number | null; n_treated_test: number };
    cells: ByoCell[];
    deciles: ByoDecile[];
  };
  aov: number; aov_source: string; cost_source: string;
  plan: Plan;
};

export async function analyzeByoCsv(file: File, controlLabel?: string, aov?: number): Promise<ByoAnalysis> {
  const fd = new FormData();
  fd.append("file", file);
  if (controlLabel) fd.append("control_label", controlLabel);
  if (aov != null) fd.append("aov", String(aov));
  const r = await fetch(`${BASE}/api/byocsv/analyze`, { method: "POST", body: fd });
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(e.detail || "Analysis failed");
  }
  return r.json();
}
export async function byoReplan(budget: number): Promise<Plan> {
  return fetch(`${BASE}/api/byocsv/replan`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ budget }),
  }).then((r) => r.json());
}
export const byoSampleUrl = () => `${BASE}/api/byocsv/sample`;

// ---- Channels ----
export type ChannelStatus = {
  id: string; label: string; kind: string; icon: string;
  configured: boolean; sandbox: boolean; mode: "live" | "sandbox" | "needs_key";
  needs: string[]; hint?: string;
};
export type ChannelLog = {
  id: number; ts: number; channel: string; to_addr: string; body: string;
  status: string; provider_id: string; error: string; customer_id: string; meta: any;
  direction?: string;
};
export type EngagementEvent = { id: number; ts: number; kind: string; channel: string; to_addr: string; run_id: number | null; detail: string };
export async function getChannels(): Promise<{ channels: ChannelStatus[] }> {
  return fetch(`${BASE}/api/channels`).then((r) => r.json());
}
export async function getChannelLogs(limit = 30): Promise<{ logs: ChannelLog[] }> {
  return fetch(`${BASE}/api/channels/logs?limit=${limit}`).then((r) => r.json());
}
export async function getEngagement(limit = 40): Promise<{ events: EngagementEvent[]; summary: Record<string, number> }> {
  return fetch(`${BASE}/api/engagement?limit=${limit}`).then((r) => r.json());
}
export async function testChannel(id: string, to: string, body?: string): Promise<{
  ok: boolean; channel: string; to: string; provider_id: string; error: string; sandbox: boolean;
}> {
  return fetch(`${BASE}/api/channels/${id}/test`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ to, body }),
  }).then((r) => r.json());
}

// ---- Workflows ----
export type WorkflowTemplate = { id: string; label: string; description: string; segment: string; intervention: string; channel: string };
export type RunStep = { id: number; run_id: number; idx: number; name: string; label: string; status: string; output: any; ts: number };
export type Run = {
  id: number; ts: number; workflow: string; label: string; status: string;
  target: string; channel: string; params: any; summary: any; steps: RunStep[];
};
export type WorkflowMeta = {
  templates: WorkflowTemplate[];
  steps: { name: string; label: string }[];
  segments: { key: string; label: string }[];
  interventions: { key: string; label: string; channel: string }[];
  channels: string[];
};
export async function getWorkflowMeta(): Promise<WorkflowMeta> {
  return fetch(`${BASE}/api/workflows`).then((r) => r.json());
}
export async function getRuns(limit = 30): Promise<{ runs: Run[] }> {
  return fetch(`${BASE}/api/workflows/runs?limit=${limit}`).then((r) => r.json());
}
export async function getRun(id: number): Promise<Run> {
  return fetch(`${BASE}/api/workflows/runs/${id}`).then((r) => r.json());
}
export async function startWorkflow(params: {
  workflow?: string; segment: string; intervention: string; channel: string;
  budget?: number; test_recipient?: string; label?: string; copy?: string; angle?: string;
}): Promise<Run> {
  return fetch(`${BASE}/api/workflows/run`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(params),
  }).then((r) => r.json());
}
export async function approveRun(id: number, test_recipient?: string): Promise<Run> {
  return fetch(`${BASE}/api/workflows/runs/${id}/approve`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ test_recipient }),
  }).then((r) => r.json());
}
export async function rejectRun(id: number): Promise<Run> {
  return fetch(`${BASE}/api/workflows/runs/${id}/reject`, { method: "POST" }).then((r) => r.json());
}

export function connectFeed(onMessage: (payload: any) => void): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${window.location.host}/ws/feed`);
  ws.onmessage = (ev) => {
    try {
      onMessage(JSON.parse(ev.data));
    } catch {
      /* ignore */
    }
  };
  return ws;
}
