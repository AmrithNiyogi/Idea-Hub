import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { agentsApi } from '../api/agents';
import { ideasApi } from '../api/ideas';
import { reviewApi } from '../api/review';
import { AgentHandoffBar } from '../components/AgentHandoffBar';
import { EntryDocumentsCard } from '../components/EntryDocumentsCard';
import { IdeaAiReview } from '../components/IdeaAiReview';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { AgentBlock } from '../components/ui/AgentBlock';
import { EFFORT_LABELS, STATUS_META } from '../constants/status';
import { fmtDate, relTime } from '../utils/format';
import type { Comment, Idea, IdeaStatus } from '../types/idea';
import type { DecisionKind } from '../types/review';

/** Suggested score cell from review-intelligence (heuristic stub). */
type SuggestedScore = {
  value?: number;
  confidence?: number;
  evidence?: string[];
};

/** Peer from review_brief.similar_ideas (Kompass-ready contract). */
type SimilarIdeaHit = {
  idea_id?: string;
  title?: string;
  status?: string;
  similarity?: number;
  shared_terms?: string[];
  can_join?: boolean;
};

type ReviewBriefOut = {
  summary?: string;
  discussion_summary?: {
    pros?: string[];
    concerns?: string[];
    open_questions?: string[];
  };
  risks?: Array<{ risk?: string; source?: string }>;
  similar_ideas?: SimilarIdeaHit[];
  suggested_scores?: {
    impact?: SuggestedScore;
    effort?: SuggestedScore;
    alignment?: SuggestedScore;
  };
  decision_lean?: {
    option?: string;
    rationale?: string;
    caveats?: string[];
  };
  suggested_decision?: {
    decision?: string;
    reason?: string;
    confidence?: number;
    simulated?: boolean;
    /** Merge target UUID when lean is merge (top eligible peer). */
    target_id?: string | null;
  };
  simulated?: boolean;
};

/** Matches review_service.decide merge-target allow-list + HTML mergeTargets. */
const MERGE_TARGET_STATUSES: IdeaStatus[] = [
  'under_review',
  'needs_info',
  'accepted',
  'prototype',
  'parked',
];

