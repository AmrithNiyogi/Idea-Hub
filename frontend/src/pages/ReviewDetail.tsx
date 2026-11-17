import { FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { reviewApi } from '../api/review';
import { AgentHandoffBar } from '../components/AgentHandoffBar';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { EFFORT_LABELS } from '../constants/status';
import { fmtDate, relTime } from '../utils/format';
import type { Comment, Idea } from '../types/idea';
import type { DecisionKind } from '../types/review';

const DECISIONS: Array<{
  id: DecisionKind;
  label: string;
  desc: string;
  ic: string;
}> = [
  {
    id: 'accept',
    label: 'Accept',
    desc: 'Worth doing. Needs an owner and recommended hours.',
    ic: 'checkcircle',
  },
  {
    id: 'park',
    label: 'Park',
    desc: 'Not now. Needs a revisit date.',
    ic: 'pause',
  },
  {
    id: 'merge',
    label: 'Merge',
    desc: 'Same goal as another idea. Authors are credited there.',
    ic: 'merge',
  },
  {
    id: 'decline',
    label: 'Decline',
    desc: 'Will not proceed. Say what would change our mind.',
    ic: 'ban',
  },
  {
    id: 'info',
    label: 'Request info',
    desc: 'Ask the author a question. The review clock pauses.',
    ic: 'help',
  },
];

const REASON_LABEL: Record<string, string> = {
  '': 'Written reason',
  accept: 'Why accept? The author and followers will read this',
  park: 'Why park, and what are we waiting for?',
  merge: 'Why merge? Both authors will read this',
  decline: 'Why decline? The author will read this',
  info: 'Question for the author',
};

const CRITERIA = [
  {
    key: 'impact',
    label: 'Impact',
    low: 'local / cosmetic',
    high: 'company-wide / material',
    weight: 40,
  },
  {
    key: 'effort',
    label: 'Effort',
    low: 'weeks',
    high: 'multi-quarter',
    weight: 30,
  },
  {
    key: 'alignment',
    label: 'Alignment',
    low: 'tangential',
    high: 'strategic priority',
    weight: 30,
  },
] as const;

export function ReviewDetailPage() {
  const { id = '' } = useParams();
  const navigate = useNavigate();
  const [idea, setIdea] = useState<Idea | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [impact, setImpact] = useState<number | null>(null);
  const [effort, setEffort] = useState<number | null>(null);
  const [alignment, setAlignment] = useState<number | null>(null);
  const [comment, setComment] = useState('');
  const [decision, setDecision] = useState<DecisionKind | ''>('');
  const [reason, setReason] = useState('');
  const [changeMind, setChangeMind] = useState('');
  const [revisitAt, setRevisitAt] = useState('');
  const [hours, setHours] = useState('');
  const [awaitingOwner, setAwaitingOwner] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    ideasApi
      .get(id)
      .then((i) => {
        setIdea(i);
        ideasApi.listComments(i.id).then(setComments).catch(() => setComments([]));
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Failed to load idea'),
      );
  }, [id]);

  const pickup = async () => {
    setBusy(true);
    setError(null);
    try {
      const updated = await reviewApi.pickup(id);
      setIdea(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Pickup failed');
    } finally {
      setBusy(false);
    }
  };

  const saveScores = async () => {
    if (impact == null && effort == null && alignment == null) {
      setError('Choose at least one score to save.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await reviewApi.saveScores(id, { impact, effort, alignment, comment });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save scores');
    } finally {
      setBusy(false);
    }
  };

  const weighted = (() => {
    if (impact == null || effort == null || alignment == null) return null;
    // Effort reverse-scored like HTML
    const eRev = 6 - effort;
    return (
      Math.round(
        ((impact * 40 + eRev * 30 + alignment * 30) / 100) * 10,
      ) / 10
    );
  })();

  const decide = async (e: FormEvent) => {
    e.preventDefault();
    if (!decision) {
      setError('Choose a decision.');
      return;
    }
    if (reason.trim().length < 20) {
      setError('Decision reason must be at least 20 characters.');
      return;
    }
    if (decision === 'decline' && changeMind.trim().length < 10) {
      setError('Say what would change our mind (at least 10 characters).');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await reviewApi.decide(id, {
        decision,
        reason: reason.trim(),
        impact,
        effort,
        alignment,
        comment,
        change_mind: changeMind.trim() || undefined,
        revisit_at: revisitAt || null,
        hours: hours ? Number(hours) : null,
        awaiting_owner: awaitingOwner,
      });
      navigate(`/ideas/${id}?tab=decision`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Decision failed');
    } finally {
      setBusy(false);
    }
  };

  if (error && !idea) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  if (!idea) return <p className="muted">Loading…</p>;

  const open = idea.status === 'under_review';
  const scoreSetters = {
    impact: setImpact,
    effort: setEffort,
    alignment: setAlignment,
  } as const;
  const scoreVals = { impact, effort, alignment };

  return (
    <div className="stack stack--lg">
      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="layout-rail layout-rail--wide layout-rail--review">
        <div className="stack">
          <div className="card">
            <div className="row" style={{ gap: 6 }}>
              <StatusPill status={idea.status} />
              {idea.due_at ? (
                <span className="pill">
                  <Icon name="clock" size={12} /> Due {fmtDate(idea.due_at, true)}
                </span>
              ) : null}
            </div>
            <h1 className="idea-title">{idea.title}</h1>
            <AgentHandoffBar ideaId={idea.id} compact />
            <div className="meta-row">
              <span className="muted">
                Submitted {fmtDate(idea.submitted_at, true)}
              </span>
              {idea.due_at ? (
                <span className="muted">
                  Decision due {fmtDate(idea.due_at, true)}
                </span>
              ) : null}
              <span className="chip-row">
                {idea.tags.map((t) => (
                  <span key={t} className="tag">
                    {t}
                  </span>
                ))}
              </span>
            </div>

            {!open ? (
              <div className="notice notice--warn" style={{ marginBottom: 12 }}>
                <Icon name="info" size={16} />
                <span>
                  {idea.status === 'needs_info'
                    ? `The review clock is paused while the author answers: “${idea.needs_info_question || '—'}”`
                    : `This idea is ${idea.status.replace(/_/g, ' ')}, so no further decision can be recorded here.`}{' '}
                  <Link to={`/ideas/${idea.id}`}>Open the idea page</Link>
                </span>
              </div>
            ) : null}

            {open && !idea.picked_up_at ? (
              <div
                className="notice notice--brand"
                style={{ marginBottom: 12 }}
              >
                <Icon name="inbox" size={16} />
                <span className="grow">
                  Nobody has picked this up yet
                  {idea.pickup_due_at
                    ? `. Pickup was due ${fmtDate(idea.pickup_due_at)}.`
                    : '.'}
                </span>
                <button
                  type="button"
                  className="btn btn--sm btn--primary"
                  disabled={busy}
                  onClick={pickup}
                >
                  Pick up
                </button>
              </div>
            ) : null}

            <dl className="dl">
              <dt>Problem</dt>
              <dd>{idea.problem || '—'}</dd>
              <dt>Proposed solution</dt>
              <dd>{idea.solution || '—'}</dd>
              <dt>Who benefits</dt>
              <dd>{idea.beneficiaries || '—'}</dd>
              <dt>Rough effort</dt>
              <dd>{EFFORT_LABELS[idea.effort] ?? idea.effort}</dd>
              <dt>Success looks like</dt>
              <dd>{idea.success_metrics || '—'}</dd>
            </dl>
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Discussion</h2>
              <Link
                className="btn btn--sm"
                to={`/ideas/${idea.id}?tab=discussion`}
              >
                Open full thread
              </Link>
            </div>
            {comments.length ? (
              comments.slice(-8).map((c) => (
                <div key={c.id} className="comment">
                  <div className="grow">
                    <strong>{c.author_id.slice(0, 8)}</strong>
                    <span className="muted small"> {relTime(c.created_at)}</span>
                    <div className="comment__body">{c.body}</div>
                  </div>
                </div>
              ))
            ) : (
              <p className="muted">No comments yet.</p>
            )}
          </div>
        </div>

        <div className="rv-right">
          {open ? (
            <form className="stack" onSubmit={decide}>
              <div className="card">
                <div className="card__head">
                  <h2>Your scores</h2>
                  <span className="muted small">1 to 5, entered by you</span>
                </div>
                {CRITERIA.map((c) => (
                  <div key={c.key} className="score-row">
                    <div>
                      <strong>{c.label}</strong>
                      <div className="muted small">
                        1 = {c.low}; 5 = {c.high}. Weight {c.weight}%.
                      </div>
                    </div>
                    <div className="segmented" role="group" aria-label={c.label}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <label key={n}>
                          <input
                            type="radio"
                            name={`rv-${c.key}`}
                            checked={scoreVals[c.key] === n}
                            onChange={() => scoreSetters[c.key](n)}
                          />
                          <span>{n}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
                <p className="small" role="status" style={{ marginTop: 8 }}>
                  {weighted == null
                    ? 'Weighted score appears once all three criteria are scored (Impact 40%, Effort 30% reverse, Alignment 30%).'
                    : `Weighted score: ${weighted} out of 5. A guide for you, not a decision.`}
                </p>
                <div className="field" style={{ marginTop: 12 }}>
                  <label htmlFor="rv-comment">Reviewer comment (optional)</label>
                  <textarea
                    id="rv-comment"
                    className="textarea"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    rows={2}
                    placeholder="Notes for the panel"
                  />
                </div>
                <div className="row" style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={saveScores}
                  >
                    Save scores
                  </button>
                  <span className="muted small">
                    Saving keeps your scores without recording a decision.
                  </span>
                </div>
              </div>

              <div className="card">
                <div className="card__head">
                  <h2>Decision</h2>
                  <span className="muted small">
                    Starts empty. Only you can record it.
                  </span>
                </div>
                <div
                  className="radio-cards"
                  role="radiogroup"
                  aria-label="Decision"
                >
                  {DECISIONS.map((d) => (
                    <label key={d.id} className="radio-card">
                      <input
                        type="radio"
                        name="rv-decision"
                        checked={decision === d.id}
                        onChange={() => setDecision(d.id)}
                      />
                      <span className="radio-card__title">
                        <Icon name={d.ic} size={16} />
                        {d.label}
                      </span>
                      <span className="radio-card__desc">{d.desc}</span>
                    </label>
                  ))}
                </div>

                {decision === 'accept' ? (
                  <div className="decision-fields" style={{ marginTop: 14 }}>
                    <label className="check">
                      <input
                        type="checkbox"
                        checked={awaitingOwner}
                        onChange={(e) => setAwaitingOwner(e.target.checked)}
                      />
                      <span>
                        Awaiting owner. Nobody is named yet, and this idea will
                        show up for team leads to pick up.
                      </span>
                    </label>
                    <div className="field">
                      <label htmlFor="rv-hours">
                        Recommended innovation hours
                      </label>
                      <input
                        className="input"
                        id="rv-hours"
                        type="number"
                        min={1}
                        max={400}
                        value={hours}
                        onChange={(e) => setHours(e.target.value)}
                        placeholder="For example 40"
                        style={{ maxWidth: 200 }}
                      />
                    </div>
                  </div>
                ) : null}

                {decision === 'park' ? (
                  <div className="decision-fields" style={{ marginTop: 14 }}>
                    <div className="field">
                      <label htmlFor="rv-revisit">Revisit date</label>
                      <input
                        className="input"
                        id="rv-revisit"
                        type="date"
                        value={revisitAt}
                        onChange={(e) => setRevisitAt(e.target.value)}
                        style={{ maxWidth: 220 }}
                      />
                    </div>
                  </div>
                ) : null}

                {decision === 'decline' ? (
                  <div className="decision-fields" style={{ marginTop: 14 }}>
                    <div className="field">
                      <label htmlFor="rv-changemind">
                        What would change our mind?
                      </label>
                      <textarea
                        className="textarea"
                        id="rv-changemind"
                        rows={2}
                        value={changeMind}
                        onChange={(e) => setChangeMind(e.target.value)}
                        placeholder="Evidence, a smaller scope or a pilot that would make the panel look again"
                      />
                    </div>
                  </div>
                ) : null}

                <div className="field" style={{ marginTop: 14 }}>
                  <label htmlFor="rv-reason">
                    {REASON_LABEL[decision] || REASON_LABEL['']}{' '}
                    <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <textarea
                    id="rv-reason"
                    className="textarea"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    rows={4}
                    required
                    minLength={20}
                    placeholder="At least 20 characters. Be specific about what drove the decision."
                  />
                  <div className="hint">
                    Required for every decision. It becomes part of the permanent
                    decision history. ({reason.trim().length}/20)
                  </div>
                </div>

                <div className="row" style={{ marginTop: 12 }}>
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={busy || !decision}
                  >
                    <Icon name="check" size={16} />{' '}
                    {busy ? 'Recording…' : 'Record decision'}
                  </button>
                  <span className="muted small">
                    The author, co-authors and followers are notified.
                  </span>
                </div>
              </div>
            </form>
          ) : (
            <div className="card">
              <p className="muted">
                Open the{' '}
                <Link to={`/ideas/${idea.id}`}>idea page</Link> for the full
                record. This workspace only records decisions while status is
                under review.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
