/** Display helpers for saved AI rubric scores. */
import type { EntryScore, RubricCriterion } from '../../types/ideathon';

export const CRITERIA: Array<{ id: RubricCriterion; label: string }> = [
  { id: 'relevance', label: 'Relevance' },
  { id: 'feasibility', label: 'Feasibility' },
  { id: 'impact', label: 'Impact' },
  { id: 'originality', label: 'Originality' },
];

export function fmtScore(n: number | null | undefined): string {
  return typeof n === 'number' && Number.isFinite(n) ? n.toFixed(1) : '—';
}

const GITHUB_LABEL: Record<string, string> = {
  ok: 'GitHub read',
  missing: 'No GitHub',
  unreachable: 'GitHub unreachable',
};

/** One-line evidence summary, e.g. "GitHub read · 2 docs · demo". */
export function evidenceText(s: EntryScore): string {
  const parts = [GITHUB_LABEL[s.evidence?.github?.status] ?? 'No GitHub'];
  const docs = s.evidence?.documents?.length ?? 0;
  parts.push(docs === 1 ? '1 doc' : `${docs} docs`);
  if (s.evidence?.has_demo) parts.push('demo');
  return parts.join(' · ');
}
