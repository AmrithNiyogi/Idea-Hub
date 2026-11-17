/** Shared display helpers ported from idea-hub.html SEL.* / fmt* patterns. */

import type { Idea } from '../types/idea';

export function relTime(iso: string | null | undefined): string {
  if (!iso) return '—';
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms)) return '—';
  const m = Math.floor(ms / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

export function fmtDate(
  iso: string | null | undefined,
  withYear = false,
): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: withYear ? 'numeric' : undefined,
  });
}

export function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function firstName(name: string | undefined | null): string {
  if (!name) return 'there';
  return name.trim().split(/\s+/)[0] || 'there';
}

/** Mirrors HTML SEL.nextStep(i) for status → next action copy. */
export function nextStep(idea: Idea): { text: string; who: string } {
  switch (idea.status) {
    case 'draft':
      return { text: 'Finish the draft and submit to start the review clock.', who: 'Author' };
    case 'submitted':
      return {
        text: 'Waiting for a reviewer on the category panel to pick this up.',
        who: 'Review panel',
      };
    case 'under_review':
      return {
        text: idea.picked_up_at
          ? 'A reviewer is scoring this idea and will record a decision.'
          : 'In the review queue, awaiting pickup.',
        who: 'Reviewer',
      };
    case 'needs_info':
      return {
        text: idea.needs_info_question
          ? `Answer the reviewer: “${idea.needs_info_question}”`
          : 'The reviewer asked a question. Answer to resume the review clock.',
        who: 'Author',
      };
    case 'accepted':
      return {
        text: idea.owner_id
          ? 'Owner should request innovation hours to start delivery.'
          : 'Needs an owner before innovation hours can be requested.',
        who: idea.owner_id ? 'Owner' : 'Team lead',
      };
    case 'parked':
      return {
        text: idea.revisit_at
          ? `Parked until ${fmtDate(idea.revisit_at, true)}. Conditions may reopen it earlier.`
          : 'Parked. Waiting on revisit conditions.',
        who: 'Review panel',
      };
    case 'merged':
      return {
        text: idea.merged_into_id
          ? 'Merged into another idea. Authors are credited there.'
          : 'Merged into another idea.',
        who: '—',
      };
    case 'declined':
      return { text: 'Declined. See the decision reason for what would change minds.', who: '—' };
    case 'prototype':
      return {
        text: 'In delivery. Log hours, post updates, and mark implemented when live.',
        who: 'Owner',
      };
    case 'implemented':
      return { text: 'Delivered. Impact and credit are recorded on the Delivery tab.', who: '—' };
    case 'withdrawn':
      return { text: 'Withdrawn by the author.', who: '—' };
    default:
      return { text: 'See the idea page for the current status.', who: '—' };
  }
}

export function trunc(s: string, n: number): string {
  const t = (s || '').trim();
  if (t.length <= n) return t;
  return `${t.slice(0, n - 1)}…`;
}
