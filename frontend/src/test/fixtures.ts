/**
 * Shared fixtures for unit / component tests.
 *
 * Keeps Idea / User shapes stable so individual specs stay focused on behaviour.
 */

import type { User } from '../types/auth';
import type { Category, Idea } from '../types/idea';

export const mockUser: User = {
  id: 'u1',
  email: 'alice@example.com',
  name: 'Alice Example',
  title: 'Engineer',
  team_id: 't1',
  roles: ['contributor', 'reviewer'],
  primary_role: 'contributor',
  active_role: 'contributor',
  status: 'active',
  avatar: 1,
  slug: 'alice',
};

export function makeIdea(overrides: Partial<Idea> = {}): Idea {
  return {
    id: 'idea-1',
    slug: 'sample-idea',
    title: 'Sample idea',
    category_id: 'cat-1',
    problem: 'We lose time on manual releases.',
    solution: 'Automate the pipeline.',
    beneficiaries: 'Platform team',
    effort: 'M',
    success_metrics: 'Deploy time under 10m',
    tags: ['ci-cd', 'automation', 'testing', 'docs', 'extra'],
    author_id: 'u1',
    anonymous: false,
    co_author_ids: [],
    owner_id: null,
    status: 'submitted',
    is_draft: false,
    reviewer_id: null,
    awaiting_owner: false,
    hours_recommended: null,
    needs_info_question: null,
    withdraw_reason: '',
    merged_into_id: null,
    submitted_at: '2026-01-01T12:00:00.000Z',
    picked_up_at: null,
    due_at: null,
    pickup_due_at: null,
    revisit_at: null,
    stage_entered_at: '2026-01-01T12:00:00.000Z',
    created_at: '2026-01-01T10:00:00.000Z',
    updated_at: '2026-01-01T12:00:00.000Z',
    vote_count: 3,
    follow_count: 2,
    comment_count: 1,
    voted: false,
    following: false,
    status_history: [],
    ...overrides,
  };
}

export const mockCategory: Category = {
  id: 'cat-1',
  slug: 'platform',
  label: 'Platform',
  color: '#5b6cff',
  description: 'Platform & tooling',
};
