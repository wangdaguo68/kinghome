export type Freshness = "live" | "stale" | "sample";

export interface DashboardData {
  meta: { trade_date: string; updated_at: string; source: string; freshness: Freshness; warning?: string; version_label?: string };
  permission: { label: string; position_limit: number; allowed: string; forbidden: string };
  state: { cycle: string; structure: string; money: number; loss: number; trend: number; speculation: number };
  breadth: { eligible: number; up: number; down: number; flat: number; median: number; limit_up: number; limit_down: number; failed_limit: number; continuous: number };
  capacity: { sample: number; up: number; down: number; median: number; label: string; source: string };
  mainlines: Array<{ name: string; score: number; role: string; change: number; flow: string; tags: string[] }>;
  cores: Array<{ name: string; code: string; kind: string; score: number; change: number; evidence: string; source?: string; confidence?: string }>;
  negative: Array<{ name: string; change: number; severity: string }>;
  alerts: Array<{ level: string; title: string; detail: string }>;
  ladder: Array<{ name: string; code: string; height: number; recent_limit_count?: number; recent_window_days?: number; change: number; concepts: string[]; primary_factor: string; factor_type: string; confidence: string; evidence: string; source: string }>;
  planned_targets: Array<{ name: string; code: string; kind: string; priority: string; score: number; logic: string; observation: string; invalidation: string; holding_period: string; source: string; confidence: string }>;
  ml_shadow?: {
    mode: "shadow";
    status: string;
    reason: string;
    feature_version?: string;
    plan_version?: string;
    market_style?: string;
    cycle?: string;
    plans: Array<{
      rank: number; name: string; code: string; kind: string; score: number; holding_period: string;
      eligible_for_live: boolean; blocked_reason: string; evidence: string;
      score_breakdown: {
        calibrated_probability: number; expectancy_payoff: number; mainline_core: number;
        style_cycle_match: number; tradeability: number; data_model_reliability: number; risk_penalty: number;
      };
    }>;
  };
  feature_store_status?: { feature_days: number; outcome_days: number; latest_trade_date: string | null; feature_version: string | null };
  ml_system?: {
    stage: "rule_only" | "shadow_learning" | "assisted" | "live_eligible";
    feature_days: number;
    outcome_days: number;
    champion_count: number;
    challenger_count: number;
    next_gate: number | null;
    last_training_run: { version: string; status: string; sample_count: number; finished_at?: string } | null;
    modules?: Record<string, "active" | "waiting_data" | "champion">;
  };
  ml_review?: {
    summary: Array<{ horizon: number; samples: number; win_rate: number | null; average_return: number | null }>;
    items: Array<{ trade_date: string; code: string; name: string; rank?: number; horizon: number; tradable: boolean; net_return: number; mfe: number; mae: number; blocked_reason?: string }>;
  };
  data_quality: Record<string, { source: string; status: string; reason?: string }>;
  sentiment: Array<{ topic: string; heat: number; crowding: string; catalyst: string; validation: string }>;
  checkpoints: string[];
  collection_status: {
    trade_date: string;
    job: { status: string; started_at: string; finished_at?: string; free_attempts: number; error?: string } | null;
    tdx_calls_used: number;
    tdx_daily_limit: number;
    tdx_calls: Array<{ code: string; called_at: string; status: string }>;
  };
}

export type Workspace = "cockpit" | "map" | "sectors" | "cores" | "sentiment" | "review" | "history" | "settings";
