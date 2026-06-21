export type Freshness = "live" | "stale" | "sample";

export interface DashboardData {
  meta: { trade_date: string; updated_at: string; source: string; freshness: Freshness; warning?: string };
  permission: { label: string; position_limit: number; allowed: string; forbidden: string };
  state: { cycle: string; structure: string; money: number; loss: number; trend: number; speculation: number };
  breadth: { eligible: number; up: number; down: number; flat: number; median: number; limit_up: number; limit_down: number; failed_limit: number; continuous: number };
  capacity: { sample: number; up: number; down: number; median: number; label: string; source: string };
  mainlines: Array<{ name: string; score: number; role: string; change: number; flow: string; tags: string[] }>;
  cores: Array<{ name: string; code: string; kind: string; score: number; change: number; evidence: string }>;
  negative: Array<{ name: string; change: number; severity: string }>;
  alerts: Array<{ level: string; title: string; detail: string }>;
  ladder: Array<{ name: string; code: string; height: number; change: number; concepts: string[]; primary_factor: string; factor_type: string; confidence: string; evidence: string; source: string }>;
  data_quality: Record<string, { source: string; status: string; reason?: string }>;
  sentiment: Array<{ topic: string; heat: number; crowding: string; catalyst: string; validation: string }>;
  checkpoints: string[];
}

export type Workspace = "cockpit" | "map" | "sectors" | "cores" | "sentiment" | "review" | "history" | "settings";
