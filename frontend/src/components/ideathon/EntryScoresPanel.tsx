/**
 * Saved AI rubric scores for every entry (relevance, feasibility, impact, originality).
 * Scores are proposals that help the panel; the admin makes the final decision.
 */
import { Fragment, useEffect, useRef, useState } from 'react';
import { ApiError } from '../../api/client';
import { ideathonsApi } from '../../api/ideathons';
import type { EntryScore, EntryScores } from '../../types/ideathon';
import { Icon } from '../Icons';
import { AgentWaiting } from '../ui/AgentWaiting';
import { CRITERIA, evidenceText, fmtScore } from './entryScores';

function repoLine(s: EntryScore): string {
  const gh = s.evidence.github;
  const extras = [gh.has_tests ? 'tests' : '', gh.has_ci ? 'CI' : ''].filter(Boolean);
  const langs = Object.keys(gh.languages ?? {});
  return [
    `Repository ${gh.full_name ?? ''}: ${gh.file_count} files, ${gh.recent_commits} recent commits`,
    extras.length ? `, ${extras.join(', ')}` : '',
    langs.length ? ` · ${langs.join(', ')}` : '',
  ].join('');
}

interface Props {
  ideathonId: string;
  /** Leadership / admin can run scoring. Reviewers can read. */
  canRun: boolean;
  titles: Record<string, string>;
  /** Called with the saved scores whenever they load or are re-run. */
  onScores?: (scores: EntryScores | null) => void;
}

export function EntryScoresPanel({ ideathonId, canRun, titles, onScores }: Props) {
  const [data, setData] = useState<EntryScores | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  // Latest callback without re-fetching when the parent re-renders.
  const onScoresRef = useRef(onScores);
  useEffect(() => {
    onScoresRef.current = onScores;
  });

  useEffect(() => {
    let alive = true;
    ideathonsApi
      .scores(ideathonId)
      .then((d) => {
        if (!alive) return;
        setData(d);
        onScoresRef.current?.(d);
        setError(null);
      })
      .catch((e: unknown) => {
        if (!alive) return;
        if (e instanceof ApiError && e.status === 404) setData(null);
        else setError(e instanceof Error ? e.message : 'Could not load scores');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [ideathonId]);

  const runAll = async () => {
    setRunning(true);
    setError(null);
    try {
      const fresh = await ideathonsApi.runScores(ideathonId);
      setData(fresh);
      onScoresRef.current?.(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Scoring failed');
    } finally {
      setRunning(false);
    }
  };

  const items = data?.items ?? [];
  const simulated = items.some((s) => s.simulated);
  const engineLabel = items.length ? (simulated ? 'Simulated' : 'Kompass') : 'Not run';
  const scoredAt = items.reduce<string | null>(
    (latest, s) => (!latest || s.scored_at > latest ? s.scored_at : latest),
    null,
  );
  const titleOf = (id: string) => titles[id] ?? `Entry ${id.slice(0, 8)}…`;
  const fallbackNote = items.find((s) => s.evidence?.scoring_note)?.evidence.scoring_note;

  return (
    <section className="agent-runs entry-scores" aria-label="AI rubric scores">
      <div className="agent-runs__head">
        <div>
          <h2 style={{ margin: 0 }}>
            AI rubric scores <span className="pill pill--agent">{engineLabel}</span>
          </h2>
          <p className="muted small">
            Every entry is scored 0–10 on relevance, feasibility, impact and originality, using its
            text, documents and GitHub repository. Author names are hidden from the scorer. These are
            suggestions: the admin makes the final decision.
            {simulated ? ' Simulated scores come from a local rubric scorer, not Kompass.' : ''}
          </p>
          {fallbackNote ? (
            <p className="entry-scores__note small" role="status">
              {fallbackNote}
            </p>
          ) : null}
          {scoredAt ? (
            <p className="muted small">
              Last scored {new Date(scoredAt).toLocaleString()}
              {data?.rubric_version ? ` · rubric ${data.rubric_version}` : ''}
            </p>
          ) : null}
        </div>
        {canRun ? (
          <div className="agent-runs__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={running}
              onClick={() => void runAll()}
            >
              <Icon name="spark" size={16} />{' '}
              {items.length ? 'Re-score all entries' : 'Score all entries'}
            </button>
          </div>
        ) : null}
      </div>

      {error ? (
        <p className="agent-runs__error" role="alert">
          {error}
        </p>
      ) : null}
      {running ? <AgentWaiting label="Scoring every entry" /> : null}

      {!loading && !items.length && !running ? (
        <p className="muted small">
          {canRun
            ? 'No scores yet. Press Score all entries to score every entry with the rubric.'
            : 'No scores yet. Leadership or an admin can run scoring.'}
        </p>
      ) : null}

      {items.length ? (
        <div className="agent-runs__table-wrap">
          <table className="agent-runs__table">
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Entry</th>
                <th scope="col">Overall</th>
                {CRITERIA.map((c) => (
                  <th scope="col" key={c.id}>
                    {c.label}
                  </th>
                ))}
                <th scope="col">Evidence</th>
                <th scope="col">Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((s) => {
                const expanded = open === s.idea_id;
                return (
                  <Fragment key={s.idea_id}>
                    <tr>
                      <td>{s.rank}</td>
                      <td>{titleOf(s.idea_id)}</td>
                      <td>
                        <strong>{fmtScore(s.overall)}</strong>
                      </td>
                      {CRITERIA.map((c) => (
                        <td key={c.id}>{fmtScore(s.criteria?.[c.id]?.score)}</td>
                      ))}
                      <td>{evidenceText(s)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          aria-expanded={expanded}
                          aria-label={`${expanded ? 'Hide' : 'Show'} reasons for ${titleOf(s.idea_id)}`}
                          onClick={() => setOpen(expanded ? null : s.idea_id)}
                        >
                          {expanded ? 'Hide' : 'Why'}
                        </button>
                      </td>
                    </tr>
                    {expanded ? (
                      <tr className="entry-scores__detail">
                        <td colSpan={CRITERIA.length + 5}>
                          {s.rationale ? <p style={{ marginTop: 0 }}>{s.rationale}</p> : null}
                          <dl className="dl">
                            {CRITERIA.map((c) => (
                              <Fragment key={c.id}>
                                <dt>
                                  {c.label} · {fmtScore(s.criteria?.[c.id]?.score)}
                                </dt>
                                <dd>{s.criteria?.[c.id]?.rationale || '—'}</dd>
                              </Fragment>
                            ))}
                          </dl>
                          {s.evidence?.github?.status === 'ok' ? (
                            <p className="muted small" style={{ marginBottom: 0 }}>
                              {repoLine(s)}
                            </p>
                          ) : null}
                          <p className="muted small" style={{ marginBottom: 0 }}>
                            {s.simulated ? 'Simulated' : 'Kompass'} ({s.engine})
                          </p>
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default EntryScoresPanel;
