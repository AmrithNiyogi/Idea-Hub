import type { IdeaStatus } from '../types/idea';

/**
 * Status → pill variant map (mirrors idea-hub.html STATUS).
 * Variants resolve to distinct hues via CSS tokens:
 * brand=purple, info=indigo, success=green, warning=amber, danger=red, gold=award.
 */
export const STATUS_META: Record<
  IdeaStatus,
  { label: string; variant: string }
> = {
  draft: { label: 'Draft', variant: 'neutral' },
  submitted: { label: 'Submitted', variant: 'info' },
  under_review: { label: 'Under review', variant: 'brand' },
  needs_info: { label: 'Needs info', variant: 'warning' },
  accepted: { label: 'Accepted', variant: 'success' },
  parked: { label: 'Parked', variant: 'warning' },
  merged: { label: 'Merged', variant: 'neutral' },
  declined: { label: 'Declined', variant: 'danger' },
  prototype: { label: 'Prototype', variant: 'info' },
  implemented: { label: 'Implemented', variant: 'success' },
  withdrawn: { label: 'Withdrawn', variant: 'neutral' },
};

export const STAGE_KEYS = [
  'submitted',
  'under_review',
  'accepted',
  'prototype',
  'implemented',
] as const;

export const STAGE_LABELS = [
  'Submitted',
  'Under review',
  'Decision',
  'Prototype',
  'Implemented',
] as const;

export const EFFORT_LABELS: Record<string, string> = {
  S: 'Small (days)',
  M: 'Medium (weeks)',
  L: 'Large (a quarter)',
  XL: 'Extra large (multi-quarter)',
};

export const TAG_VOCAB = [
  'ci-cd',
  'testing',
  'automation',
  'observability',
  'docs',
  'cost',
  'performance',
  'security',
  'agents',
  'support',
  'onboarding',
  'analytics',
  'customer-feedback',
  'sales-enablement',
  'partners',
  'pricing',
  'meetings',
  'compliance',
  'accessibility',
  'design-system',
  'knowledge-base',
  'integrations',
  'reporting',
  'templates',
];
