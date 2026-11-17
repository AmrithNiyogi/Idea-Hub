import type { LedgerEntry, Level } from './recognition';

export interface ProfileIdeaRef {
  id: string;
  title: string;
  status: string;
  role: string;
}

export interface Profile {
  user_id: string;
  name?: string | null;
  title?: string | null;
  team_id?: string | null;
  roles: string[];
  points: number;
  level: Level;
  badges: Array<{
    badge_id: string;
    name: string;
    icon: string;
    awarded_at: string;
    note: string;
  }>;
  submitted: ProfileIdeaRef[];
  co_authored: ProfileIdeaRef[];
  implemented: ProfileIdeaRef[];
  impact: {
    hours_saved: number;
    hours_verified: number;
    usd_influenced: number;
    ideas_credited: number;
  };
  ledger: LedgerEntry[];
  history: Array<{
    at: string;
    role: string;
    idea_id: string;
    idea_title: string;
    extra: string;
  }>;
  dims: Record<string, number>;
  is_self: boolean;
}
