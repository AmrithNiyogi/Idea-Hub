/**
 * Organiser panel for the Ideathon Rank and Pitch agents.
 * Results are proposals. Nothing here changes the ideathon until an organiser acts on it.
 */
import { useState } from 'react';
import { ideathonsApi } from '../../api/ideathons';
import type { AgentRunResult } from '../../types/ideathon';

type AgentKind = 'rank' | 'pitch';

interface Props {
  ideathonId: string;
  /** Scoring weights from the ideathon, as percentages (e.g. 70 and 30). */
  panelWeight: number;
  audienceWeight: number;
}

/** Pretty-print the reply when it is JSON; otherwise show it as written. */
function formatReply(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

export function AgentRunsPanel({ ideathonId, panelWeight, audienceWeight }: Props) {
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
          <pre>{result.run.result_text ? formatReply(result.run.result_text) : '(empty reply)'}</pre>
        </div>
      ) : null}
    </section>
  );
}
