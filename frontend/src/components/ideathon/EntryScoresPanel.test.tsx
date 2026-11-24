import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { EntryScoresPanel } from './EntryScoresPanel';
import { evidenceText, fmtScore } from './entryScores';
import { ideathonsApi } from '../../api/ideathons';
import { ApiError } from '../../api/http';
import type { EntryScore, EntryScores } from '../../types/ideathon';

vi.mock('../../api/ideathons', () => ({
  ideathonsApi: { scores: vi.fn(), runScores: vi.fn() },
}));

const score: EntryScore = {
  idea_id: 'idea-1',
  rank: 1,
  overall: 7.25,
  criteria: {
    relevance: { score: 8, rationale: 'Answers challenge one.' },
    feasibility: { score: 7, rationale: 'Repo has tests.' },
    impact: { score: 6.5, rationale: 'Names a measure.' },
    originality: { score: null, rationale: '' },
  },
  rationale: 'Strong entry overall.',
  engine: 'heuristic-rubric',
  simulated: true,
  evidence: {
    github: {
      status: 'ok',
      full_name: 'acme/app',
      languages: { Python: 100 },
      readme_chars: 900,
      file_count: 42,
      has_tests: true,
      has_ci: true,
      recent_commits: 12,
    },
    documents: [{ filename: 'design.pdf', text_chars: 1200 }],
    has_demo: true,
  },
  scored_at: '2026-11-24T10:00:00Z',
};

const payload: EntryScores = { ideathon_id: 't1', rubric_version: 'v1', items: [score] };

describe('entry score helpers', () => {
  it('formats scores and evidence', () => {
    expect(fmtScore(7.25)).toBe('7.3');
    expect(fmtScore(null)).toBe('—');
    expect(evidenceText(score)).toBe('GitHub read · 1 doc · demo');
    expect(
      evidenceText({
        ...score,
        evidence: { ...score.evidence, github: { ...score.evidence.github, status: 'missing' }, documents: [], has_demo: false },
      }),
    ).toBe('No GitHub · 0 docs');
  });
});

describe('EntryScoresPanel', () => {
  beforeEach(() => {
    vi.mocked(ideathonsApi.scores).mockReset();
    vi.mocked(ideathonsApi.runScores).mockReset();
  });

  it('shows saved scores and expands the reasons', async () => {
    vi.mocked(ideathonsApi.scores).mockResolvedValue(payload);
    render(<EntryScoresPanel ideathonId="t1" canRun={false} titles={{ 'idea-1': 'Faster CI' }} />);
    expect(await screen.findByText('Faster CI')).toBeInTheDocument();
    expect(screen.getByText('7.3')).toBeInTheDocument();
    expect(screen.getByText('Simulated')).toBeInTheDocument();
    expect(screen.getByText(/admin makes the final decision/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /score all/i })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /show reasons for faster ci/i }));
    expect(screen.getByText('Answers challenge one.')).toBeInTheDocument();
    expect(screen.getByText(/Repository acme\/app: 42 files, 12 recent commits, tests, CI · Python/)).toBeInTheDocument();
  });

  it('lets an organiser score all entries when none are saved', async () => {
    vi.mocked(ideathonsApi.scores).mockRejectedValue(new ApiError(404, 'none'));
    vi.mocked(ideathonsApi.runScores).mockResolvedValue({ ...payload, items: [{ ...score, simulated: false }] });
    render(<EntryScoresPanel ideathonId="t1" canRun titles={{}} />);
    expect(await screen.findByText(/No scores yet. Press Score all entries/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: /score all entries/i }));
    await waitFor(() => expect(ideathonsApi.runScores).toHaveBeenCalledWith('t1'));
    expect(await screen.findByText('Kompass')).toBeInTheDocument();
    expect(screen.getByText(/Entry idea-1/)).toBeInTheDocument();
  });

  it('shows load and run errors', async () => {
    vi.mocked(ideathonsApi.scores).mockRejectedValue(new Error('Forbidden'));
    vi.mocked(ideathonsApi.runScores).mockRejectedValue(new Error('Scoring broke'));
    render(<EntryScoresPanel ideathonId="t1" canRun titles={{}} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Forbidden');
    await userEvent.click(screen.getByRole('button', { name: /score all entries/i }));
    expect(await screen.findByText('Scoring broke')).toBeInTheDocument();
  });
});

describe('EntryScoresPanel onScores', () => {
  beforeEach(() => vi.clearAllMocks());

  it('reports loaded and re-run scores to the parent', async () => {
    vi.mocked(ideathonsApi.scores).mockResolvedValue(payload);
    vi.mocked(ideathonsApi.runScores).mockResolvedValue(payload);
    const onScores = vi.fn();
    render(<EntryScoresPanel ideathonId="t1" canRun titles={{}} onScores={onScores} />);
    await waitFor(() => expect(onScores).toHaveBeenCalledWith(payload));
    await userEvent.click(await screen.findByRole('button', { name: /score all entries/i }));
    await waitFor(() => expect(onScores).toHaveBeenCalledTimes(2));
  });
});

describe('EntryScoresPanel fallback note', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows why Kompass was not used', async () => {
    const fallback: EntryScore = {
      ...score,
      evidence: { ...score.evidence, scoring_note: 'Kompass Rank agent failed (gateway timeout); scored locally.' },
    };
    vi.mocked(ideathonsApi.scores).mockResolvedValue({ ...payload, items: [fallback] });
    render(<EntryScoresPanel ideathonId="t1" canRun={false} titles={{}} />);
    expect(await screen.findByRole('status')).toHaveTextContent(/gateway timeout/);
  });
});
