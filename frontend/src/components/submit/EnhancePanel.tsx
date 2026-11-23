/**
 * Improve one field of a draft idea with the Idea Enhancement agent.
 * Suggestions are proposals. Nothing changes in the draft until the author clicks "Use".
 */
import { useState } from 'react';
import { agentsApi } from '../../api/agents';
import type { IdeaWrite } from '../../types/idea';
import { AgentWaiting } from '../ui/AgentWaiting';

export type EnhanceField = 'title' | 'problem' | 'solution' | 'beneficiaries' | 'success_metrics';

const FIELD_LABELS: Record<EnhanceField, string> = {
  title: 'Title',
  problem: 'Problem',
  solution: 'Solution',
  beneficiaries: 'Beneficiaries',
  success_metrics: 'Success metrics',
};

interface Suggestion {
  kind?: string;
  text?: string;
  rationale?: string;
}

interface MetricSuggestion {
  metric?: string;
  unit?: string;
}

interface Proposal {
  suggestions: Suggestion[];
  beneficiaries: string[];
  metrics: MetricSuggestion[];
  impactBand: string | null;
  impactAssumptions: string[];
}

/** Reads the workflow's camelCase keys or the simulated snake_case keys. */
function readProposal(out: Record<string, unknown>): Proposal {
  const pick = (camel: string, snake: string): unknown => out[camel] ?? out[snake];
  const list = (v: unknown): unknown[] => (Array.isArray(v) ? v : []);
  const impact = pick('impactEstimate', 'impact_estimate') as
    | { band?: string; assumptions?: unknown }
    | undefined;
  return {
    suggestions: list(out.suggestions).filter((s): s is Suggestion => !!s && typeof s === 'object'),
    beneficiaries: list(pick('suggestedBeneficiaries', 'suggested_beneficiaries')).filter(
      (b): b is string => typeof b === 'string',
    ),
    metrics: list(pick('suggestedMetrics', 'suggested_metrics')).filter(
      (m): m is MetricSuggestion => !!m && typeof m === 'object',
    ),
    impactBand: typeof impact?.band === 'string' ? impact.band : null,
    impactAssumptions: list(impact?.assumptions).filter((a): a is string => typeof a === 'string'),
  };
}

export function EnhancePanel({
  draft,
  onApply,
}: {
  draft: IdeaWrite;
  onApply: (field: EnhanceField, text: string) => void;
}) {
  const [field, setField] = useState<EnhanceField>('problem');
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState<boolean | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function suggest() {
    setBusy(true);
    setError(null);
    setProposal(null);
    try {
      const res = await agentsApi.run({
        agent_id: 'idea-enhancement',
        event: 'idea.enhance',
        record: false,
        context: {
          field,
          draft: {
            title: draft.title,
            problem: draft.problem ?? '',
            solution: draft.solution ?? '',
            beneficiaries: draft.beneficiaries ?? '',
            success_metrics: draft.success_metrics ?? '',
            tags: draft.tags ?? [],
          },
        },
      });
      setLive(!res.simulated);
      setProposal(readProposal(res.output));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The enhancement agent did not respond.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card card--tight" style={{ marginTop: 12 }}>
      <div className="row row--between" style={{ alignItems: 'center' }}>
        <h4 style={{ margin: 0 }}>Improve a field</h4>
        {proposal ? (
          <span className="pill pill--agent">{live ? 'Live' : 'Simulated'}</span>
        ) : null}
      </div>

      <div className="row" style={{ gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
        <select
          className="select"
          aria-label="Field to improve"
          value={field}
          onChange={(e) => setField(e.target.value as EnhanceField)}
          disabled={busy}
        >
          {(Object.keys(FIELD_LABELS) as EnhanceField[]).map((f) => (
            <option key={f} value={f}>
              {FIELD_LABELS[f]}
            </option>
          ))}
        </select>
        <button className="btn btn--ghost" type="button" onClick={() => void suggest()} disabled={busy}>
          {busy ? 'Working…' : 'Suggest improvements'}
        </button>
      </div>

      {busy ? (
        <div style={{ marginTop: 8 }}>
          <AgentWaiting label={`Working on the ${FIELD_LABELS[field].toLowerCase()}`} />
        </div>
      ) : null}

      {error ? (
        <p className="muted small" role="alert" style={{ marginTop: 8 }}>
          {error}
        </p>
      ) : null}

      {proposal ? (
        <div className="stack stack--sm" style={{ marginTop: 12 }}>
          {proposal.suggestions.length === 0 ? (
            <p className="muted small" style={{ margin: 0 }}>
              No suggestions for this field.
            </p>
          ) : (
            proposal.suggestions.map((s, i) => (
              <div key={i} className="similar">
                {s.kind ? <div className="eyebrow eyebrow--plain">{s.kind}</div> : null}
                {s.text ? <p style={{ margin: '4px 0' }}>{s.text}</p> : null}
                {s.rationale ? (
                  <p className="muted small" style={{ margin: 0 }}>
                    {s.rationale}
                  </p>
                ) : null}
                {s.text ? (
                  <div className="row" style={{ justifyContent: 'flex-end', marginTop: 6 }}>
                    <button
                      className="btn btn--sm btn--ghost"
                      type="button"
                      onClick={() => onApply(field, s.text ?? '')}
                    >
                      Use for {FIELD_LABELS[field].toLowerCase()}
                    </button>
                  </div>
                ) : null}
              </div>
            ))
          )}

          {proposal.beneficiaries.length ? (
            <div>
              <div className="eyebrow eyebrow--plain">Beneficiaries</div>
              <ul className="bullets" style={{ paddingLeft: 18, margin: '4px 0' }}>
                {proposal.beneficiaries.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {proposal.metrics.length ? (
            <div>
              <div className="eyebrow eyebrow--plain">Metrics to consider</div>
              <ul className="bullets" style={{ paddingLeft: 18, margin: '4px 0' }}>
                {proposal.metrics.map((m, i) => (
                  <li key={i}>
                    {m.metric}
                    {m.unit ? <span className="muted small"> ({m.unit})</span> : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {proposal.impactBand ? (
            <p className="muted small" style={{ margin: 0 }}>
              Impact: {proposal.impactBand}
              {proposal.impactAssumptions.length ? ` — ${proposal.impactAssumptions.join('; ')}` : ''}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
