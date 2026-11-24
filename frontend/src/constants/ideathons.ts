/** Ideathon phases — mirrors backend + idea-hub.html `ITH_PHASES`. */

export const ITH_PHASES = [
  { id: 'open', label: 'Open', blurb: 'Submissions are open' },
  {
    id: 'shortlist',
    label: 'Shortlist',
    blurb: 'Agent proposes, organiser approves',
  },
  {
    id: 'pitch',
    label: 'Pitch day',
    blurb: 'Pitches, panel scores and audience votes',
  },
  {
    id: 'results',
    label: 'Results',
    blurb: 'Ranking proposed, winners confirmed',
  },
  {
    id: 'handoff',
    label: 'Handoff',
    blurb: 'Problem statements go to the hackathon backlog',
  },
] as const;

export type IdeathonPhase = (typeof ITH_PHASES)[number]['id'];

export const IT_NEXT: Record<string, string> = {
  open: 'shortlist',
  shortlist: 'pitch',
  pitch: 'results',
  results: 'handoff',
};

export const PANEL_WEIGHT = 70;
export const AUDIENCE_WEIGHT = 30;
export const PITCH_SECONDS = 300;

export const ORG_ROLES = ['leadership', 'admin'] as const;
export const PANEL_SCORE_ROLES = ['reviewer', 'leadership', 'admin'] as const;

export function ithPhaseIdx(phase: string): number {
  const i = ITH_PHASES.findIndex((p) => p.id === phase);
  return i < 0 ? 0 : i;
}

export type IthStatus = 'active' | 'upcoming' | 'past';

export function ithStatus(
  startAt: string,
  endAt: string,
  completedAt?: string | null,
  now = Date.now(),
): IthStatus {
  if (completedAt) return 'past';
  const start = new Date(startAt).getTime();
  const end = new Date(endAt).getTime();
  if (now < start) return 'upcoming';
  if (now > end && !completedAt) return 'active';
  return 'active';
}

export function fmtDate(iso: string, withYear = false): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(withYear ? { year: 'numeric' } : {}),
  });
}

export function fmtNum(n: number): string {
  return new Intl.NumberFormat().format(Math.round(n));
}

export function fmtClock(sec: number): string {
  const s = Math.max(0, Math.ceil(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

export function quarterKey(d = new Date()): string {
  return `${d.getFullYear()}-Q${Math.floor(d.getMonth() / 3) + 1}`;
}

export function quarterLabel(key: string): string {
  const m = /^(\d{4})-Q([1-4])$/.exec(key);
  if (!m) return key;
  const labels = ['Jan–Mar', 'Apr–Jun', 'Jul–Sep', 'Oct–Dec'];
  return `${labels[Number(m[2]) - 1]} ${m[1]}`;
}

export const PERIODS: Record<string, string> = {
  quarter: 'This quarter',
  year: 'This year',
  all: 'All time',
};

/** Display names for the event kinds. */
export const EVENT_KIND_LABEL: Record<'ideathon' | 'hackathon', string> = {
  ideathon: 'Ideathon',
  hackathon: 'Hackathon',
};
