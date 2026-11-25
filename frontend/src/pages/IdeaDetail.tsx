import {
  type CSSProperties,
  type FormEvent,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { collabApi } from '../api/collab';
import { ideasApi } from '../api/ideas';
import { usersApi } from '../api/users';
import { AgentBuildPanel } from '../components/AgentBuildPanel';
import { AgentHandoffBar } from '../components/AgentHandoffBar';
import { IdeaOptimizePanel } from '../components/IdeaOptimizePanel';
import { IdeaAiReview } from '../components/IdeaAiReview';
import { EntryDocumentsCard } from '../components/EntryDocumentsCard';
import { Avatar, Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { JourneyStepper, type JourneyStage } from '../components/ui/JourneyStepper';
import { useAuth } from '../auth/AuthProvider';
import { EFFORT_LABELS } from '../constants/status';
import { DeliveryTab } from './DeliveryTab';
import { TrackerTab } from './TrackerTab';
import { CollabTrackerPanel } from '../components/CollabTrackerPanel';
import { groupsApi } from '../api/groups';
import { fmtDate, nextStep, relTime } from '../utils/format';
import type { User } from '../types/auth';
import type { Category, Comment, Effort, Idea } from '../types/idea';
import type { CollabRequest } from '../types/phase456';
import type { Group } from '../types/groups';
import { useDialog } from '../components/DialogProvider';

type Tab =
  | 'overview'
  | 'discussion'
  | 'decision'
  | 'team'
  | 'delivery'
  | 'tracker'
  | 'activity';

const TABS: Array<[Tab, string]> = [
  ['overview', 'Overview'],
  ['discussion', 'Discussion'],
  ['decision', 'Decision history'],
  ['team', 'Team & progress'],
  ['delivery', 'Delivery'],
  ['tracker', 'Tracker'],
  ['activity', 'Activity'],
];

function stageIndex(status: string): number {
  if (['submitted'].includes(status)) return 0;
  if (['under_review', 'needs_info'].includes(status)) return 1;
  if (['accepted', 'parked', 'merged', 'declined'].includes(status)) return 2;
  if (status === 'prototype') return 3;
  if (status === 'implemented') return 4;
  return -1;
}

/** Each stage, what moves the idea on, and who has to act. Matches the status transitions in the backend. */
const IDEA_STAGES: JourneyStage[] = [
  {
    label: 'Submitted',
    gate: 'A reviewer on the category panel picks it up.',
    owner: 'Review panel',
  },
  {
    label: 'Under review',
    gate: 'A reviewer scores it and records a decision with a reason.',
    owner: 'Reviewer',
  },
  {
    label: 'Decision',
    gate: 'The owner requests innovation hours to start a prototype.',
    owner: 'Owner',
  },
  {
    label: 'Prototype',
    gate: 'The owner marks it implemented and records the impact.',
    owner: 'Owner',
  },
  {
    label: 'Implemented',
    gate: 'Final stage. A second person can verify the recorded impact.',
    owner: 'Verifier',
  },
];

export function IdeaDetailPage() {
  const dialog = useDialog();
  const { id = '' } = useParams();
  const [search, setSearch] = useSearchParams();
  const { user } = useAuth();
  const rawTab = search.get('tab');
  const tab: Tab =
    rawTab === 'history'
      ? 'decision'
      : rawTab === 'collab'
        ? 'team'
        : TABS.some(([t]) => t === rawTab)
          ? (rawTab as Tab)
          : 'overview';
  const [idea, setIdea] = useState<Idea | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [related, setRelated] = useState<Idea[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [collabReqs, setCollabReqs] = useState<CollabRequest[]>([]);
  const [linkedGroup, setLinkedGroup] = useState<Group | null>(null);
  // Until the lookup answers, neither Open group nor Create group is shown (no flicker).
  const [groupChecked, setGroupChecked] = useState(false);
  const navigate = useNavigate();
  const [commentBody, setCommentBody] = useState('');
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  /** Author-optimizer staged field overrides (local preview). */
  const [optPreview, setOptPreview] = useState<{
    title?: string;
    problem?: string;
    solution?: string;
    beneficiaries?: string;
    success_metrics?: string;
    tags?: string[];
    effort?: Effort;
  }>({});

  const category = useMemo(
    () => categories.find((c) => c.id === idea?.category_id) ?? null,
    [categories, idea],
  );

  const userMap = useMemo(() => {
    const m = new Map<string, User>();
    users.forEach((u) => m.set(u.id, u));
    return m;
  }, [users]);

  const nameOf = (uid: string) => {
    if (user?.id === uid) return 'You';
    return userMap.get(uid)?.name ?? 'Unknown user';
  };

  useEffect(() => {
    let cancelled = false;
    // Drop previous idea immediately so tabs (esp. Tracker) don't keep
    // showing another idea's data while the new id loads.
    setIdea(null);
    setError(null);
    setRelated([]);
    setCollabReqs([]);
    setLinkedGroup(null);
    setGroupChecked(false);
    setComments([]);
    setOptPreview({});
    (async () => {
      try {
        const [i, cats, us] = await Promise.all([
          ideasApi.get(id),
          ideasApi.categories().catch(() => [] as Category[]),
          usersApi.list().catch(() => [] as User[]),
        ]);
        if (cancelled) return;
        setIdea(i);
        setCategories(cats);
        setUsers(us);
        collabApi
          .forIdea(id)
          .then((r) => {
            if (!cancelled) setCollabReqs(r);
          })
          .catch(() => {
            if (!cancelled) setCollabReqs([]);
          });
        groupsApi
          .forIdea(id)
          .then((g) => {
            if (!cancelled) {
              setLinkedGroup(g);
              setGroupChecked(true);
            }
          })
          .catch(() => {
            if (!cancelled) {
              setLinkedGroup(null);
              setGroupChecked(true);
            }
          });
        if (i.tags.length || i.category_id) {
          const rel = await ideasApi
            .list({
              category_id: i.category_id || undefined,
              tag: i.tags[0],
              limit: 6,
            })
            .catch(() => ({ items: [] as Idea[], total: 0 }));
          if (!cancelled) {
            setRelated(rel.items.filter((x) => x.id !== i.id).slice(0, 4));
          }
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load idea');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    if ((tab !== 'discussion' && tab !== 'overview') || !id) return;
    ideasApi.listComments(id).then(setComments).catch(() => setComments([]));
  }, [tab, id]);

  const setTab = (t: Tab) => {
    const next = new URLSearchParams(search);
    if (t === 'overview') next.delete('tab');
    else next.set('tab', t);
    setSearch(next);
  };

  const toggleVote = async () => {
    if (!idea) return;
    setBusy(true);
    try {
      const res = await ideasApi.vote(idea.id);
      setIdea({
        ...idea,
        voted: res.active,
        vote_count: idea.vote_count + (res.active ? 1 : -1),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Vote failed');
    } finally {
      setBusy(false);
    }
  };

  const toggleFollow = async () => {
    if (!idea) return;
    setBusy(true);
    try {
      const res = await ideasApi.follow(idea.id);
      setIdea({
        ...idea,
        following: res.active,
        follow_count: idea.follow_count + (res.active ? 1 : -1),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Follow failed');
    } finally {
      setBusy(false);
    }
  };

  const postComment = async (e: FormEvent) => {
    e.preventDefault();
    if (!idea || !commentBody.trim()) return;
    setBusy(true);
    try {
      const c = await ideasApi.addComment(idea.id, commentBody.trim());
      setComments((list) => [...list, c]);
      setCommentBody('');
      setIdea({ ...idea, comment_count: idea.comment_count + 1 });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comment failed');
    } finally {
      setBusy(false);
    }
  };

  const withdraw = async () => {
    if (!idea) return;
    if (
      !(await dialog.confirm({
        title: 'Withdraw this idea?',
        confirmLabel: 'Withdraw',
        danger: true,
      }))
    )
      return;
    setBusy(true);
    try {
      const updated = await ideasApi.withdraw(idea.id, 'Withdrawn by author');
      setIdea(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Withdraw failed');
    } finally {
      setBusy(false);
    }
  };

  const restoreIdea = async () => {
    if (!idea) return;
    setBusy(true);
    try {
      await ideasApi.restore(idea.id);
      navigate(`/submit?draft=${idea.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Restore failed');
      setBusy(false);
    }
  };

  const answerInfo = async (e: FormEvent) => {
    e.preventDefault();
    if (!idea || answer.trim().length < 10) {
      setError('Answer must be at least 10 characters.');
      return;
    }
    setBusy(true);
    try {
      const updated = await ideasApi.answerInfo(idea.id, answer.trim());
      setIdea(updated);
      setAnswer('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send answer');
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

  if (!idea) {
    return <p className="muted">Loading idea…</p>;
  }

  if (idea.is_draft || idea.status === 'draft') {
    return (
      <div className="card" style={{ maxWidth: 640, margin: '40px auto' }}>
        <div className="empty">
          <Icon name="edit" size={36} />
          <h2>This idea is still a draft</h2>
          <p className="muted">
            Finish it and submit it to start the review clock.
          </p>
          <Link className="btn btn--primary" to={`/submit?draft=${idea.id}`}>
            Resume draft
          </Link>
        </div>
      </div>
    );
  }

  const si = stageIndex(idea.status);
  const isAuthor = user?.id === idea.author_id;
  const own = isAuthor || idea.co_author_ids.includes(user?.id ?? '');
  const canSeeAiReview =
    own || ['reviewer', 'admin', 'leadership'].includes(user?.active_role ?? '');
  const live = idea.status !== 'withdrawn';
  const canWithdraw =
    isAuthor &&
    ['submitted', 'under_review', 'needs_info'].includes(idea.status);
  const canWork =
    ['reviewer', 'admin'].includes(user?.active_role ?? '') &&
    ['under_review', 'needs_info', 'submitted'].includes(idea.status);
  const canLaunchBuild =
    idea.status === 'accepted' &&
    (user?.id === idea.owner_id ||
      isAuthor ||
      ['reviewer', 'admin', 'lead', 'leadership'].includes(
        user?.active_role ?? '',
      ));
  const canDecideBuild =
    user?.id === idea.owner_id ||
    isAuthor ||
    ['reviewer', 'admin', 'leadership'].includes(user?.active_role ?? '');
  const ns = nextStep(idea);
  const history = [...idea.status_history].sort(
    (a, b) => new Date(b.at).getTime() - new Date(a.at).getTime(),
  );
  const pendingCollab = collabReqs.filter((r) => r.status === 'pending');
  const canSeePendingCount =
    isAuthor ||
    idea.owner_id === user?.id ||
    idea.co_author_ids.includes(user?.id ?? '') ||
    ['lead', 'admin', 'leadership'].includes(user?.active_role ?? '');
  const teamIds = (() => {
    const ids = [idea.author_id, ...idea.co_author_ids];
    if (idea.owner_id) ids.push(idea.owner_id);
    collabReqs
      .filter((r) => r.status === 'accepted')
      .forEach((r) => ids.push(r.from_user_id));
    return [...new Set(ids)];
  })();
  const teamRole = (uid: string) => {
    if (uid === idea.author_id && uid === idea.owner_id)
      return 'Author and owner';
    if (uid === idea.author_id) return 'Author';
    if (uid === idea.owner_id) return 'Owner';
    if (idea.co_author_ids.includes(uid)) return 'Co-author';
    return 'Collaborator';
  };

  return (
    <div className="stack stack--lg">
      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="card">
        <div className="row" style={{ gap: 6 }}>
          {category ? (
            <span
              className="tag tag--cat"
              style={
                category.color
                  ? ({ ['--cat-color']: category.color } as CSSProperties)
                  : undefined
              }
            >
              <i className="dot" aria-hidden="true" />
              {category.label}
            </span>
          ) : null}
          <StatusPill status={idea.status} />
          {idea.anonymous && isAuthor ? (
            <span className="pill">
              <Icon name="lock" size={12} /> Anonymous (you)
            </span>
          ) : null}
        </div>
        <h1 className="idea-title">
          {optPreview.title ?? idea.title}
        </h1>

        {idea.anonymous && isAuthor ? (
          <div className="notice notice--brand" style={{ marginBottom: 12 }}>
            <Icon name="lock" size={16} />
            <span>
              <strong>You submitted this anonymously.</strong> Your name is
              hidden from everyone, including reviewers.
            </span>
          </div>
        ) : null}
        {idea.merged_into_id ? (
          <div className="notice" style={{ marginBottom: 12 }}>
            <Icon name="merge" size={16} />
            <span>
              This idea was <strong>merged into </strong>
              <Link to={`/ideas/${idea.merged_into_id}`}>another idea</Link>.
            </span>
          </div>
        ) : null}
        {idea.status === 'withdrawn' ? (
          <div className="notice notice--warn" style={{ marginBottom: 12 }}>
            <Icon name="ban" size={16} />
            <span>
              The author withdrew this idea
              {idea.withdraw_reason ? `: “${idea.withdraw_reason}”` : '.'}
            </span>
            {own ? (
              <button type="button" className="btn btn--sm" disabled={busy} onClick={restoreIdea}>
                Restore to draft
              </button>
            ) : null}
          </div>
        ) : null}

        <div className="row" style={{ marginBottom: 'var(--space-4)' }}>
          {own ? (
            <span className="btn" aria-disabled="true" title="You wrote this idea">
              <Icon name="up" size={16} /> Upvote{' '}
              <span className="count">{idea.vote_count}</span>
            </span>
          ) : (
            <button
              type="button"
              className={`btn${idea.voted ? ' btn--primary' : ''}`}
              disabled={busy || !live}
              aria-pressed={idea.voted}
              onClick={toggleVote}
            >
              <Icon name="up" size={16} /> {idea.voted ? 'Upvoted' : 'Upvote'}{' '}
              <span className="count">{idea.vote_count}</span>
            </button>
          )}
          <button
            type="button"
            className="btn"
            disabled={busy || !live}
            aria-pressed={idea.following}
            title={
              idea.following
                ? 'Unfollow to stop updates in your notifications'
                : 'Follow to get updates in your notifications'
            }
            onClick={toggleFollow}
          >
            <Icon name="eye" size={16} />{' '}
            {idea.following ? 'Following' : 'Follow to get updates'}
          </button>
          {canWork ? (
            <Link className="btn btn--primary" to={`/review/${idea.id}`}>
              <Icon name="checkcircle" size={16} /> Open review workspace
            </Link>
          ) : null}
          {canWithdraw ? (
            <button
              type="button"
              className="btn btn--ghost"
              disabled={busy}
              onClick={withdraw}
            >
              <Icon name="ban" size={16} /> Withdraw
            </button>
          ) : null}
        </div>

        <AgentHandoffBar ideaId={idea.id} />

        <AgentBuildPanel
          ideaId={idea.id}
          ideaStatus={idea.status}
          canLaunch={canLaunchBuild}
          canDecide={canDecideBuild}
        />

        <div className="meta-row">
          <span className="person">
            <Avatar
              name={
                idea.anonymous && !isAuthor
                  ? 'Anonymous'
                  : nameOf(idea.author_id)
              }
              avatar={
                idea.anonymous && !isAuthor
                  ? 1
                  : (userMap.get(idea.author_id)?.avatar ?? 1)
              }
              size="sm"
            />
            {idea.anonymous && !isAuthor
              ? 'Anonymous'
              : nameOf(idea.author_id)}
          </span>
          {idea.co_author_ids.length ? (
            <>
              <span className="muted">with</span>
              {idea.co_author_ids.map((cid) => (
                <span key={cid} className="person">
                  <Avatar
                    name={nameOf(cid)}
                    avatar={userMap.get(cid)?.avatar ?? 1}
                    size="sm"
                  />
                  {nameOf(cid)}
                </span>
              ))}
            </>
          ) : null}
          {idea.team_name ? (
            <>
              <span className="muted">Team</span>
              <span>{idea.team_name}</span>
            </>
          ) : null}
          {idea.demo_url ? (
            <>
              <span className="muted">Live project</span>
              <a href={idea.demo_url} target="_blank" rel="noreferrer">
                {idea.demo_url.replace(/^https:\/\//, '')}
              </a>
            </>
          ) : null}
          {idea.github_url ? (
            <>
              <span className="muted">Code</span>
              <a href={idea.github_url} target="_blank" rel="noreferrer">
                {idea.github_url.replace('https://github.com/', 'github.com/')}
              </a>
            </>
          ) : null}
          {idea.owner_id ? (
            <>
              <span className="muted">Owner</span>
              <span className="person">
                <Avatar
                  name={nameOf(idea.owner_id)}
                  avatar={userMap.get(idea.owner_id)?.avatar ?? 1}
                  size="sm"
                />
                {nameOf(idea.owner_id)}
              </span>
            </>
          ) : null}
          <span className="muted">
            Effort:{' '}
            {EFFORT_LABELS[optPreview.effort ?? idea.effort] ??
              (optPreview.effort ?? idea.effort)}
          </span>
          {idea.submitted_at ? (
            <span className="muted">
              Submitted {fmtDate(idea.submitted_at, true)}
            </span>
          ) : null}
          <span className="chip-row">
            {(optPreview.tags ?? idea.tags).map((t) => (
              <Link
                key={t}
                className="tag"
                to={`/explore?tag=${encodeURIComponent(t)}`}
              >
                {t}
              </Link>
            ))}
          </span>
        </div>

        <JourneyStepper
          ariaLabel="Idea lifecycle"
          stages={IDEA_STAGES}
          current={si}
          finished={idea.status === 'implemented'}
          tone={
            ['declined', 'withdrawn'].includes(idea.status)
              ? 'stopped'
              : idea.status === 'parked'
                ? 'paused'
                : 'normal'
          }
          now={
            <>
              <div className="eyebrow eyebrow--plain">Now</div>
              <div>
                {['declined', 'withdrawn'].includes(idea.status)
                  ? `This idea was ${idea.status}. It stops here unless it is reopened.`
                  : ns.text}
              </div>
            </>
          }
        />
      </div>

      <div className="tabs" role="tablist">
        {TABS.map(([tid, label]) => (
          <button
            key={tid}
            type="button"
            role="tab"
            aria-selected={tab === tid}
            onClick={() => setTab(tid)}
          >
            {label}
            {tid === 'discussion' ? (
              <span className="count">{idea.comment_count}</span>
            ) : null}
            {tid === 'decision' && history.length ? (
              <span className="count">{history.length}</span>
            ) : null}
            {tid === 'team' &&
            canSeePendingCount &&
            pendingCollab.length ? (
              <span className="count">{pendingCollab.length}</span>
            ) : null}
          </button>
        ))}
      </div>

      <div className="layout-rail">
        <div className="stack">
          {tab === 'overview' && (
            <>
              {idea.status === 'needs_info' ? (
                <div
                  className="card"
                  style={{ borderColor: 'var(--warning)' }}
                >
                  <div className="eyebrow eyebrow--plain">
                    <Icon name="help" size={14} /> The reviewer asked
                  </div>
                  <blockquote
                    className="quote"
                    style={{ fontSize: 14, margin: '8px 0 12px' }}
                  >
                    {idea.needs_info_question || '—'}
                  </blockquote>
                  {own ? (
                    <form className="stack" onSubmit={answerInfo}>
                      <div className="field">
                        <label htmlFor="ans-text">Your answer</label>
                        <textarea
                          className="textarea"
                          id="ans-text"
                          value={answer}
                          onChange={(e) => setAnswer(e.target.value)}
                          rows={4}
                          placeholder="Answer the question. The review clock restarts when you send this."
                          required
                        />
                      </div>
                      <button
                        type="submit"
                        className="btn btn--primary"
                        disabled={busy}
                      >
                        <Icon name="send" size={16} /> Send answer and resume
                        review
                      </button>
                    </form>
                  ) : (
                    <p className="muted small">
                      The review clock is paused until the author answers.
                    </p>
                  )}
                </div>
              ) : null}
              <div className="card">
                <dl className="dl">
                  <dt>Problem</dt>
                  <dd>{(optPreview.problem ?? idea.problem) || '—'}</dd>
                  <dt>Proposed solution</dt>
                  <dd>{(optPreview.solution ?? idea.solution) || '—'}</dd>
                  <dt>Who benefits</dt>
                  <dd>
                    {(optPreview.beneficiaries ?? idea.beneficiaries) || '—'}
                  </dd>
                  <dt>Rough effort</dt>
                  <dd>
                    {EFFORT_LABELS[optPreview.effort ?? idea.effort] ??
                      (optPreview.effort ?? idea.effort)}
                  </dd>
                  <dt>What success looks like</dt>
                  <dd>
                    {(optPreview.success_metrics ?? idea.success_metrics) ||
                      '—'}
                  </dd>
                </dl>
              </div>
              {canSeeAiReview ? (
                <IdeaAiReview
                  review={idea.ai_review}
                  isDraft={false}
                  audience={own ? 'author' : 'reviewer'}
                />
              ) : null}
            </>
          )}

          {tab === 'discussion' && (
            <div className="card">
              <div className="card__head">
                <h2>Discussion</h2>
                <span className="muted small">
                  {idea.comment_count} comment
                  {idea.comment_count === 1 ? '' : 's'}
                </span>
              </div>
              {comments.length === 0 ? (
                <div className="empty" style={{ padding: 24 }}>
                  <Icon name="message" size={28} />
                  <h3>No comments yet</h3>
                  <p className="muted small">
                    Be the first to add context, a question or an offer to help.
                  </p>
                </div>
              ) : (
                comments.map((c) => (
                  <div key={c.id} className="comment">
                    <Avatar
                      name={nameOf(c.author_id)}
                      avatar={userMap.get(c.author_id)?.avatar ?? 1}
                    />
                    <div className="grow">
                      <div className="row" style={{ gap: 8 }}>
                        <strong>{nameOf(c.author_id)}</strong>
                        {c.kind === 'info_answer' ? (
                          <span className="pill pill--brand">
                            Answer to reviewer
                          </span>
                        ) : null}
                        <span className="muted small">
                          {relTime(c.created_at)}
                        </span>
                      </div>
                      <div className="comment__body">{c.body}</div>
                    </div>
                  </div>
                ))
              )}
              {live ? (
                <form
                  className="stack"
                  onSubmit={postComment}
                  style={{ marginTop: 12 }}
                >
                  <div className="field">
                    <label htmlFor="cmt-body">Add a comment</label>
                    <textarea
                      id="cmt-body"
                      className="textarea"
                      value={commentBody}
                      onChange={(e) => setCommentBody(e.target.value)}
                      rows={3}
                      placeholder="Share context, a concern, a question or an offer to help"
                      required
                    />
                  </div>
                  <div className="row" style={{ marginTop: 12 }}>
                    <button
                      type="submit"
                      className="btn btn--primary"
                      disabled={busy}
                    >
                      <Icon name="send" size={16} /> Post comment
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          )}

          {tab === 'decision' && (
            <div className="card">
              <div className="card__head">
                <h2>Decision history</h2>
              </div>
              {history.length === 0 ? (
                <div className="empty" style={{ padding: 24 }}>
                  <Icon name="refresh" size={28} />
                  <h3>No decision yet</h3>
                  <p className="muted small">
                    Every decision is recorded here with who decided and the
                    written reason.
                  </p>
                </div>
              ) : (
                <div className="stack">
                  {history.map((h) => (
                    <div key={h.id} className="decision">
                      <div className="row row--between">
                        <div className="row" style={{ gap: 8 }}>
                          <StatusPill status={h.to_status} />
                          <span className="muted small">
                            by {h.actor_id ? nameOf(h.actor_id) : 'IdeaKonnekt'} ·{' '}
                            {fmtDate(h.at, true)}
                          </span>
                        </div>
                      </div>
                      {h.reason ? (
                        <blockquote style={{ marginTop: 10 }}>
                          {h.reason}
                        </blockquote>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'team' && <CollabTrackerPanel idea={idea} />}
          {tab === 'delivery' && <DeliveryTab idea={idea} />}
          {tab === 'tracker' && (
            <TrackerTab
              idea={idea}
              onOpenDelivery={() => setTab('delivery')}
            />
          )}

          {tab === 'activity' && (
            <div className="card">
              <div className="card__head">
                <h2>Activity</h2>
              </div>
              {history.length === 0 ? (
                <div className="empty" style={{ padding: 24 }}>
                  <Icon name="clock" size={28} />
                  <h3>No activity yet</h3>
                  <p className="muted small">
                    Status changes and updates will show up here.
                  </p>
                </div>
              ) : (
                <div className="timeline">
                  {history.map((h) => (
                    <div key={h.id} className="timeline__item">
                      <span
                        className={`timeline__dot${
                          ['accepted', 'implemented'].includes(h.to_status)
                            ? ' timeline__dot--good'
                            : ['declined', 'withdrawn'].includes(h.to_status)
                              ? ' timeline__dot--bad'
                              : ''
                        }`}
                      >
                        <Icon
                          name={
                            h.to_status === 'merged'
                              ? 'merge'
                              : h.to_status === 'parked'
                                ? 'pause'
                                : h.to_status === 'declined' ||
                                    h.to_status === 'withdrawn'
                                  ? 'x'
                                  : 'check'
                          }
                          size={14}
                        />
                      </span>
                      <div>
                        <div>
                          Status changed to{' '}
                          <strong>{h.to_status.replace(/_/g, ' ')}</strong>{' '}
                          <span className="muted">
                            by {h.actor_id ? nameOf(h.actor_id) : 'IdeaKonnekt'}
                          </span>
                        </div>
                        {h.reason ? (
                          <div className="muted small" style={{ marginTop: 2 }}>
                            {h.reason}
                          </div>
                        ) : null}
                        <div className="timeline__when">
                          {new Date(h.at).toLocaleString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <aside className="stack">
          {own ? (
            <IdeaOptimizePanel
              idea={idea}
              onApplyPatches={(patches) => {
                setOptPreview((prev) => ({ ...prev, ...patches }));
              }}
            />
          ) : null}
          <EntryDocumentsCard ideaId={idea.id} canEdit={own} />
          <div className="card card--tight">
            <h3 style={{ marginBottom: 8 }}>Related ideas</h3>
            {related.length ? (
              related.map((r) => (
                <div key={r.id} className="listrow">
                  <div className="listrow__main">
                    <Link className="listrow__title" to={`/ideas/${r.id}`}>
                      {r.title}
                    </Link>
                    <div className="muted small">
                      <StatusPill status={r.status} />
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <p className="muted small">No closely related ideas found.</p>
            )}
            <p className="muted small" style={{ marginTop: 8 }}>
              Computed from shared category and tags.
            </p>
          </div>
          <div className="card card--tight">
            <h3 style={{ marginBottom: 8 }}>
              Team <span className="muted">({teamIds.length})</span>
            </h3>
            {teamIds.slice(0, 6).map((uid) => {
              const u = userMap.get(uid);
              const anon = idea.anonymous && uid === idea.author_id && !isAuthor;
              return (
                <div
                  key={uid}
                  className="listrow"
                  style={{ alignItems: 'center' }}
                >
                  <Avatar
                    name={anon ? 'Anonymous' : nameOf(uid)}
                    avatar={anon ? 1 : (u?.avatar ?? 1)}
                  />
                  <div className="listrow__main">
                    <span className="strong">
                      {anon ? 'Anonymous' : nameOf(uid)}
                    </span>
                    <div className="muted small">{teamRole(uid)}</div>
                  </div>
                </div>
              );
            })}
            {teamIds.length > 6 ? (
              <p className="muted small">and {teamIds.length - 6} more</p>
            ) : null}
            <p className="muted small" style={{ marginTop: 8 }}>
              {collabReqs.filter((r) => r.status === 'accepted').length}{' '}
              accepted collaborator
              {collabReqs.filter((r) => r.status === 'accepted').length === 1
                ? ''
                : 's'}
              {canSeePendingCount && pendingCollab.length
                ? ` · ${pendingCollab.length} pending`
                : ''}
              . {idea.follow_count}{' '}
              {idea.follow_count === 1 ? 'person' : 'people'} following.
            </p>
            <div className="row" style={{ gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
              <button
                type="button"
                className="btn btn--sm"
                onClick={() => setTab('team')}
              >
                Team and progress
              </button>
              {!groupChecked ? null : linkedGroup ? (
                <Link
                  className="btn btn--sm btn--ghost"
                  to={`/groups/${linkedGroup.id}`}
                >
                  Open group
                </Link>
              ) : (
                <button
                  type="button"
                  className="btn btn--sm btn--ghost"
                  disabled={busy}
                  onClick={() => {
                    void (async () => {
                      setBusy(true);
                      try {
                        const g = await groupsApi.create({
                          name: idea.title.slice(0, 200),
                          description: 'Linked from idea detail',
                          idea_id: idea.id,
                        });
                        setLinkedGroup(g);
                        navigate(`/groups/${g.id}`);
                      } catch (e) {
                        setError(
                          e instanceof Error
                            ? e.message
                            : 'Could not create group',
                        );
                        setBusy(false);
                      }
                    })();
                  }}
                >
                  Create group
                </button>
              )}
            </div>
          </div>
          <div className="card card--tight">
            <h3 style={{ marginBottom: 8 }}>Engagement</h3>
            <div className="mini-kpis">
              <div>
                <div className="kpi__label">Votes</div>
                <div className="kpi__value kpi__value--sm">
                  {idea.vote_count}
                </div>
              </div>
              <div>
                <div className="kpi__label">Following</div>
                <div className="kpi__value kpi__value--sm">
                  {idea.follow_count}
                </div>
              </div>
              <div>
                <div className="kpi__label">Comments</div>
                <div className="kpi__value kpi__value--sm">
                  {idea.comment_count}
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
