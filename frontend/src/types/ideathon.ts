export type EventKind = 'ideathon' | 'hackathon';

export interface IdeathonSummary {
  id: string;
  title: string;
  /** Older rows may omit it; treat missing as ideathon. */
  kind?: EventKind;
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
  kind?: EventKind;
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
  kind?: EventKind;
  theme: string;
  challenges: string[];
  sponsor_id: string;
  start_at: string;
  end_at: string;
}

/** Partial organiser edit. Theme and challenges are only accepted while the ideathon is open. */
export interface IdeathonUpdateBody {
  title?: string;
  kind?: EventKind;
  theme?: string;
  challenges?: string[];
  start_at?: string;
  end_at?: string;
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

export type RubricCriterion = 'relevance' | 'feasibility' | 'impact' | 'originality';

export interface CriterionScore {
  score: number | null;
  rationale: string;
}

export interface GithubEvidence {
  status: 'ok' | 'missing' | 'unreachable';
  full_name?: string;
  description?: string;
  languages: Record<string, number>;
  readme_chars: number;
  file_count: number;
  has_tests: boolean;
  has_ci: boolean;
  recent_commits: number;
  pushed_at?: string;
}

/** Saved AI rubric score for one entry. A proposal; the admin decides. */
export interface EntryScore {
  idea_id: string;
  rank: number;
  overall: number | null;
  criteria: Record<RubricCriterion, CriterionScore>;
  rationale: string;
  engine: string;
  simulated: boolean;
  evidence: {
    github: GithubEvidence;
    documents: Array<{ filename: string; text_chars: number }>;
    has_demo: boolean;
    /** Why Kompass was not used for this entry (set only when it fell back to the local scorer). */
    scoring_note?: string;
  };
  scored_at: string;
}

export interface EntryScores {
  ideathon_id: string;
  rubric_version: string;
  items: EntryScore[];
}
