/**
 * Saved AI review for an idea (generated after submit). Shown to the author and the reviewer.
 * Every item is a proposal; nothing here changes the idea.
 */
import type { DotKonnektFitBand, IdeaAiReview as AiReview } from '../types/idea';
import { AgentBlock } from './ui/AgentBlock';
import { Pill } from './ui/Pill';

const BAND: Record<DotKonnektFitBand, { label: string; variant: string }> = {
  strong: { label: 'Strong DotKonnekt fit', variant: 'success' },
  partial: { label: 'Partial DotKonnekt fit', variant: 'info' },
  exploratory: { label: 'Exploratory', variant: '' },
};

const FIELD_LABEL: Record<string, string> = {
  title: 'Title',
  problem: 'Problem',
  solution: 'Solution',
  beneficiaries: 'Beneficiaries',
  success_metrics: 'Success metrics',
  category_id: 'Category',
  tags: 'Tags',
};

function fieldLabel(field: string): string {
  return FIELD_LABEL[field] ?? field.replace(/_/g, ' ');
}

function fmtWhen(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleString();
}

interface Props {
  review: AiReview | null | undefined;
  /** Drafts never get a review, so the "being prepared" state is hidden for them. */
  isDraft: boolean;
  /** Reviewer view words the footer for the decision maker. */
  audience?: 'author' | 'reviewer';
}

export function IdeaAiReview({ review, isDraft, audience = 'author' }: Props) {
  if (isDraft) return null;
  const foot =
    audience === 'reviewer'
      ? 'Generated when the idea was submitted. Suggestions only; the reviewer makes the decision.'
      : 'Generated when you submitted. Suggestions only; nothing changes your idea unless you edit it.';

  if (!review) {
    return (
      <AgentBlock agent="AI review" kind="DotKonnekt fit" how={foot} status="Pending">
        <p className="muted">No AI review yet. New submissions get one within a minute; ideas submitted before this feature have none.</p>
      </AgentBlock>
    );
  }

  const fit = review.dotkonnekt_fit;
  const band = BAND[fit?.band] ?? BAND.exploratory;
  return (
    <AgentBlock
      agent="AI review"
      kind="DotKonnekt fit"
      status={review.simulated ? 'Simulated' : 'Live'}
      how={`${foot}${review.generated_at ? ` Generated ${fmtWhen(review.generated_at)}.` : ''}`}
    >
      <div className="ai-review stack">
        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          <Pill variant={band.variant}>{band.label}</Pill>
          {(fit?.themes ?? []).map((t) => (
            <Pill key={t.id} title={t.matched_terms.join(', ')}>
              {t.label}
            </Pill>
          ))}
        </div>
        {review.summary ? <p style={{ margin: 0 }}>{review.summary}</p> : null}

        {fit?.angles?.length ? (
          <section>
            <h4 className="ai-review__h">Ways it could serve DotKonnekt</h4>
            <ul className="ai-review__list">
              {fit.angles.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </section>
        ) : null}

        {review.suggestions?.length ? (
          <section>
            <h4 className="ai-review__h">Suggestions</h4>
            <ul className="ai-review__rows">
              {review.suggestions.map((s, i) => (
                <li key={i} className="ai-review__row">
                  <span className="ai-review__field">{fieldLabel(s.field)}</span>
                  <div>
                    <div>{s.text}</div>
                    {s.rationale ? <div className="muted small">{s.rationale}</div> : null}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {review.suggested_metrics?.length ? (
          <section>
            <h4 className="ai-review__h">Metrics to consider</h4>
            <ul className="ai-review__list">
              {review.suggested_metrics.map((m, i) => (
                <li key={i}>
                  {m.metric}
                  {m.unit ? <span className="muted"> ({m.unit})</span> : null}
                  {m.baseline_prompt ? (
                    <div className="muted small">{m.baseline_prompt}</div>
                  ) : null}
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        {review.suggested_beneficiaries?.length ? (
          <section>
            <h4 className="ai-review__h">Who else could benefit</h4>
            <p className="small" style={{ margin: 0 }}>
              {review.suggested_beneficiaries.join(' · ')}
            </p>
          </section>
        ) : null}

        {review.missing_fields?.length ? (
          <p className="small" style={{ margin: 0 }}>
            <strong>Still thin:</strong> {review.missing_fields.map(fieldLabel).join(', ')}
          </p>
        ) : null}
      </div>
    </AgentBlock>
  );
}

export default IdeaAiReview;
