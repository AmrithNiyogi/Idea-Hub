export interface ReviewQueueItem {
  idea_id: string;
  title: string;
  status: string;
  category_id: string | null;
  author_id: string;
  submitted_at: string | null;
  due_at: string | null;
  pickup_due_at: string | null;
  picked_up_at: string | null;
  reviewer_id: string | null;
  reviewer_name: string | null;
  days_until_due: number | null;
}

export interface ReviewScores {
  impact?: number | null;
  effort?: number | null;
  alignment?: number | null;
  comment?: string;
}

export type DecisionKind = 'accept' | 'park' | 'merge' | 'decline' | 'info';

export interface DecideRequest extends ReviewScores {
  decision: DecisionKind;
  reason: string;
  owner_id?: string | null;
  awaiting_owner?: boolean;
  hours?: number | null;
  revisit_at?: string | null;
  target_id?: string | null;
  change_mind?: string;
}

export interface Decision {
  id: string;
  idea_id: string;
  outcome: string;
  reason: string;
  decider_id: string;
  as_role: string;
  owner_id: string | null;
  awaiting_owner: boolean;
  hours: number | null;
  revisit_at: string | null;
  merged_into_id: string | null;
  change_mind: string;
  question: string;
  impact: number | null;
  effort: number | null;
  alignment: number | null;
  created_at: string;
}
