export interface Pool {
  period_key: string;
  budget_hours: number;
  granted_hours: number;
  remaining: number;
}

export interface HoursRequest {
  id: string;
  idea_id: string;
  requested_by: string;
  hours: number;
  justification: string;
  state: string;
  decided_by?: string | null;
  decided_at?: string | null;
  granted_hours?: number | null;
  reason: string;
  override: boolean;
  created_at: string;
}

export interface DeliveryTask {
  id: string;
  idea_id: string;
  title: string;
  description: string;
  assignee_id?: string | null;
  due_at?: string | null;
  status: string;
  blocker: string;
  sort_order: number;
  done_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeliveryUpdate {
  id: string;
  user_id: string;
  body: string;
  task_id?: string | null;
  created_at: string;
}

export interface ImpactEntry {
  id: string;
  impact_type: string;
  value: number;
  unit: string;
  baseline: number;
  evidence: string;
  confidence: string;
  created_by: string;
  created_at: string;
  verified_by?: string | null;
  verified_at?: string | null;
  verify_note: string;
}

export interface DeliveryDetail {
  idea_id: string;
  project_id?: string | null;
  hours_granted?: number | null;
  hours_logged: number;
  started_at?: string | null;
  implemented_at?: string | null;
  outcome: string;
  pending_request?: HoursRequest | null;
  hour_logs: Array<{
    id: string;
    user_id: string;
    work_date: string;
    hours: number;
    note: string;
    created_at: string;
  }>;
  tasks: DeliveryTask[];
  updates: DeliveryUpdate[];
  contributors: Array<{
    user_id: string;
    role: string;
    added_at: string;
    added_by: string;
  }>;
  impact: ImpactEntry[];
  shares: Array<{ user_id: string; roles: string[]; pct: number }>;
  pool?: Pool | null;
}

export interface HoursRequestBody {
  hours: number;
  justification: string;
}

export interface HoursDecideBody {
  approve: boolean;
  hours?: number;
  reason?: string;
  override?: boolean;
}

export interface HoursLogBody {
  hours: number;
  work_date: string;
  note: string;
}

export interface TaskCreateBody {
  title: string;
  description?: string;
  assignee_id?: string;
  status?: string;
}

export interface TaskStatusBody {
  status: string;
  blocker?: string;
}

export interface MarkImplementedBody {
  outcome: string;
  impact: Array<{
    impact_type: string;
    value: number;
    baseline: number;
    unit?: string;
    evidence: string;
    confidence: 'low' | 'medium' | 'high';
  }>;
  shares: Array<{ user_id: string; roles: string[]; pct: number }>;
}