function truncTitle(title: string, max = 70): string {
  const t = title.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max - 1)}…`;
}

const DECISION_IDS = new Set([
  'accept',
  'park',
  'merge',
  'decline',
  'info',
]);

function mapSuggestedDecision(raw: string | undefined): DecisionKind | null {
  if (!raw) return null;
  const key = raw === 'needs_info' ? 'info' : raw;
  return DECISION_IDS.has(key) ? (key as DecisionKind) : null;
}

function scoreValue(s: SuggestedScore | undefined): number | null {
  const v = s?.value;
  if (typeof v !== 'number' || v < 1 || v > 5) return null;
  return Math.round(v);
}

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
  const [targetId, setTargetId] = useState('');
  const [mergeTargets, setMergeTargets] = useState<Idea[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [brief, setBrief] = useState<ReviewBriefOut | null>(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [scoresApplied, setScoresApplied] = useState(false);
  const [decisionApplied, setDecisionApplied] = useState(false);

  useEffect(() => {
    ideasApi
      .get(id)
      .then((i) => {
        setIdea(i);
        setTargetId('');
        ideasApi.listComments(i.id).then(setComments).catch(() => setComments([]));
        ideasApi
          .list({ status: MERGE_TARGET_STATUSES, limit: 100 })
          .then((res) => {
            setMergeTargets(
              (res.items || []).filter((t) => t.id !== i.id),
            );
          })
          .catch(() => setMergeTargets([]));
      })
      .catch((e) =>
        setError(e instanceof Error ? e.message : 'Failed to load idea'),
      );
  }, [id]);

  // Phase A stub: agent-first brief via local heuristic (not Kompass).
  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setBrief(null);
    setBriefError(null);
    setScoresApplied(false);
    setDecisionApplied(false);
    setBriefLoading(true);
    agentsApi
      .run({
        agent_id: 'review-intelligence',
        event: 'review.opened',
        idea_id: id,
        record: false,
      })
      .then((run) => {
        if (cancelled) return;
        setBrief((run.output || {}) as ReviewBriefOut);
      })
      .catch((e) => {
        if (cancelled) return;
        setBriefError(
          e instanceof Error ? e.message : 'Could not load review brief',
        );
      })
      .finally(() => {
        if (!cancelled) setBriefLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const applySuggestedScores = () => {
    const s = brief?.suggested_scores;
    if (!s) return;
    const nextImpact = scoreValue(s.impact);
    const nextEffort = scoreValue(s.effort);
    const nextAlignment = scoreValue(s.alignment);
    if (nextImpact != null) setImpact(nextImpact);
    if (nextEffort != null) setEffort(nextEffort);
    if (nextAlignment != null) setAlignment(nextAlignment);
    setScoresApplied(true);
  };

  const applySuggestedDecision = () => {
    const sd = brief?.suggested_decision;
    const mapped =
      mapSuggestedDecision(sd?.decision) ||
      mapSuggestedDecision(brief?.decision_lean?.option);
    if (!mapped) return;
    setDecision(mapped);
    const draftReason = (sd?.reason || '').trim();
    if (draftReason.length >= 20) {
      setReason(draftReason);
    } else if (brief?.decision_lean?.rationale) {
      const fallback =
        `${brief.decision_lean.rationale} Simulated draft — edit before recording.`.trim();
      setReason(fallback.length >= 20 ? fallback : fallback.padEnd(20, '.'));
    }
    if (mapped === 'merge') {
      const tid = (sd?.target_id || '').trim();
      if (tid) setTargetId(tid);
    }
    setDecisionApplied(true);
  };

  const relatedMergeIds = useMemo(() => {
    const ids = new Set(
      (brief?.similar_ideas || [])
        .slice(0, 3)
        .map((s) => s.idea_id)
        .filter((x): x is string => Boolean(x)),
    );
    return ids;
  }, [brief?.similar_ideas]);

  /** Related IDs from brief first (HTML: Possible match), then A–Z title. */
  const orderedMergeTargets = useMemo(() => {
    const byId = new Map(mergeTargets.map((t) => [t.id, t]));
    // Ensure brief peers / suggested target appear even if list fetch is slow.
    for (const hit of brief?.similar_ideas || []) {
      const sid = hit.idea_id;
      if (!sid || sid === idea?.id || byId.has(sid)) continue;
      const st = (hit.status || 'under_review') as IdeaStatus;
      if (!MERGE_TARGET_STATUSES.includes(st)) continue;
      byId.set(sid, {
        id: sid,
        title: hit.title || sid,
        status: st,
      } as Idea);
    }
    const suggested = brief?.suggested_decision?.target_id;
    if (
      suggested &&
      suggested !== idea?.id &&
      !byId.has(suggested) &&
      brief?.suggested_decision?.decision === 'merge'
    ) {
      byId.set(suggested, {
        id: suggested,
        title: 'Suggested merge target',
        status: 'under_review',
      } as Idea);
    }
    return [...byId.values()].sort((a, b) => {
      const ar = relatedMergeIds.has(a.id) ? 1 : 0;
      const br = relatedMergeIds.has(b.id) ? 1 : 0;
      if (br !== ar) return br - ar;
      return a.title.localeCompare(b.title);
    });
  }, [
    mergeTargets,
    brief?.similar_ideas,
    brief?.suggested_decision?.target_id,
    brief?.suggested_decision?.decision,
    idea?.id,
    relatedMergeIds,
  ]);

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
    if (decision === 'merge' && !targetId.trim()) {
      setError('Choose the idea to merge into.');
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
        target_id: decision === 'merge' ? targetId.trim() : null,
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
              {idea.github_url ? (
                <>
                  <dt>GitHub</dt>
                  <dd>
                    <a href={idea.github_url} target="_blank" rel="noreferrer">
                      {idea.github_url.replace('https://github.com/', 'github.com/')}
                    </a>
                  </dd>
                </>
              ) : null}
              {idea.demo_url ? (
                <>
                  <dt>Live project</dt>
                  <dd>
                    <a href={idea.demo_url} target="_blank" rel="noreferrer">
                      {idea.demo_url.replace(/^https:\/\//, '')}
                    </a>
                  </dd>
                </>
              ) : null}
            </dl>
          </div>

          <IdeaAiReview
            review={idea.ai_review}
            isDraft={idea.status === 'draft'}
            audience="reviewer"
          />
          <EntryDocumentsCard ideaId={idea.id} canEdit={false} />

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
          <AgentBlock
            agent="Review Intelligence"
            kind="Computed · stub"
            how="STUB (not Kompass): deterministic local heuristic via POST /agents/run with agent_id=review-intelligence. Suggests only — never writes scores of record. Apply fills the form; you edit and Save / Record."
          >
            {briefLoading ? (
              <p className="muted small">Preparing reviewer brief…</p>
            ) : null}
            {briefError ? (
              <p className="muted small" role="alert">
                {briefError}
              </p>
            ) : null}
            {!briefLoading && !briefError && brief ? (
              <>
                {brief.summary ? (
                  <div>
                    <h4 style={{ margin: '0 0 6px' }}>Summary</h4>
                    <p style={{ margin: 0 }}>{brief.summary}</p>
                  </div>
                ) : null}
                {brief.risks && brief.risks.length ? (
                  <div>
                    <h4 style={{ margin: '0 0 6px' }}>Risks</h4>
                    <ul className="bullets">
                      {brief.risks.slice(0, 4).map((r, i) => (
                        <li key={i}>
                          {r.risk || '—'}
                          {r.source ? (
                            <span className="muted small"> ({r.source})</span>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                {brief.suggested_scores ? (
                  <div>
                    <h4 style={{ margin: '0 0 6px' }}>
                      Suggested scores{' '}
                      <span className="pill pill--agent">Simulated</span>
                    </h4>
                    <ul className="bullets">
                      {(['impact', 'effort', 'alignment'] as const).map(
                        (key) => {
                          const cell = brief.suggested_scores?.[key];
                          const v = scoreValue(cell);
                          return (
                            <li key={key}>
                              <strong style={{ textTransform: 'capitalize' }}>
                                {key}
                              </strong>
                              : {v != null ? `${v}/5` : '—'}
                              {cell?.evidence?.[0] ? (
                                <span className="muted small">
                                  {' '}
                                  — {cell.evidence[0]}
                                </span>
                              ) : null}
                            </li>
                          );
                        },
                      )}
                    </ul>
                    {(brief.suggested_decision?.decision ||
                      brief.decision_lean?.option) && (
                      <div
                        className="notice notice--brand"
                        style={{ marginTop: 8 }}
                      >
                        <span>
                          <strong>
                            Suggested decision:{' '}
                            {brief.suggested_decision?.decision ||
                              brief.decision_lean?.option}
                            {brief.suggested_decision?.decision === 'merge' &&
                            brief.suggested_decision?.target_id
                              ? ' (target set)'
                              : ''}
                            .
                          </strong>{' '}
                          <span className="pill pill--agent">Simulated</span>
                          <div className="muted small" style={{ marginTop: 4 }}>
                            {(() => {
                              const r =
                                brief.suggested_decision?.reason ||
                                brief.decision_lean?.rationale ||
                                '';
                              return r.length > 180 ? `${r.slice(0, 180)}…` : r;
                            })()}
                          </div>
                          <span className="muted small">
                            Proposal only — Apply fills the Decision card; you
                            still Record.
                          </span>
                        </span>
                      </div>
                    )}
                    {open ? (
                      <div
                        className="row"
                        style={{ marginTop: 10, flexWrap: 'wrap', gap: 8 }}
                      >
                        <button
                          type="button"
                          className="btn btn--sm btn--primary"
                          disabled={busy || !brief.suggested_scores}
                          onClick={applySuggestedScores}
                        >
                          <Icon name="spark" size={14} /> Apply suggested
                          scores
                        </button>
                        <button
                          type="button"
                          className="btn btn--sm"
                          disabled={
                            busy ||
                            !(
                              brief.suggested_decision?.decision ||
                              brief.decision_lean?.option
                            )
                          }
                          onClick={applySuggestedDecision}
                        >
                          <Icon name="spark" size={14} /> Apply suggested
                          decision
                        </button>
                        <span className="muted small">
                          {scoresApplied || decisionApplied
                            ? 'Applied to the form — edit before Save / Record.'
                            : 'Does not save or record. You confirm below.'}
                        </span>
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
            {!briefLoading && !briefError && !brief ? (
              <p className="muted small">No brief available.</p>
            ) : null}
          </AgentBlock>

          {open ? (
            <form className="stack" onSubmit={decide}>
              <div className="card">
                <div className="card__head">
                  <h2>Your scores</h2>
                  <span className="muted small">
                    1 to 5 — agent may prefill; you confirm
                  </span>
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
                    {decisionApplied
                      ? 'Prefill from Simulated agent — edit, then Record'
                      : 'Agent may prefill; only you Record'}
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

                {decision === 'merge' ? (
                  <div className="decision-fields" style={{ marginTop: 14 }}>
                    <div className="field">
                      <label htmlFor="rv-target">
                        Merge into{' '}
                        <span style={{ color: 'var(--danger)' }}>*</span>
                      </label>
                      <select
                        className="select"
                        id="rv-target"
                        value={targetId}
                        onChange={(e) => setTargetId(e.target.value)}
                        required
                        aria-invalid={!targetId ? true : undefined}
                      >
                        <option value="">Choose an idea</option>
                        {orderedMergeTargets.map((t) => {
                          const statusLabel =
                            STATUS_META[t.status]?.label ||
                            t.status.replace(/_/g, ' ');
                          const possible = relatedMergeIds.has(t.id);
                          return (
                            <option key={t.id} value={t.id}>
                              {possible ? 'Possible match: ' : ''}
                              {truncTitle(t.title)} ({statusLabel})
                            </option>
                          );
                        })}
                      </select>
                      <div className="hint">
                        All authors of this idea become co-authors on the
                        target. This idea stays visible as “Merged into”.
                      </div>
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
