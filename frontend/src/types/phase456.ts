/** Types for Insights, Admin, Agents, Problems, Reopen, Collab (Phases 4–6). */

export interface InsightsDashboard {
  days: number;
  participation: {
    days: number;
    active: number;
    total: number;
    pct: number;
    prev_active: number;
    by_team: Array<{
      team_id: string;
      team_name: string;
      size: number;
      active: number;
      pct: number;
    }>;
    buckets: Array<{ start: string; end: string; n: number; label: string }>;
  };
  funnel: {
    days: number;
    counts: number[];
    stages: string[];
    conversions: Array<{
      from: string;
      to: string;
      n: number;
      of: number;
      pct: number | null;
    }>;
    accepted: number;
    accepted_impl: number;
  };
  review: {
    days: number;
    timeline_days: number;
    overdue_total: number;
    rows: Array<Record<string, unknown>>;
    bottleneck: Record<string, unknown> | null;
  };
  themes: {
    days: number;
    tags: Array<{ tag: string; cur: number; prev: number; growth: number }>;
    themes: Array<{
      id: string;
      label: string;
      cur: number;
      prev: number;
      growth: number;
    }>;
    cur_n: number;
    prev_n: number;
  };
  impact: {
    days: number;
    period: Record<string, unknown>;
    all_time: Record<string, unknown>;
  };
  hours: {
    quarterly_hours: number;
    remaining: number;
    granted: number;
    logged: number;
    by_idea: Array<{ idea_id: string; granted: number; logged: number }>;
  };
  recognition: {
    days: number;
    total: number;
    rows: number;
    dims: Record<string, number>;
    by_team: Array<Record<string, unknown>>;
  };
  cards: Array<{
    id: string;
    text: string;
    evidence: string[];
    link?: string | null;
    simulated: boolean;
  }>;
}

export interface AdminConfig {
  timelines: Record<string, number>;
  scoring: Array<{
    key: string;
    label: string;
    low: string;
    high: string;
    weight: number;
  }>;
  point_overrides: Record<string, number>;
  pool: Record<string, unknown>;
  categories: Array<{
    id: string;
    slug: string;
    label: string;
    color: string;
    description: string;
    enabled: boolean;
  }>;
  panels: Array<{
    id: string;
    slug: string;
    category_id: string;
    name: string;
    member_ids: string[];
    chair_id: string | null;
  }>;
}

export interface AgentInfo {
  id: string;
  prompt_slug: string | null;
  form: string;
  purpose: string;
  triggers: string[];
  approval_default: string;
  never: string[];
  simulated: boolean;
}

export interface AgentRun {
  id: string;
  agent_id: string;
  event: string;
  idea_id: string | null;
  summary: string;
  output: Record<string, unknown>;
  simulated: boolean;
  engine: string;
  approval_required: boolean;
  approval_role: string | null;
  approval_state: string;
  proposal_key: string | null;
  created_at: string;
}

export interface PendingProposal {
  proposal_key: string;
  run: AgentRun;
  evidence: string[];
}

export interface KompassMap {
  connected: boolean;
  notice: string;
  questions: Array<{
    id: string;
    text: string;
    answered: boolean;
    note: string;
  }>;
}

export interface Problem {
  cluster_key: string;
  label: string;
  terms: string[];
  state: string;
  idea_count: number;
  me_too_count: number;
  me_too_mine: boolean;
  team_count: number;
  ideas: Array<{
    id: string;
    title: string;
    status: string;
    tags: string[];
    submitted_at: string | null;
    anonymous: boolean;
  }>;
  sponsor_id: string | null;
  acknowledged_at: string | null;
  custom_label: string;
  note: string;
}

export interface ReopenState {
  idea_id: string;
  rule: string;
  satisfied: boolean;
  met: number;
  total: number;
  close: number;
  derived: boolean;
  items: Array<{
    cond: Record<string, unknown>;
    label: string;
    met: boolean;
    frac: number;
    progress: string;
    evidence: string;
    impossible: boolean;
  }>;
  evidence: string[];
  snoozed_until: string | null;
  closed: boolean;
}

export interface ReopenProposal {
  type: string;
  proposal_key: string;
  idea_id: string;
  idea_title: string;
  evidence: string[];
  state: ReopenState;
}

export interface CollabRequest {
  id: string;
  idea_id: string;
  from_user_id: string;
  type: string;
  message: string;
  role: string;
  hours: number | null;
  status: string;
  source: string;
  decided_by: string | null;
  decided_at: string | null;
  note: string;
  created_at: string;
}

export interface Tracker {
  idea_id: string;
  milestones: Array<{
    id: string;
    idea_id: string;
    title: string;
    status: string;
    owner_id: string | null;
    due_at: string | null;
    blocker: string;
    sort_order: number;
    done_at: string | null;
    created_at: string;
  }>;
  checkins: Array<{
    id: string;
    idea_id: string;
    author_id: string;
    body: string;
    percent_complete: number | null;
    created_at: string;
  }>;
  blocked_count: number;
  overdue_count: number;
}
