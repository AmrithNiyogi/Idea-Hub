export interface RecognitionRules {
  rules: Record<string, Record<string, unknown>>;
  levels: Array<{ id: string; name: string; min: number }>;
  badges: Array<{ id: string; name: string; icon: string; rule: string }>;
  dims: Record<string, string>;
}

export interface LeaderboardRow {
  user_id: string;
  points: number;
  level_id: string;
  level_name: string;
  dims?: Record<string, number>;
}

export interface LedgerEntry {
  id: string;
  user_id: string;
  rule_id: string;
  points: number;
  idea_id?: string | null;
  note: string;
  escrow: boolean;
  created_at: string;
  rule_label?: string | null;
  dimension?: string | null;
}

export interface Level {
  id: string;
  name: string;
  min: number;
  points: number;
  next_min?: number | null;
}

export interface Award {
  id: string;
  kind: string;
  period: string;
  idea_id?: string | null;
  user_ids: string[];
  reason: string;
  points: number;
  confirmed_by: string;
  created_at: string;
}
