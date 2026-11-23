/**
 * Splits an agent reply into the prose written before its JSON and the parsed JSON object.
 * The agents write a short note, then one JSON object. Anything else is shown as written.
 */

export interface SplitReply {
  prose: string;
  data: Record<string, unknown> | null;
}

export function splitReply(text: string): SplitReply {
  const start = text.indexOf('{');
  const end = text.lastIndexOf('}');
  if (start < 0 || end <= start) return { prose: text.trim(), data: null };
  try {
    const parsed: unknown = JSON.parse(text.slice(start, end + 1));
    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
      return { prose: text.slice(0, start).trim(), data: parsed as Record<string, unknown> };
    }
  } catch {
    // Not JSON: fall through and show the text as written.
  }
  return { prose: text.trim(), data: null };
}

export interface CriterionScore {
  panelScore?: number;
  audienceScore?: number;
  weightedScore?: number;
}

export interface RankRow {
  ideaId: string;
  rank: number;
  criteriaScores: Record<string, CriterionScore> & { overall?: { weightedTotal?: number } };
  rationale: string;
}

export interface PitchSummary {
  ideaId: string;
  oneLiner: string;
  problem: string;
  solution: string;
  ask: string;
}

export interface HackathonStatement {
  ideaId: string;
  statement: string;
  successCriteria: string[];
}

export function rankRows(data: Record<string, unknown> | null): RankRow[] {
  const raw = data?.shortlistSuggestion;
  if (!Array.isArray(raw)) return [];
  return (raw as RankRow[])
    .filter((r) => r && typeof r.ideaId === 'string')
    .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
}

export function pitchSummaries(data: Record<string, unknown> | null): PitchSummary[] {
  const raw = data?.pitchSummaries;
  return Array.isArray(raw) ? (raw as PitchSummary[]).filter((p) => p && p.ideaId) : [];
}

export function hackathonStatements(data: Record<string, unknown> | null): HackathonStatement[] {
  const raw = data?.hackathonStatements;
  return Array.isArray(raw)
    ? (raw as HackathonStatement[]).filter((h) => h && h.ideaId)
    : [];
}

/** A score for display, or a dash when the agent gave none. */
export function fmtScore(value: number | undefined, digits = 1): string {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(digits) : '–';
}
