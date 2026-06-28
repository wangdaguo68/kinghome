export type Freshness = "live" | "stale" | "sample";

export interface HistoryItem {
  id: number;
  created_at: string;
  trade_date: string;
  source: string;
  freshness: Freshness;
  is_official: number;
}

export interface DashboardData {
  meta: { trade_date: string; updated_at: string; source: string; freshness: Freshness; warning?: string; version_label?: string };
  permission: { label: string; position_limit: number; allowed: string; forbidden: string };
  state: { cycle: string; structure: string; money: number; loss: number; trend: number; speculation: number };
  breadth: { eligible: number; up: number; down: number; flat: number; median: number; limit_up: number; limit_down: number; failed_limit: number; continuous: number };
  capacity: { sample: number; up: number; down: number; median: number; label: string; source: string };
  market_graph?: {
    nodes: Array<{ id: string; label: string; type: string; score: number; detail: string }>;
    edges: Array<{ source: string; target: string; label: string; tone: string }>;
  };
  capacity_cores?: Array<{
    name: string; code: string; industry: string; rank: number; score: number; change: number;
    amount: number; amount_label: string; capacity_median: number; linkage_score?: number | null;
    linkage_level: string; mainline_match: boolean; tradable: boolean; tags: string[]; reason: string; source: string;
  }>;
  mainlines: Array<{ name: string; score: number; role: string; change: number; flow: string; tags: string[] }>;
  sector_linkage?: Array<{
    name: string; score: number; level: string; leader: string; leader_code: string;
    limit_up_count: number; follower_count: number; elastic_count: number; low_level_count: number;
    tier_count: number; max_height: number; strong_count: number; positive_count: number;
    median_change: number; isolated: boolean; evidence: string[]; risks: string[];
    followers: Array<{ name: string; code: string; change: number; role: string }>;
  }>;
  cores: Array<{ name: string; code: string; kind: string; score: number; change: number; evidence: string; source?: string; confidence?: string }>;
  negative: Array<{ name: string; change: number; severity: string; detail?: string; source?: string }>;
  negative_stocks?: Array<{
    name: string; code: string; industry: string; change: number; drawdown: number;
    amount: number; amount_label: string; severity: string; reason: string; tags: string[]; source: string;
  }>;
  alerts: Array<{ level: string; title: string; detail: string }>;
  ladder: Array<{ name: string; code: string; height: number; recent_limit_count?: number; recent_window_days?: number; change: number; concepts: string[]; primary_factor: string; factor_type: string; confidence: string; evidence: string; source: string }>;
  planned_targets: Array<{
    name: string; code: string; kind: string; priority: string; score: number; logic: string;
    observation: string; invalidation: string; holding_period: string; source: string; confidence: string;
    setup?: string; payoff?: string; risk_note?: string; position_plan?: string;
    sector_linkage_score?: number | null; sector_linkage_level?: string; sector_linkage_evidence?: string[];
    leader_effect?: string; followers?: Array<{ name: string; code: string; change: number; role: string }>;
    is_isolated?: boolean;
    event_signal_score?: number | null;
    event_signals?: Array<{ topic: string; type: string; score: number; catalyst: string; validation: string; risk: string }>;
    entry_preconditions?: string[]; entry_trigger?: string[]; no_buy_conditions?: string[];
    stop_loss?: string[]; take_profit?: string[]; sell_plan?: string[];
  }>;
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
    notice?: string;
    is_backtest?: boolean;
    label_scope?: string;
    items: Array<{
      trade_date: string; code: string; name: string; rank?: number; horizon: number; holding_days?: number;
      tradable: boolean; net_return: number; gross_return?: number; mfe: number; mae: number; payoff_ratio?: number | null;
      entry_trade_date?: string; exit_trade_date?: string; entry_price?: number; exit_price?: number;
      cost_rate?: number; blocked_reason?: string | null; label_version?: string;
      sample_type?: string; is_backtest?: boolean; execution_model?: string; entry_rule?: string; exit_rule?: string;
    }>;
  };
  data_quality: Record<string, { source: string; status: string; reason?: string }>;
  event_signals?: Array<{
    topic: string; score: number; type: string; heat?: number | null; crowding: string;
    catalyst: string; validation: string; mainline_match: boolean; linkage_match: boolean;
    source: string; usable: boolean; risk: string;
  }>;
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
