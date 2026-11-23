/**
 * Organiser panel for the Ideathon Rank and Pitch agents.
 * Results are proposals. Nothing here changes the ideathon until an organiser acts on it.
 */
import { useState } from 'react';
import { ideathonsApi } from '../../api/ideathons';
import type { AgentRunResult } from '../../types/ideathon';
import {
  fmtScore,
  hackathonStatements,
  pitchSummaries,
  rankRows,
  splitReply,
} from './agentReply';
import { AgentWaiting } from '../ui/AgentWaiting';
import { ReplyText } from './ReplyText';

type AgentKind = 'rank' | 'pitch';

interface Props {
  ideathonId: string;
  /** Scoring weights from the ideathon, as percentages (e.g. 70 and 30). */
  panelWeight: number;
  audienceWeight: number;
  /** Entry titles by idea id, so results show names rather than ids. */
  titles: Record<string, string>;
}

function titleOf(titles: Record<string, string>, ideaId: string): string {
  return titles[ideaId] ?? `Entry ${ideaId.slice(0, 8)}…`;
}

/** The agent's own notes, collapsed so the result stays the main view. */
function Notes({ prose }: { prose: string }) {
  if (!prose) return null;
  const words = prose.split(/\s+/).length;
  return (
    <details className="agent-runs__notes">
      <summary>Agent notes ({words} words)</summary>
      <ReplyText text={prose} />
    </details>
  );
}

function RankResult({ text, titles }: { text: string; titles: Record<string, string> }) {
  const { prose, data } = splitReply(text);
  const rows = rankRows(data);
  if (rows.length === 0) return <ReplyText text={text} />;
  return (
    <>
      <Notes prose={prose} />
      <div className="agent-runs__table-wrap">
        <table className="agent-runs__table">
          <thead>
            <tr>
              <th scope="col">Rank</th>
              <th scope="col">Entry</th>
              <th scope="col">Overall</th>
              <th scope="col">Relevance</th>
              <th scope="col">Feasibility</th>
              <th scope="col">Impact</th>
              <th scope="col">Originality</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const c = row.criteriaScores;
              return (
                <tr key={row.ideaId}>
                  <td>{row.rank}</td>
                  <td>{titleOf(titles, row.ideaId)}</td>
                  <td>{fmtScore(c.overall?.weightedTotal, 2)}</td>
                  <td>{fmtScore(c.relevance?.weightedScore)}</td>
                  <td>{fmtScore(c.feasibility?.weightedScore)}</td>
                  <td>{fmtScore(c.impact?.weightedScore)}</td>
                  <td>{fmtScore(c.originality?.weightedScore)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="agent-runs__rationales">
        {rows.map((row) => (
          <div key={row.ideaId} className="agent-runs__rationale">
            <div className="agent-runs__rationale-head">
              <span className="agent-runs__rank">#{row.rank}</span>
              {titleOf(titles, row.ideaId)}
            </div>
            <ReplyText text={row.rationale || 'No rationale given.'} />
          </div>
        ))}
      </div>
    </>
  );
}

function PitchResult({ text, titles }: { text: string; titles: Record<string, string> }) {
  const { prose, data } = splitReply(text);
  const summaries = pitchSummaries(data);
  const statements = hackathonStatements(data);
  if (summaries.length === 0 && statements.length === 0) return <ReplyText text={text} />;
  return (
    <>
      <Notes prose={prose} />
      <div className="agent-runs__cards">
        {summaries.map((p) => {
          const statement = statements.find((s) => s.ideaId === p.ideaId);
          return (
            <article key={p.ideaId} className="agent-runs__card">
              <h4 className="agent-runs__card-title">{titleOf(titles, p.ideaId)}</h4>
              <p className="agent-runs__one-liner">{p.oneLiner}</p>
              <dl className="agent-runs__fields">
                <dt>Problem</dt>
                <dd>{p.problem}</dd>
                <dt>Solution</dt>
                <dd>{p.solution}</dd>
                <dt>Ask</dt>
                <dd>{p.ask}</dd>
              </dl>
              {statement ? (
                <div className="agent-runs__statement">
                  <div className="eyebrow eyebrow--plain">Hackathon statement</div>
                  <p>{statement.statement}</p>
                  {statement.successCriteria.length > 0 ? (
                    <ul>
                      {statement.successCriteria.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </>
  );
}

export function AgentRunsPanel({ ideathonId, panelWeight, audienceWeight, titles }: Props) {
  const [busy, setBusy] = useState<AgentKind | null>(null);
  const [result, setResult] = useState<{ kind: AgentKind; run: AgentRunResult } | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(kind: AgentKind) {
    setBusy(kind);
    setError(null);
    setResult(null);
    try {
      const run =
        kind === 'rank'
          ? await ideathonsApi.runRank(ideathonId, {
              panel: panelWeight / 100,
              audience: audienceWeight / 100,
            })
          : await ideathonsApi.runPitch(ideathonId, { stage: 'both' });
      if (!run.success) {
        setError(run.error || 'The agent run failed.');
      } else {
        setResult({ kind, run });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The agent run failed.');
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="agent-runs" aria-label="Ideathon agents">
      <div className="agent-runs__head">
        <div>
          <div className="eyebrow eyebrow--plain">Agents</div>
          <p className="muted small">
            Proposals only. Nothing changes until you act on what the agent suggests.
          </p>
        </div>
        <div className="agent-runs__actions">
          <button
            type="button"
            className="btn"
            disabled={busy !== null}
            onClick={() => void run('rank')}
          >
            {busy === 'rank' ? 'Running rank…' : 'Run rank'}
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy !== null}
            onClick={() => void run('pitch')}
          >
            {busy === 'pitch' ? 'Running pitch…' : 'Run pitch'}
          </button>
        </div>
      </div>

      {busy ? (
        <AgentWaiting
          label={busy === 'rank' ? 'Scoring the entries' : 'Drafting the pitches'}
        />
      ) : null}

      {error ? (
        <p className="agent-runs__error" role="alert">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="agent-runs__result">
          <div className="eyebrow eyebrow--plain">
            {result.kind === 'rank' ? 'Proposed shortlist' : 'Proposed pitch and handoff'}
          </div>
          {!result.run.result_text ? (
            <p className="muted small">The agent returned an empty reply.</p>
          ) : result.kind === 'rank' ? (
            <RankResult text={result.run.result_text} titles={titles} />
          ) : (
            <PitchResult text={result.run.result_text} titles={titles} />
          )}
        </div>
      ) : null}
    </section>
  );
}
