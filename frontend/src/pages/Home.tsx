import { useEffect, useState, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { recognitionApi } from '../api/recognition';
import { InfoTip } from '../components/ui/InfoTip';
import { usersApi } from '../api/users';
import { Avatar, Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { fmtNum } from '../constants/ideathons';
import { STATUS_META } from '../constants/status';
import { useAuth } from '../auth/AuthProvider';
import { CAN_SUBMIT, ROLE_BLURBS, roleLabel } from '../constants/roles';
import { nextStep, relTime } from '../utils/format';
import type { HomeAggregates, Idea } from '../types/idea';
import type { LeaderboardRow } from '../types/recognition';
import type { Role, User } from '../types/auth';

export function HomePage() {
  const { user } = useAuth();
  const [data, setData] = useState<HomeAggregates | null>(null);
  const [mine, setMine] = useState<Idea[]>([]);
  const [queue, setQueue] = useState<Idea[]>([]);
  const [recent, setRecent] = useState<Idea[]>([]);
  const [board, setBoard] = useState<LeaderboardRow[]>([]);
  const [people, setPeople] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const home = await ideasApi.home();
        if (!cancelled) setData(home);
        const [mineRes, recentRes] = await Promise.all([
          user
            ? ideasApi.list({ author_id: user.id, limit: 4 }).catch(() => ({
                items: [] as Idea[],
                total: 0,
              }))
            : Promise.resolve({ items: [] as Idea[], total: 0 }),
          ideasApi.list({ limit: 9 }).catch(() => ({ items: [] as Idea[], total: 0 })),
        ]);
        if (cancelled) return;
        setMine(mineRes.items.filter((i) => i.status !== 'draft'));
        setRecent(recentRes.items.filter((i) => i.status !== 'draft'));
        const [boardRes, peopleRes] = await Promise.all([
          recognitionApi.leaderboard(5).catch(() => [] as LeaderboardRow[]),
          usersApi.list().catch(() => [] as User[]),
        ]);
        if (cancelled) return;
        setBoard(boardRes);
        setPeople(peopleRes);
        if (
          user &&
          (user.active_role === 'reviewer' || user.active_role === 'admin')
        ) {
          const q = await ideasApi
            .list({ status: 'under_review', limit: 4 })
            .catch(() => ({ items: [] as Idea[], total: 0 }));
          if (!cancelled) setQueue(q.items);
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load home');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  const active = (user?.active_role ?? 'contributor') as Role;
  const canSubmit = CAN_SUBMIT.includes(active);

  if (loading) {
    return (
      <div className="empty">
        <p className="muted">Loading home…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }

  const counts = data?.status_counts ?? {};
  const awaiting =
    (counts.submitted ?? 0) +
    (counts.under_review ?? 0) +
    (counts.needs_info ?? 0);
  const acceptedOnly = counts.accepted ?? 0;
  const delivery = counts.prototype ?? 0;
  const implemented = counts.implemented ?? 0;
  const total = data?.total_live ?? 0;

  const tiles: Array<[string, number, string, string, string]> = [
    [
      'Total ideas',
      total,
      'submitted, excluding drafts and withdrawn',
      '/explore',
      '',
    ],
    [
      'Awaiting review',
      awaiting,
      'submitted, in review or waiting on the author',
      '/explore?status=under_review',
      'kpi--accent',
    ],
    [
      'Accepted',
      acceptedOnly,
      'accepted, not yet in prototype',
      '/explore?status=accepted',
      '',
    ],
    [
      'In delivery',
      delivery,
      'in prototype',
      '/explore?status=prototype',
      '',
    ],
    [
      'Implemented',
      implemented,
      'delivered',
      '/explore?status=implemented',
      '',
    ],
  ];

  const attention = data?.needs_attention ?? [];
  const peopleMap = new Map(people.map((p) => [p.id, p]));

  let band: ReactNode;
  if (active === 'reviewer' || active === 'admin') {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>
            {active === 'admin' ? 'Review queue across panels' : 'Your review queue'}
          </h2>
          <Link className="btn btn--sm" to="/review">
            Open queue
          </Link>
        </div>
        {queue.length ? (
          queue.map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link className="listrow__title" to={`/review/${i.id}`}>
                  {i.title}
                </Link>
                <div className="muted small">
                  {i.picked_up_at ? 'in review' : 'awaiting pickup'}
                  {i.due_at ? ` · due ${relTime(i.due_at)}` : ''}
                </div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="checkcircle" size={28} />
            <h3>Queue clear</h3>
            <p className="muted small">No ideas are waiting for a decision.</p>
          </div>
        )}
      </div>
    );
  } else if (active === 'lead') {
    const owned = mine.filter((i) =>
      ['accepted', 'prototype'].includes(i.status),
    );
    band = (
      <div className="card">
        <div className="card__head">
          <h2>My delivery items</h2>
          <Link className="btn btn--sm" to="/pipeline">
            Open pipeline
          </Link>
        </div>
        {owned.length ? (
          owned.map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link
                  className="listrow__title"
                  to={`/ideas/${i.id}?tab=delivery`}
                >
                  {i.title}
                </Link>
                <div className="muted small">{nextStep(i).text}</div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="layers" size={28} />
            <h3>Nothing assigned</h3>
            <p className="muted small">
              Accepted ideas without an owner appear under attention.
            </p>
          </div>
        )}
      </div>
    );
  } else if (active === 'leadership') {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>Where ideas are waiting</h2>
          <Link className="btn btn--sm" to="/pipeline?stuck=1">
            See stuck ideas
          </Link>
        </div>
        <p className="muted small">
          Open Approvals for innovation-hour requests. Use Insights for pipeline
          health.
        </p>
        <div className="row" style={{ marginTop: 12, gap: 8 }}>
          <Link className="btn btn--sm btn--primary" to="/approvals">
            Open approvals
          </Link>
          <Link className="btn btn--sm" to="/insights">
            Insights
          </Link>
          <Link className="btn btn--sm" to="/problems">
            Problem radar
          </Link>
        </div>
      </div>
    );
  } else {
    band = (
      <div className="card">
        <div className="card__head">
          <h2>Your ideas</h2>
          <Link className="btn btn--sm" to="/my">
            All my ideas
          </Link>
        </div>
        {mine.length ? (
          mine.slice(0, 4).map((i) => (
            <div key={i.id} className="listrow">
              <div className="listrow__main">
                <Link className="listrow__title" to={`/ideas/${i.id}`}>
                  {i.title}
                </Link>
                <div className="muted small">{nextStep(i).text}</div>
              </div>
              <StatusPill status={i.status} />
            </div>
          ))
        ) : (
          <div className="empty" style={{ padding: 24 }}>
            <Icon name="plus" size={28} />
            <h3>No ideas yet</h3>
            <p className="muted small">
              Use New idea in the top bar — it takes about five minutes.
            </p>
          </div>
        )}
      </div>
    );
  }

  // Only things the viewer must act on count as "your next move".
  // Ideas another reviewer is already scoring are not the viewer's move.
  const isReviewer = active === "reviewer" || active === "admin";
  const scoringMine = isReviewer ? queue.find((i) => i.reviewer_id === user?.id) : undefined;
  const awaitingPickup = isReviewer ? queue.find((i) => !i.picked_up_at) : undefined;
  const answerMine = mine.find((i) => i.status === "needs_info");
  const action: { idea: Idea; kind: "decide" | "answer" | "pickup" } | null = scoringMine
    ? { idea: scoringMine, kind: "decide" }
    : answerMine
      ? { idea: answerMine, kind: "answer" }
      : awaitingPickup
        ? { idea: awaitingPickup, kind: "pickup" }
        : null;
  const myBoardIdx = board.findIndex((r) => r.user_id === user?.id);
  const myBoardRow = myBoardIdx >= 0 ? board[myBoardIdx] : undefined;
  const movers = board
    .filter((r) => (r.week_points ?? 0) > 0)
    .sort((a, b) => (b.week_points ?? 0) - (a.week_points ?? 0))
    .slice(0, 3);
  const today = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">{today}</div>
          <h1>Home</h1>
          <p>{ROLE_BLURBS[active] ?? roleLabel(active)}</p>
        </div>
      </div>

      {action ? (
        <section className="home-hero" aria-label="Your next move">
          <div className="home-hero__text">
            <div className="eyebrow eyebrow--plain">Your next move</div>
            <Link className="home-hero__title" to={`/ideas/${action.idea.id}`}>
              {action.idea.title}
            </Link>
            <p>
              {action.kind === "decide"
                ? "You are scoring this idea. Record a decision with a written reason."
                : action.kind === "answer"
                  ? "A reviewer asked a question. Answer it to resume the review."
                  : "Nobody has picked this idea up yet. Open it to start scoring."}
            </p>
          </div>
          <div className="home-hero__actions">
            <Link className="btn btn--primary" to={`/ideas/${action.idea.id}`}>
              {action.kind === "decide"
                ? "Record decision"
                : action.kind === "answer"
                  ? "Answer reviewer"
                  : "Open review"}
              <Icon name="arrowRight" size={14} />
            </Link>
          </div>
        </section>
      ) : null}

      <div className="home-strip card" role="list" aria-label="Idea counts">
        {tiles.map(([label, value, sub, href, tone]) => (
          <Link
            key={label}
            role="listitem"
            className={`home-strip__cell ${tone}`}
            to={href}
            title={sub}
          >
            <span className="home-strip__value">{value}</span>
            <span className="home-strip__label">{label}</span>
          </Link>
        ))}
      </div>

      <div className="layout-rail layout-rail--wide" style={{ marginTop: 'var(--space-5)' }}>
        <div className="stack">
          {band}

          <div className="card">
            <div className="card__head">
              <h2>Needs your attention</h2>
              <span className="muted small">
                {attention.length
                  ? `${attention.length} item${attention.length === 1 ? '' : 's'}`
                  : ''}
              </span>
            </div>
            {attention.length === 0 ? (
              <div className="empty" style={{ padding: 24 }}>
                <Icon name="checkcircle" size={28} />
                <h3>You are all caught up</h3>
                <p className="muted small">Nothing needs your action right now.</p>
              </div>
            ) : (
              <div className="stack stack--sm">
                {attention.slice(0, 8).map((item, idx) => {
                  const href =
                    typeof item.href === 'string' ? item.href : '/my';
                  const to = href.startsWith('#')
                    ? href.replace(/^#/, '') || '/'
                    : href;
                  const sev = Math.min(Number(item.priority) || 1, 2);
                  return (
                    <Link
                      key={idx}
                      className={`attn attn--${sev}`}
                      to={to.startsWith('/') ? to : `/${to}`}
                    >
                      <span className="attn__ic">
                        <Icon name="inbox" size={16} />
                      </span>
                      <span className="grow">{String(item.text ?? 'Open item')}</span>
                      <Icon name="chevronR" size={16} />
                    </Link>
                  );
                })}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Recent activity</h2>
            </div>
            {recent.length === 0 ? (
              <p className="muted small">No recent ideas yet.</p>
            ) : (
              <ul className="feed">
                {recent.map((i) => (
                  <li key={i.id}>
                    <span className="grow">
                      <Link to={`/ideas/${i.id}`}>{i.title}</Link>{' '}
                      <span className="muted">
                        · {STATUS_META[i.status]?.label ?? i.status}
                      </span>
                    </span>
                    <span className="when muted small">
                      {relTime(i.updated_at || i.submitted_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="stack">
          <div className="card home-race">
            <div className="card__head">
              <h2>
                Contribution board{" "}
                <InfoTip label="How the board works">
                  Points come from outcomes, collaboration and verified impact.
                  Upvotes and idea counts earn nothing. "Moving this week" counts
                  points from the last seven days.
                </InfoTip>
              </h2>
              <Link className="lbh__more" to="/recognition?tab=leaderboard">
                Full board
              </Link>
            </div>
            <ol className="home-race__top">
              {board.slice(0, 3).map((r, n) => {
                const u = peopleMap.get(r.user_id);
                const me = r.user_id === user?.id;
                return (
                  <li key={r.user_id} className={`home-race__seat home-race__seat--${n + 1}${me ? " is-me" : ""}`}>
                    <span className="home-race__place">{n + 1}</span>
                    <span className="home-race__avatar">
                      <Avatar name={u?.name ?? r.user_id} avatar={u?.avatar ?? 1} size="md" />
                    </span>
                    <span className="home-race__who">
                      <span className="home-race__name">
                        {u?.name ?? `${r.user_id.slice(0, 8)}…`}
                        {me ? " (you)" : ""}
                      </span>
                      <span className="home-race__level lvl" data-level={r.level_id}>{r.level_name}</span>
                    </span>
                    <span className="home-race__score">
                      <span className="home-race__pts">{fmtNum(r.points)}</span>
                      <span className="home-race__unit">points</span>
                    </span>
                  </li>
                );
              })}
            </ol>
            <div className="home-race__week">
              <div className="eyebrow eyebrow--plain">Moving this week</div>
              {movers.length ? (
                <ul>
                  {movers.map((r) => (
                    <li key={r.user_id}>
                      <span>{peopleMap.get(r.user_id)?.name ?? "A teammate"}</span>
                      <span className="home-race__gain">+{fmtNum(r.week_points ?? 0)}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted small">
                  Nobody has moved yet this week. One idea moving forward starts it.
                </p>
              )}
            </div>
            <div className="home-race__foot">
              <span className="muted small">
                {myBoardRow
                  ? `You are #${myBoardIdx + 1} with ${fmtNum(myBoardRow.points)} points.`
                  : "Your first point comes from moving one idea forward."}
              </span>
              <Link className="btn btn--sm btn--primary" to="/recognition?tab=standing">
                See how to earn
              </Link>
            </div>
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Quick links</h2>
            </div>
            <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
              <Link className="btn btn--sm" to="/pipeline">
                Pipeline board
              </Link>
              <Link className="btn btn--sm" to="/explore">
                Explore
              </Link>
              {canSubmit ? (
                <Link className="btn btn--sm" to="/my">
                  My ideas
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
