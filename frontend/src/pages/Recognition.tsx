/** Recognition — mirrors idea-hub.html `viewRecognition` tabs. */

import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { recognitionApi } from '../api/recognition';
import { usersApi, type Team } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Avatar, Icon } from '../components/Icons';
import { AgentBlock } from '../components/ui/AgentBlock';
import { DimBar, DimLegend } from '../components/ui/DimBar';
import { EmptyState } from '../components/ui/EmptyState';
import { Kpi } from '../components/ui/Kpi';
import { Pill } from '../components/ui/Pill';
import { TabsNav } from '../components/ui/TabsNav';
import {
  PERIODS,
  fmtNum,
  quarterKey,
  quarterLabel,
} from '../constants/ideathons';
import { ORG_ROLES } from '../constants/ideathons';
import type { User } from '../types/auth';
import type {
  Award,
  LeaderboardRow,
  RecognitionRules,
} from '../types/recognition';

const REC_TABS = ['leaderboard', 'teams', 'impact', 'awards', 'how'] as const;
type RecTab = (typeof REC_TABS)[number];

function AwardCard({
  a,
  people,
}: {
  a: Award;
  people: Map<string, User>;
}) {
  const names = a.user_ids
    .map((id) => people.get(id)?.name)
    .filter(Boolean) as string[];
  return (
    <div className="award-card">
      <span className="winner-ic">
        <Icon name="award" size={18} />
      </span>
      <div>
        <div
          className="eyebrow eyebrow--plain"
          style={{ color: 'var(--gold-ink)' }}
        >
          {a.kind === 'ioq'
            ? `Idea of the Quarter · ${quarterLabel(a.period)}`
            : `Annual Innovation Award · ${a.period}`}
        </div>
        {a.idea_id ? (
          <h3>
            <Link to={`/ideas/${a.idea_id}`}>Idea {a.idea_id.slice(0, 8)}…</Link>
          </h3>
        ) : (
          <h3>{names.join(', ') || 'Award'}</h3>
        )}
        {names.length && a.idea_id ? (
          <div className="small">
            {names.map((n, i) => (
              <span key={n}>
                {i ? ', ' : ''}
                {n}
              </span>
            ))}
          </div>
        ) : null}
        <p className="small" style={{ marginTop: 6 }}>
          {a.reason}
        </p>
        <div className="muted small" style={{ marginTop: 4 }}>
          Confirmed {new Date(a.created_at).toLocaleDateString()} · {a.points}{' '}
          points
          {a.kind === 'ioq' ? ' shared between the authors' : ''}
        </div>
      </div>
    </div>
  );
}

function PeriodChips({
  tab,
  period,
}: {
  tab: string;
  period: string;
}) {
  return (
    <div className="chip-row" role="group" aria-label="Period">
      {Object.entries(PERIODS).map(([k, label]) => (
        <Link
          key={k}
          className="chip-link"
          to={`/recognition?tab=${tab}&period=${k}`}
          aria-current={k === period ? 'true' : undefined}
        >
          {label}
        </Link>
      ))}
    </div>
  );
}

