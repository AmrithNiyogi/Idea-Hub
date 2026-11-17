import type { Role } from '../types/auth';

export const ROLE_LABELS: Record<Role, string> = {
  contributor: 'Contributor',
  reviewer: 'Reviewer',
  lead: 'Team lead',
  leadership: 'Leadership',
  admin: 'Administrator',
};

/** Home page blurbs — same copy as idea-hub.html ROLES.*.blurb */
export const ROLE_BLURBS: Record<Role, string> = {
  contributor: 'Submit and follow ideas, collaborate, track your own ideas.',
  reviewer: 'Work the review queue, score ideas and record decisions.',
  lead: 'Take ownership of accepted ideas and run them through delivery.',
  leadership: 'See pipeline health, bottlenecks and impact.',
  admin: 'Configure the platform and reset demo data.',
};

export const ROLE_ORDER: Role[] = [
  'contributor',
  'reviewer',
  'lead',
  'leadership',
  'admin',
];

export const CAN_SUBMIT: Role[] = ['contributor', 'reviewer', 'lead'];

export const REVIEW_ROLES: Role[] = ['reviewer', 'admin'];

export function roleLabel(role: string): string {
  return ROLE_LABELS[role as Role] ?? role;
}

export function sortRoles(roles: string[]): Role[] {
  return ROLE_ORDER.filter((r) => roles.includes(r));
}
