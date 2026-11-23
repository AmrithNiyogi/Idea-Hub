export type IdeaStatus =
  | 'draft'
  | 'submitted'
  | 'under_review'
  | 'needs_info'
  | 'accepted'
  | 'parked'
  | 'merged'
  | 'declined'
  | 'prototype'
  | 'implemented'
  | 'withdrawn';

export type Effort = 'S' | 'M' | 'L' | 'XL';

export interface StatusHistory {
  id: string;
  from_status: string | null;
  to_status: string;
  actor_id: string | null;
  at: string;
  reason: string;
}

export interface Idea {
  id: string;
  slug: string | null;
  title: string;
  category_id: string | null;
  problem: string;
  solution: string;
  beneficiaries: string;
  effort: Effort;
  success_metrics: string;
  tags: string[];
  author_id: string;
  anonymous: boolean;
  co_author_ids: string[];
  team_name?: string | null;
  github_url?: string | null;
  demo_url?: string | null;
  owner_id: string | null;
  status: IdeaStatus;
  is_draft: boolean;
  reviewer_id: string | null;
  awaiting_owner: boolean;
  hours_recommended: number | null;
  needs_info_question: string | null;
  withdraw_reason: string;
  merged_into_id: string | null;
  submitted_at: string | null;
  picked_up_at: string | null;
  due_at: string | null;
  pickup_due_at: string | null;
  revisit_at: string | null;
  stage_entered_at: string | null;
  created_at: string;
  updated_at: string;
  vote_count: number;
  follow_count: number;
  comment_count: number;
  voted: boolean;
  following: boolean;
  status_history: StatusHistory[];
}

export interface IdeaWrite {
  title: string;
  category_id?: string | null;
  problem?: string;
  solution?: string;
  beneficiaries?: string;
  effort?: Effort;
  success_metrics?: string;
  tags?: string[];
  anonymous?: boolean;
  co_author_ids?: string[];
  team_name?: string | null;
  github_url?: string | null;
  demo_url?: string | null;
}

export interface IdeaListResponse {
  items: Idea[];
  total: number;
}

export interface Comment {
  id: string;
  idea_id: string;
  author_id: string;
  body: string;
  kind: string;
  created_at: string;
}

export interface HomeAggregates {
  status_counts: Record<string, number>;
  needs_attention: Array<{
    text?: string;
    href?: string;
    priority?: number;
    kind?: string;
    [key: string]: unknown;
  }>;
  total_live: number;
}

export interface Category {
  id: string;
  slug: string;
  label: string;
  color: string;
  description: string;
}

export interface ToggleResponse {
  active: boolean;
}

/** Skill pack included in GET /ideas/{id}/agent-context */
export interface AgentSkillPack {
  name: string;
  skill_markdown: string;
  install_cursor: string;
  install_claude: string;
  zip_url: string;
}

/** Response from GET /ideas/{id}/agent-context */
export interface AgentContext {
  idea_id: string;
  slug: string | null;
  title: string;
  status: string;
  api_base_url: string;
  skill: AgentSkillPack;
  markdown: string;
  prompts: {
    cursor: string;
    claude: string;
  };
}