export function RecognitionPage() {
  const { user } = useAuth();
  const [params] = useSearchParams();
  const tabParam = params.get('tab');
  const tab: RecTab = REC_TABS.includes(tabParam as RecTab)
    ? (tabParam as RecTab)
    : 'leaderboard';
  const period = PERIODS[params.get('period') ?? '']
    ? (params.get('period') as string)
    : 'quarter';

  const [rules, setRules] = useState<RecognitionRules | null>(null);
  const [board, setBoard] = useState<LeaderboardRow[]>([]);
  const [awards, setAwards] = useState<Award[]>([]);
  const [people, setPeople] = useState<User[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [ioqIdea, setIoqIdea] = useState('');
  const [ioqReason, setIoqReason] = useState('');
  const [annualUser, setAnnualUser] = useState('');
  const [annualReason, setAnnualReason] = useState('');

  const isLeadership = user?.active_role === 'leadership';
  const isOrg =
    !!user && ORG_ROLES.includes(user.active_role as (typeof ORG_ROLES)[number]);

  const reload = () =>
    Promise.all([
      recognitionApi.rules(),
      recognitionApi.leaderboard(50),
      recognitionApi.awards(),
      usersApi.list().catch(() => [] as User[]),
      usersApi.teams().catch(() => [] as Team[]),
    ]).then(([r, b, a, u, t]) => {
      setRules(r);
      setBoard(b);
      setAwards(a);
      setPeople(u);
      setTeams(t);
    });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    reload()
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const peopleMap = useMemo(
    () => new Map(people.map((p) => [p.id, p])),
    [people],
  );
  const teamMap = useMemo(
    () => new Map(teams.map((t) => [t.id, t])),
    [teams],
  );

  const myRow = board.find((r) => r.user_id === user?.id);
  const myPts = myRow?.points ?? 0;
  const myLevel = myRow?.level_name ?? rules?.levels[0]?.name ?? '—';
  const nextLevel = useMemo(() => {
    if (!rules) return null;
    const sorted = [...rules.levels].sort((a, b) => a.min - b.min);
    const next = sorted.find((l) => l.min > myPts);
    return next ? { name: next.name, toNext: next.min - myPts } : null;
  }, [rules, myPts]);

  const teamBoard = useMemo(() => {
    const agg = new Map<
      string,
      { pts: number; dims: Record<string, number>; members: number; active: number }
    >();
    board.forEach((row) => {
      const u = peopleMap.get(row.user_id);
      const tid = u?.team_id;
      if (!tid) return;
      const cur = agg.get(tid) ?? {
        pts: 0,
        dims: { quality: 0, collab: 0, delivery: 0, impact: 0 },
        members: 0,
        active: 0,
      };
      cur.pts += row.points;
      cur.active += 1;
      Object.entries(row.dims ?? {}).forEach(([k, v]) => {
        cur.dims[k] = (cur.dims[k] ?? 0) + v;
      });
      agg.set(tid, cur);
    });
    teams.forEach((t) => {
      const cur = agg.get(t.id) ?? {
        pts: 0,
        dims: { quality: 0, collab: 0, delivery: 0, impact: 0 },
        members: 0,
        active: 0,
      };
      cur.members = people.filter((p) => p.team_id === t.id).length;
      agg.set(t.id, cur);
    });
    return [...agg.entries()]
      .map(([id, v]) => ({
        team: teamMap.get(id),
        id,
        ...v,
        per: v.members ? v.pts / v.members : 0,
      }))
      .filter((r) => r.team)
      .sort((a, b) => b.pts - a.pts);
  }, [board, people, peopleMap, teamMap, teams]);

  const qk = quarterKey();
  const yr = String(new Date().getFullYear());
  const curIoq = awards.find((a) => a.kind === 'ioq' && a.period === qk);
  const curAnnual = awards.find((a) => a.kind === 'annual' && a.period === yr);
  const past = awards.filter((a) => a !== curIoq && a !== curAnnual);

  async function confirmIoq() {
    if (!ioqIdea.trim() || ioqReason.trim().length < 20) {
      setError('Idea id and a reason of at least 20 characters are required.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await recognitionApi.confirmIoq(qk, ioqIdea.trim(), ioqReason.trim());
      setIoqIdea('');
      setIoqReason('');
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Confirm failed');
    } finally {
      setBusy(false);
    }
  }

  async function confirmAnnual() {
    if (!annualUser.trim() || annualReason.trim().length < 20) {
      setError('User id and a reason of at least 20 characters are required.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await recognitionApi.confirmAnnual(
        yr,
        annualUser.trim(),
        annualReason.trim(),
      );
      setAnnualUser('');
      setAnnualReason('');
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Confirm failed');
    } finally {
      setBusy(false);
    }
  }

  if (error && !rules) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }
  if (loading || !rules) {
    return <p className="muted">Loading recognition…</p>;
  }

  let body: React.ReactNode = null;

  if (tab === 'leaderboard') {
    const latest = awards.find((a) => a.kind === 'ioq');
    body = (
      <div className="stack">
        {latest ? <AwardCard a={latest} people={peopleMap} /> : null}
        <div className="card">
          <div className="card__head">
            <h2>Individual leaderboard</h2>
            <PeriodChips tab="leaderboard" period={period} />
          </div>
          <div className="notice notice--brand" style={{ marginBottom: 12 }}>
            <Icon name="info" size={16} />
            <span>
              <strong>Ranked by points, never by number of ideas.</strong>{' '}
              Points come from outcomes, collaboration and verified impact.
              Upvotes earn none. Escrowed anonymous points are excluded.
            </span>
          </div>
          <DimLegend />
          <div className="lb-head">
            <span>#</span>
            <span>Person</span>
            <span className="bd-wrap">Where the points came from</span>
            <span style={{ textAlign: 'right' }}>Points</span>
          </div>
          {board.length ? (
            board.slice(0, 25).map((r, n) => {
              const u = peopleMap.get(r.user_id);
              const team = u?.team_id ? teamMap.get(u.team_id) : null;
              return (
                <div
                  className={`lb-row ${r.user_id === user?.id ? 'lb-row--me' : ''}`}
                  key={r.user_id}
                >
                  <span className={`lb-rank ${n < 3 ? 'lb-rank--top' : ''}`}>
                    {n + 1}
                  </span>
                  <div className="lb-who">
                    <Avatar
                      name={u?.name ?? r.user_id}
                      avatar={u?.avatar ?? 1}
                    />
                    <div>
                      <Link className="strong" to={`/people/${r.user_id}`}>
                        {u?.name ?? `${r.user_id.slice(0, 8)}…`}
                      </Link>
                      {r.user_id === user?.id ? (
                        <span className="muted small"> (you)</span>
                      ) : null}
                      <div className="muted small">
                        {team?.name ?? '—'} · {r.level_name}
                      </div>
                    </div>
                  </div>
                  <div className="bd-wrap">
                    <DimBar dims={r.dims} />
                  </div>
                  <span className="pts" style={{ textAlign: 'right', fontSize: 15 }}>
                    {fmtNum(r.points)}
                  </span>
                </div>
              );
            })
          ) : (
            <EmptyState
              icon="award"
              title="No points in this period yet"
              body="Points appear when ideas are accepted, prototyped, implemented or verified."
            />
          )}
          <p className="muted small" style={{ marginTop: 12 }}>
            Period chips are shown for parity with the prototype; the API
            currently returns the all-time public leaderboard.
          </p>
        </div>
      </div>
    );
  } else if (tab === 'teams') {
    body = (
      <div className="card">
        <div className="card__head">
          <h2>Team leaderboard</h2>
          <PeriodChips tab="teams" period={period} />
        </div>
        <p className="muted small" style={{ marginBottom: 8 }}>
          Team points are the sum of members’ points. Points per member is shown
          so larger teams do not win by size alone.
        </p>
        <DimLegend />
        <div className="lb-head">
          <span>#</span>
          <span>Team</span>
          <span className="bd-wrap">Where the points came from</span>
          <span style={{ textAlign: 'right' }}>Points</span>
        </div>
        {teamBoard.length ? (
          teamBoard.map((r, n) => (
            <div
              className={`lb-row ${r.id === user?.team_id ? 'lb-row--me' : ''}`}
              key={r.id}
            >
              <span className={`lb-rank ${n < 3 ? 'lb-rank--top' : ''}`}>
                {n + 1}
              </span>
              <div className="lb-who">
                <div>
                  <span className="strong">{r.team?.name}</span>
                  <div className="muted small">
                    {r.active} active of {r.members} · {fmtNum(Math.round(r.per))}{' '}
                    per member
                  </div>
                </div>
              </div>
              <div className="bd-wrap">
                <DimBar dims={r.dims} />
              </div>
              <span className="pts" style={{ textAlign: 'right', fontSize: 15 }}>
                {fmtNum(r.pts)}
              </span>
            </div>
          ))
        ) : (
          <EmptyState
            icon="users"
            title="No team points yet"
            body="Points appear on the leaderboard as ideas reach outcomes."
          />
        )}
      </div>
    );
  } else if (tab === 'impact') {
    body = (
      <div className="stack">
        <div className="notice">
          <Icon name="shield" size={16} />
          <span>
            Only <strong>verified</strong> impact counts here: a second person
            checked the baseline and evidence. Figures are per month and weighted
            by contribution share. Anonymous ideas are left out.
          </span>
        </div>
        <div className="grid grid-3 kpi-row">
          <Kpi
            label="Verified hours saved"
            value="—"
            sub="per month"
            tone="gold"
          />
          <Kpi
            label="Verified cost avoided"
            value="—"
            sub="per month"
            tone="gold"
          />
          <Kpi
            label="Verified entries"
            value="—"
            sub="awaiting board API"
            tone="success"
          />
        </div>
        <div className="card">
          <EmptyState
            icon="shield"
            title="Impact board not wired yet"
            body="Verified impact aggregates will appear here once the recognition impact endpoint is available. Individual impact is on each person’s profile."
          />
        </div>
      </div>
    );
  } else if (tab === 'awards') {
    body = (
      <div className="stack">
        <section>
          <div className="card__head" style={{ marginBottom: 'var(--space-3)' }}>
            <h2>Idea of the Quarter</h2>
            <span className="muted small">{quarterLabel(qk)}</span>
          </div>
          {curIoq ? (
            <AwardCard a={curIoq} people={peopleMap} />
          ) : (
            <AgentBlock
              agent="Recognition"
              kind="Computed"
              how="An idea is nominated when it reached Accepted, Prototype or Implemented during the quarter. Leadership confirms; the agent never confirms an award."
            >
              <p>
                <strong>{quarterLabel(qk)} nominations.</strong> Candidate
                scoring is computed by the Recognition agent in the prototype.
                This build confirms from an idea id once leadership is ready.
              </p>
              {isLeadership ? (
                <div className="stack stack--sm" style={{ marginTop: 12 }}>
                  <div className="field">
                    <label htmlFor="ioq-idea">Idea id</label>
                    <input
                      id="ioq-idea"
                      className="input"
                      value={ioqIdea}
                      onChange={(e) => setIoqIdea(e.target.value)}
                      placeholder="UUID of the idea"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="ioq-reason">Why this idea</label>
                    <textarea
                      id="ioq-reason"
                      className="textarea"
                      rows={3}
                      value={ioqReason}
                      onChange={(e) => setIoqReason(e.target.value)}
                      placeholder="Recorded with the award (min 20 characters)."
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn--sm btn--primary"
                    disabled={busy}
                    onClick={() => void confirmIoq()}
                  >
                    <Icon name="award" size={14} /> Confirm as Idea of the
                    Quarter
                  </button>
                </div>
              ) : (
                <p className="muted small">
                  Leadership confirms the Idea of the Quarter.
                </p>
              )}
            </AgentBlock>
          )}
        </section>

        <section>
          <div className="card__head" style={{ marginBottom: 'var(--space-3)' }}>
            <h2>Annual Innovation Award</h2>
            <span className="muted small">{yr}</span>
          </div>
          {curAnnual ? (
            <AwardCard a={curAnnual} people={peopleMap} />
          ) : (
            <AgentBlock
              agent="Recognition"
              kind="Computed"
              how="People are ranked by points earned this calendar year from the public ledger. Leadership chooses."
            >
              <p>
                <strong>{yr} shortlist.</strong> Top people by points this year
                appear on the leaderboard tab.
              </p>
              {isLeadership ? (
                <div className="stack stack--sm" style={{ marginTop: 12 }}>
                  <div className="field">
                    <label htmlFor="ann-user">Person</label>
                    <select
                      id="ann-user"
                      className="select"
                      value={annualUser}
                      onChange={(e) => setAnnualUser(e.target.value)}
                    >
                      <option value="">Choose…</option>
                      {board.slice(0, 10).map((r) => (
                        <option key={r.user_id} value={r.user_id}>
                          {peopleMap.get(r.user_id)?.name ?? r.user_id} (
                          {r.points} pts)
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="ann-reason">Why this person</label>
                    <textarea
                      id="ann-reason"
                      className="textarea"
                      rows={3}
                      value={annualReason}
                      onChange={(e) => setAnnualReason(e.target.value)}
                    />
                  </div>
                  <button
                    type="button"
                    className="btn btn--sm btn--primary"
                    disabled={busy}
                    onClick={() => void confirmAnnual()}
                  >
                    <Icon name="award" size={14} /> Confirm Annual Innovation
                    Award
                  </button>
                </div>
              ) : (
                <p className="muted small">
                  Leadership confirms the Annual Innovation Award.
                </p>
              )}
            </AgentBlock>
          )}
        </section>

        <section>
          <div className="card__head" style={{ marginBottom: 'var(--space-3)' }}>
            <h2>Past awards</h2>
          </div>
          {past.length ? (
            <div className="stack stack--sm">
              {past.map((a) => (
                <AwardCard key={a.id} a={a} people={peopleMap} />
              ))}
            </div>
          ) : (
            <div className="card">
              <EmptyState icon="award" title="No past awards yet" />
            </div>
          )}
        </section>

        {isOrg ? (
          <section>
            <div
              className="card__head"
              style={{ marginBottom: 'var(--space-3)' }}
            >
              <h2>Integrity checks</h2>
              <span className="muted small">Leadership and administrators</span>
            </div>
            <AgentBlock
              agent="Recognition"
              kind="Computed"
              how="A pair is flagged when each person upvoted the other’s ideas enough times. Informational only — no points change."
            >
              <p className="muted small">
                Reciprocal-upvote review is not exposed by the API yet. No pairs
                to show.
              </p>
            </AgentBlock>
          </section>
        ) : null}
      </div>
    );
  } else {
    // how
    const myBadges = rules.badges;
    body = (
      <div className="stack">
        <div className="notice notice--brand">
          <Icon name="award" size={16} />
          <span>
            <strong>Votes do not earn points.</strong> Points follow outcomes,
            collaboration and verified impact. Every ledger row cites the rule
            below that produced it.
          </span>
        </div>
        <div className="card">
          <div className="card__head">
            <h2>Point rules</h2>
            <span className="muted small">
              Values are proposals held in platform configuration
            </span>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Points</th>
                  <th>Counts as</th>
                  <th>When</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(rules.rules).map(([k, r]) => (
                  <tr key={k} id={`rule-${k}`}>
                    <td>
                      <strong>{String(r.label)}</strong>
                      <div className="muted small mono">{k}</div>
                    </td>
                    <td className="pts">
                      {r.max_points ?? r.maxPoints
                        ? `${String(r.points)} to ${String(r.max_points ?? r.maxPoints)}`
                        : String(r.points)}
                    </td>
                    <td>{rules.dims[String(r.dim)] ?? String(r.dim)}</td>
                    <td className="small">{String(r.when)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="grid grid-2">
          <div className="card">
            <div className="card__head">
              <h2>Levels</h2>
            </div>
            {rules.levels.map((l) => (
              <div className="listrow" key={l.id}>
                <div className="listrow__main">
                  <strong>{l.name}</strong>
                </div>
                <span className="pts">{fmtNum(l.min)}+ points</span>
              </div>
            ))}
            <p className="muted small" style={{ marginTop: 8 }}>
              Levels use all-time points from the public ledger.
            </p>
          </div>
          <div className="card">
            <div className="card__head">
              <h2>Anti-gaming rules</h2>
            </div>
            <ul
              className="bullets"
              style={{
                listStyle: 'disc',
                paddingLeft: 20,
                display: 'flex',
                flexDirection: 'column',
                gap: 8,
              }}
            >
              <li>No self-voting, and no marking your own comment helpful.</li>
              <li>
                Submission points are capped and need a complete template.
              </li>
              <li>Duplicates earn nothing; joining or merging earns points.</li>
              <li>
                Most points vest at outcome events, so withdrawn ideas do not
                inflate totals.
              </li>
              <li>
                Verified-impact bonus needs a baseline, evidence and a second
                person.
              </li>
              <li>
                Points for anonymous ideas wait in escrow until the author
                reveals them.
              </li>
              <li>Ledger rows are never edited or deleted.</li>
            </ul>
          </div>
        </div>
        <div className="card">
          <div className="card__head">
            <h2>Badge catalogue</h2>
            <span className="muted small">
              Your progress{user ? `, ${user.name}` : ''}
            </span>
          </div>
          <div className="grid grid-2">
            {myBadges.map((b) => (
              <div className="badge-card badge-card--locked" key={b.id}>
                <span className="badge-ic">
                  <Icon name={b.icon || 'lock'} size={18} />
                </span>
                <div>
                  <div className="strong">
                    {b.name} <Pill>Catalog</Pill>
                  </div>
                  <div className="muted small" style={{ marginTop: 2 }}>
                    {b.rule}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Rewards</div>
          <h1>Recognition</h1>
          <p>
            Points for quality, collaboration and real business impact. Never
            for the number of ideas.
          </p>
        </div>
        {user ? (
          <Link
            className="award-card"
            style={{ textDecoration: 'none', color: 'inherit' }}
            to={`/people/${user.id}?tab=ledger`}
          >
            <span className="winner-ic">
              <Icon name="award" size={18} />
            </span>
            <div>
              <div className="muted small">Your points</div>
              <div className="pts" style={{ fontSize: 20 }}>
                {fmtNum(myPts)}
              </div>
              <div className="small">
                {myLevel}
                {nextLevel
                  ? ` · ${nextLevel.toNext} to ${nextLevel.name}`
                  : ' · top level'}
              </div>
            </div>
          </Link>
        ) : null}
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <TabsNav
        tabs={[
          {
            id: 'leaderboard',
            label: 'Leaderboard',
            href: '/recognition?tab=leaderboard',
          },
          { id: 'teams', label: 'Teams', href: '/recognition?tab=teams' },
          { id: 'impact', label: 'Impact', href: '/recognition?tab=impact' },
          { id: 'awards', label: 'Awards', href: '/recognition?tab=awards' },
          {
            id: 'how',
            label: 'How points work',
            href: '/recognition?tab=how',
          },
        ]}
        active={tab}
      />
      {body}
    </div>
  );
}

export default RecognitionPage;
