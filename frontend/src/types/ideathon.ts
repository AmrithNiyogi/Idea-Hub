export interface IdeathonSummary {
  id: string;
  title: string;
  theme: string;
  phase: string;
  start_at: string;
  end_at: string;
  sponsor_id: string;
  organiser_id: string;
  entry_count: number;
  shortlist_count: number;
  completed_at?: string | null;
  /** Optional first challenge when backend includes it. */
  challenges?: string[];
}

export interface IdeathonDetail {
  id: string;
  title: string;
  theme: string;
  challenges: string[];
  phase: string;
  phase_log: Array<{ phase?: string; at?: string; by?: string }>;
  start_at: string;
  end_at: string;
  sponsor_id: string;
  organiser_id: string;
  shortlist: string[];
  shortlisted_at?: string | null;
  shortlist_edited: boolean;
  voting_closed_at?: string | null;
  winners: string[];
  results_at?: string | null;
  tally?: Array<Record<string, unknown>> | null;
  completed_at?: string | null;
  entry_idea_ids: string[];
}

export interface Handoff {
  id: string;
  idea_id: string;
  statement: string;
  sent_by: string;
  edited: boolean;
  status: string;
  created_at: string;
}

export interface IdeathonCreateBody {
  title: string;
  theme: string;
  challenges: string[];
  sponsor_id: string;
  start_at: string;
  end_at: string;
}

export interface TallyRow {
  idea_id: string;
  panel_avg: number;
  panel_n: number;
  panel_pct: number;
  audience_votes: number;
  aud_pct: number;
  combined: number;
}

/** Outcome of one Ideathon agent run (Rank or Pitch). Proposals only. */
export interface AgentRunResult {
  success: boolean;
  result_text: string;
  conversation_id: string | null;
  run_id: string | null;
  error: string | null;
}
