/** Ideathon detail — mirrors idea-hub.html `viewIdeathon` + phase tabs. */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import { ideathonsApi } from '../api/ideathons';
import { ideasApi } from '../api/ideas';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { IdeaCard } from '../components/IdeaCard';
import { Avatar, Icon } from '../components/Icons';
import { AgentBlock } from '../components/ui/AgentBlock';
import { EmptyState } from '../components/ui/EmptyState';
import { JourneyStepper, type JourneyStage } from '../components/ui/JourneyStepper';
import { Pill } from '../components/ui/Pill';
import { TabsNav } from '../components/ui/TabsNav';
import { AgentRunsPanel } from '../components/ideathon/AgentRunsPanel';
import { CAN_SUBMIT } from '../constants/roles';
import { STATUS_META } from '../constants/status';
import {
  AUDIENCE_WEIGHT,
  IT_NEXT,
  ITH_PHASES,
  ORG_ROLES,
  PANEL_SCORE_ROLES,
  PANEL_WEIGHT,
  PITCH_SECONDS,
  fmtClock,
  fmtDate,
  ithPhaseIdx,
  ithStatus,
} from '../constants/ideathons';
import type { Idea } from '../types/idea';
import type {
  Handoff,
  IdeathonDetail,
  TallyRow,
} from '../types/ideathon';
import type { User } from '../types/auth';
import { useDialog } from '../components/DialogProvider';

const TABS = ['submissions', 'shortlist', 'pitch', 'results', 'handoff'] as const;
type TabId = (typeof TABS)[number];

function shortId(id: string): string {
  return id.slice(0, 8);
}

function ideaTitle(map: Map<string, Idea>, id: string): string {
  return map.get(id)?.title ?? `${shortId(id)}…`;
}

function StatusPillFor({ it }: { it: IdeathonDetail }) {
  const st = ithStatus(it.start_at, it.end_at, it.completed_at);
  if (st === 'past') return <Pill variant="success" icon="check">Complete</Pill>;
  if (st === 'upcoming')
    return (
      <Pill variant="info" icon="calendar">
        Opens {fmtDate(it.start_at)}
      </Pill>
    );
  return (
    <Pill variant="brand">
      {ITH_PHASES[ithPhaseIdx(it.phase)]?.label ?? it.phase}
    </Pill>
  );
}

/** Gates mirror IdeathonService.advance(): the checks the backend enforces before each move. */
const IDEATHON_GATES: Record<string, { gate: string; owner: string }> = {
  open: {
    gate: 'At least 2 entries are in. The organiser moves it to Shortlist.',
    owner: 'Organiser',
  },
  shortlist: {
    gate: 'The agent proposes a shortlist. The organiser approves at least 2 ideas, then moves to Pitch day.',
    owner: 'Organiser',
  },
  pitch: {
    gate: 'Close voting first. Then the organiser moves to Results.',
    owner: 'Organiser',
  },
  results: {
    gate: 'Confirm at least one winner. Then the organiser moves to Handoff.',
    owner: 'Organiser',
  },
  handoff: {
    gate: 'Mark the ideathon complete once winners are handed off.',
    owner: 'Organiser',
  },
};

function IdeathonStepper({ it }: { it: IdeathonDetail }) {
  const idx = ithPhaseIdx(it.phase);
  const stages: JourneyStage[] = ITH_PHASES.map((ph) => ({
    label: ph.label,
    gate: IDEATHON_GATES[ph.id]?.gate ?? ph.blurb,
    owner: IDEATHON_GATES[ph.id]?.owner ?? 'Organiser',
  }));
  return (
    <JourneyStepper
      ariaLabel="Ideathon phase"
      stages={stages}
      current={idx}
      finished={!!it.completed_at}
      when={(n) => {
        const log = it.phase_log.find((x) => x.phase === ITH_PHASES[n]?.id);
        return log?.at ? fmtDate(log.at) : undefined;
      }}
      now={
        <>
          <div className="eyebrow eyebrow--plain">Now</div>
          <div>
            {it.completed_at
              ? 'This ideathon is complete.'
              : `${ITH_PHASES[idx]?.blurb ?? ''}. ${IDEATHON_GATES[it.phase]?.gate ?? ''}`}
          </div>
        </>
      }
    />
  );
}

function LockedNote({ text }: { text: string }) {
  return (
    <div className="card">
      <EmptyState icon="lock" title="Not yet" body={text} />
    </div>
  );
}

function TallyBlock({
  rows,
  ideas,
  winners,
  live,
  votingClosedAt,
  org,
  onClose,
  busy,
}: {
  rows: TallyRow[];
  ideas: Map<string, Idea>;
  winners: string[];
  live: boolean;
  votingClosedAt?: string | null;
  org: boolean;
  onClose: () => void;
  busy: boolean;
}) {
  return (
    <div className="card">
      <div className="card__head">
        <h2>{live ? 'Live tally' : 'Final tally'}</h2>
        <div className="row">
          {votingClosedAt ? (
            <Pill variant="warning" icon="lock">
              Voting closed {fmtDate(votingClosedAt)}
            </Pill>
          ) : live ? (
            <Pill variant="success">Voting open</Pill>
          ) : null}
          {org ? (
            <button
              type="button"
              className="btn btn--sm btn--primary"
              disabled={busy}
              onClick={onClose}
            >
              Close voting
            </button>
          ) : null}
        </div>
      </div>
      <p className="muted small">
        Combined score (0 to 100) = {PANEL_WEIGHT}% panel + {AUDIENCE_WEIGHT}%
        audience. Panel: mean of reviewer scores (1–10). Audience: votes as a
        share of the leading entry.
      </p>
      {rows.map((r, n) => {
        const win = winners.includes(r.idea_id);
        return (
          <div className="tally" key={r.idea_id}>
            <div style={{ minWidth: 0 }}>
              <div className="row" style={{ gap: 6 }}>
                <span className="pts" style={{ color: 'var(--text-3)' }}>
                  #{n + 1}
                </span>
                {win ? (
                  <Pill variant="gold" icon="trophy">
                    Winner
                  </Pill>
                ) : null}
              </div>
              <Link className="listrow__title" to={`/ideas/${r.idea_id}`}>
                {ideaTitle(ideas, r.idea_id)}
              </Link>
            </div>
            <div className="tally__bars">
              <div className="tally__bar">
                <span>Panel</span>
                <div className="meter">
                  <i style={{ width: `${r.panel_pct}%` }} />
                </div>
                <span className="mono">
                  {r.panel_n ? r.panel_avg.toFixed(1) : '–'}
                </span>
              </div>
              <div className="tally__bar tally__bar--a">
                <span>Audience</span>
                <div className="meter">
                  <i style={{ width: `${r.aud_pct}%` }} />
                </div>
                <span className="mono">{r.audience_votes}</span>
              </div>
              <div className="tally__bar">
                <span className="strong">Combined</span>
                <div className="meter">
                  <i style={{ width: `${r.combined}%` }} />
                </div>
                <span className="mono strong">{r.combined.toFixed(0)}</span>
              </div>
              <div className="muted small">
                {r.panel_n} panel · {r.audience_votes} audience
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function usePitchTimers(ids: string[]) {
  const [left, setLeft] = useState<Record<string, number>>({});
  const state = useRef<
    Record<string, { base: number; running: boolean; t0: number }>
  >({});

  useEffect(() => {
    ids.forEach((id) => {
      if (!state.current[id])
        state.current[id] = { base: PITCH_SECONDS, running: false, t0: 0 };
    });
    setLeft((prev) => {
      const next = { ...prev };
      ids.forEach((id) => {
        if (next[id] == null) next[id] = PITCH_SECONDS;
      });
      return next;
    });
  }, [ids]);

  useEffect(() => {
    const iv = window.setInterval(() => {
      let any = false;
      const next: Record<string, number> = {};
      Object.keys(state.current).forEach((id) => {
        const x = state.current[id];
        const sec = !x.running
          ? x.base
          : Math.max(0, x.base - (Date.now() - x.t0) / 1000);
        next[id] = sec;
        if (x.running) {
          any = true;
          if (sec <= 0) {
            x.running = false;
            x.base = 0;
          }
        }
      });
      if (any) setLeft((p) => ({ ...p, ...next }));
    }, 250);
    return () => clearInterval(iv);
  }, []);

  const start = (id: string) => {
    const x = state.current[id] ?? {
      base: PITCH_SECONDS,
      running: false,
      t0: 0,
    };
    let b = x.running
      ? Math.max(0, x.base - (Date.now() - x.t0) / 1000)
      : x.base;
    if (b <= 0) b = PITCH_SECONDS;
    if (x.running) return;
    state.current[id] = { base: b, running: true, t0: Date.now() };
    setLeft((p) => ({ ...p, [id]: b }));
  };
  const pause = (id: string) => {
    const x = state.current[id];
    if (!x?.running) return;
    const b = Math.max(0, x.base - (Date.now() - x.t0) / 1000);
    state.current[id] = { base: b, running: false, t0: 0 };
    setLeft((p) => ({ ...p, [id]: b }));
  };
  const reset = (id: string) => {
    state.current[id] = { base: PITCH_SECONDS, running: false, t0: 0 };
    setLeft((p) => ({ ...p, [id]: PITCH_SECONDS }));
  };

  return { left, start, pause, reset };
}

export function IdeathonDetailPage() {
  const dialog = useDialog();
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const { user } = useAuth();
  const [it, setIt] = useState<IdeathonDetail | null>(null);
  const [tally, setTally] = useState<TallyRow[]>([]);
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [ideas, setIdeas] = useState<Map<string, Idea>>(new Map());
  const [people, setPeople] = useState<Map<string, User>>(new Map());
  const [eligible, setEligible] = useState<Idea[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [slSel, setSlSel] = useState<string[]>([]);
  const [winSel, setWinSel] = useState<string[]>([]);
  const [myVote, setMyVote] = useState<string | null>(null);
  const [myScores, setMyScores] = useState<Record<string, number>>({});
  const [linkId, setLinkId] = useState('');
  const [hoDrafts, setHoDrafts] = useState<Record<string, string>>({});

  const role = user?.active_role ?? 'contributor';
  const isOrg = ORG_ROLES.includes(role as (typeof ORG_ROLES)[number]);
  const canScore = PANEL_SCORE_ROLES.includes(
    role as (typeof PANEL_SCORE_ROLES)[number],
  );
  const canSubmit = CAN_SUBMIT.includes(role);

  const reload = useCallback(async () => {
    if (!id) return;
    setError(null);
    try {
      const detail = await ideathonsApi.get(id);
      setIt(detail);
      const ids = [
        ...new Set([
          ...detail.entry_idea_ids,
          ...detail.shortlist,
          ...detail.winners,
        ]),
      ];
      const ideaPairs = await Promise.all(
        ids.map(async (iid) => {
          try {
            return [iid, await ideasApi.get(iid)] as const;
          } catch {
            return null;
          }
        }),
      );
      const imap = new Map<string, Idea>();
      ideaPairs.forEach((p) => {
        if (p) imap.set(p[0], p[1]);
      });
      setIdeas(imap);

      if (
        detail.phase === 'pitch' ||
        detail.phase === 'results' ||
        detail.phase === 'handoff' ||
        detail.tally
      ) {
        try {
          setTally(await ideathonsApi.tally(id));
        } catch {
          setTally([]);
        }
      } else setTally([]);

      try {
        setHandoffs(await ideathonsApi.handoffs(id));
      } catch {
        setHandoffs([]);
      }

      if (!detail.shortlist.length) {
        setSlSel(detail.entry_idea_ids.slice(0, 4));
      } else {
        setSlSel(detail.shortlist.map(String));
      }
      if (!detail.winners.length && detail.shortlist.length) {
        setWinSel([String(detail.shortlist[0])]);
      } else {
        setWinSel(detail.winners.map(String));
      }

      if (user && detail.phase === 'open') {
        try {
          const mine = await ideasApi.list({
            author_id: user.id,
            include_drafts: false,
            limit: 50,
          });
          const linked = new Set(detail.entry_idea_ids);
          setEligible(
            mine.items.filter(
              (i) =>
                !linked.has(i.id) &&
                [
                  'submitted',
                  'under_review',
                  'needs_info',
                  'accepted',
                  'parked',
                  'prototype',
                ].includes(i.status),
            ),
          );
        } catch {
          setEligible([]);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load');
    }
  }, [id, user]);

  useEffect(() => {
    void reload();
  }, [reload]);

  useEffect(() => {
    usersApi
      .list()
      .then((list) => setPeople(new Map(list.map((u) => [u.id, u]))))
      .catch(() => setPeople(new Map()));
  }, []);

  const defaultTab = useMemo(() => {
    if (!it) return 'submissions';
    const idx = Math.min(ithPhaseIdx(it.phase), 4);
    return TABS[idx];
  }, [it]);

  const tabParam = params.get('tab');
  const tab: TabId = TABS.includes(tabParam as TabId)
    ? (tabParam as TabId)
    : defaultTab;

  const setTab = (t: string) => {
    const next = new URLSearchParams(params);
    next.set('tab', t);
    setParams(next);
  };

  const timers = usePitchTimers(it?.shortlist.map(String) ?? []);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed');
    } finally {
      setBusy(false);
    }
  }

  if (error && !it) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }
  if (!it) return <p className="muted">Loading ideathon…</p>;

  const st = ithStatus(it.start_at, it.end_at, it.completed_at);
  const org = isOrg && !it.completed_at;
  const next = IT_NEXT[it.phase];
  const sponsor = people.get(it.sponsor_id);
  const organiser = people.get(it.organiser_id);
  const open = it.phase === 'open' && st === 'active';
  const phaseIdx = ithPhaseIdx(it.phase);

  const advanceHint = (() => {
    const entries = it.entry_idea_ids.length;
    return (
      {
        open:
          st === 'upcoming'
            ? `Opens ${fmtDate(it.start_at)}.`
            : `Closing submissions needs at least 2 entries (${entries} so far).`,
        shortlist: it.shortlist.length
          ? `Shortlist approved (${it.shortlist.length} entries).`
          : 'Approve a shortlist first.',
        pitch: it.voting_closed_at ? 'Voting closed.' : 'Close voting first.',
        results: it.winners.length
          ? 'Winners confirmed.'
          : 'Confirm the winner(s) first.',
        handoff: 'Send every winner to the backlog, then mark complete.',
      } as Record<string, string>
    )[it.phase];
  })();

  let body: ReactNode = null;

  if (tab === 'submissions') {
    body = (
      <div className="stack">
        <div className="card">
          <div className="row" style={{ gap: 10, alignItems: 'flex-end' }}>
            {open && canSubmit ? (
              <Link
                className="btn btn--primary"
                to={`/submit?ideathon=${it.id}`}
              >
                <Icon name="plus" size={16} /> Submit to this ideathon
              </Link>
            ) : null}
            {open && eligible.length ? (
              <div className="field" style={{ margin: 0 }}>
                <label htmlFor="ith-link-select">
                  Or link one of your existing ideas
                </label>
                <div className="row">
                  <select
                    className="select"
                    id="ith-link-select"
                    style={{ maxWidth: 360 }}
                    value={linkId || eligible[0]?.id || ''}
                    onChange={(e) => setLinkId(e.target.value)}
                  >
                    {eligible.map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.title} ({STATUS_META[i.status]?.label ?? i.status})
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="btn"
                    disabled={busy}
                    onClick={() =>
                      void run(async () => {
                        await ideathonsApi.link(
                          it.id,
                          linkId || eligible[0].id,
                        );
                      })
                    }
                  >
                    Link idea
                  </button>
                </div>
              </div>
            ) : null}
          </div>
          {st === 'upcoming' ? (
            <div className="notice" style={{ marginTop: 12 }}>
              <Icon name="calendar" size={16} />
              <span>
                Submissions open on <strong>{fmtDate(it.start_at, true)}</strong>
                .
              </span>
            </div>
          ) : null}
          {!open && st !== 'upcoming' ? (
            <div className="notice" style={{ marginTop: 12 }}>
              <Icon name="lock" size={16} />
              <span>Submissions are closed. Entries are locked.</span>
            </div>
          ) : null}
        </div>
        {!it.entry_idea_ids.length ? (
          <div className="card">
            <EmptyState
              icon="flag"
              title="No entries yet"
              body="Ideas submitted to or linked with this ideathon appear here."
            />
          </div>
        ) : (
          <div className="grid grid-3">
            {it.entry_idea_ids.map((iid) => {
              const idea = ideas.get(iid);
              return (
                <div className="stack stack--sm" key={iid}>
                  {idea ? (
                    <IdeaCard idea={idea} />
                  ) : (
                    <div className="card">
                      <Link to={`/ideas/${iid}`}>{shortId(iid)}…</Link>
                    </div>
                  )}
                  {open && idea?.author_id === user?.id ? (
                    <button
                      type="button"
                      className="btn btn--sm btn--ghost"
                      disabled={busy}
                      onClick={() =>
                        void run(async () => {
                          await ideathonsApi.unlink(it.id, iid);
                        })
                      }
                    >
                      Remove from ideathon
                    </button>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  } else if (tab === 'shortlist') {
    if (it.phase === 'open') {
      body = (
        <LockedNote text="Shortlisting starts when the organiser closes submissions. The Ideathon agent will then propose a ranked shortlist." />
      );
    } else {
      const entries = it.entry_idea_ids;
      const orgSl = isOrg && it.phase === 'shortlist';
      body = (
        <div className="stack">
          <AgentBlock
            agent="Ideathon"
            kind="Computed"
            how="Score out of 100 uses upvotes, template completeness and cross-team discussion. The organiser can add or remove entries before approving."
          >
            <p>
              {it.shortlist.length
                ? `The organiser approved a shortlist of ${it.shortlist.length}${it.shortlist_edited ? ' with manual changes.' : '.'}`
                : `Select at least 2 entries to shortlist (${slSel.length} selected).`}
            </p>
            {entries.map((iid, n) => {
              const idea = ideas.get(iid);
              const checked = slSel.includes(iid);
              return (
                <div className="sl-row" key={iid}>
                  <span className="pitch-no" style={{ width: 26, height: 26 }}>
                    {n + 1}
                  </span>
                  {orgSl ? (
                    <input
                      type="checkbox"
                      checked={checked}
                      aria-label={`Shortlist ${ideaTitle(ideas, iid)}`}
                      onChange={(e) => {
                        setSlSel((prev) =>
                          e.target.checked
                            ? [...prev, iid]
                            : prev.filter((x) => x !== iid),
                        );
                      }}
                    />
                  ) : (
                    <span>
                      {it.shortlist.includes(iid) ? (
                        <Icon name="checkcircle" size={18} />
                      ) : null}
                    </span>
                  )}
                  <div style={{ minWidth: 0 }}>
                    <Link className="listrow__title" to={`/ideas/${iid}`}>
                      {ideaTitle(ideas, iid)}
                    </Link>
                    <div className="small muted" style={{ marginTop: 2 }}>
                      {idea
                        ? STATUS_META[idea.status]?.label ?? idea.status
                        : ''}
                    </div>
                  </div>
                  <div className="pts" style={{ color: 'var(--text)' }}>
                    {idea?.vote_count ?? '—'}
                  </div>
                </div>
              );
            })}
            {orgSl ? (
              <div className="row" style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={busy || slSel.length < 2}
                  onClick={() =>
                    void run(async () => {
                      await ideathonsApi.approveShortlist(it.id, slSel);
                    })
                  }
                >
                  <Icon name="check" size={16} />{' '}
                  {it.shortlist.length ? 'Update shortlist' : 'Approve shortlist'}
                </button>
                <span className="muted small">{slSel.length} selected</span>
              </div>
            ) : (
              <p className="muted small">
                {it.shortlist.length
                  ? 'Shortlist approved.'
                  : 'Waiting for the organiser to approve a shortlist.'}
              </p>
            )}
          </AgentBlock>
          {it.shortlist.length ? (
            <div className="card">
              <div className="card__head">
                <h2>Approved shortlist and pitch order</h2>
                <span className="muted small">Authors were notified</span>
              </div>
              {it.shortlist.map((iid, n) => (
                <div className="listrow" key={iid}>
                  <span className="pitch-no">{n + 1}</span>
                  <div className="listrow__main">
                    <Link className="listrow__title" to={`/ideas/${iid}`}>
                      {ideaTitle(ideas, iid)}
                    </Link>
                  </div>
                  {isOrg &&
                  ['shortlist', 'pitch'].includes(it.phase) &&
                  !it.voting_closed_at ? (
                    <>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        disabled={busy || n === 0}
                        aria-label="Move earlier"
                        onClick={() =>
                          void run(async () => {
                            await ideathonsApi.move(it.id, iid, 'up');
                          })
                        }
                      >
                        <Icon name="up" size={14} />
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        disabled={busy || n === it.shortlist.length - 1}
                        aria-label="Move later"
                        onClick={() =>
                          void run(async () => {
                            await ideathonsApi.move(it.id, iid, 'down');
                          })
                        }
                      >
                        <span
                          style={{
                            display: 'inline-block',
                            transform: 'rotate(180deg)',
                          }}
                        >
                          <Icon name="up" size={14} />
                        </span>
                      </button>
                    </>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      );
    }
  } else if (tab === 'pitch') {
    if (!it.shortlist.length) {
      body = (
        <LockedNote text="Pitch day needs an approved shortlist. The organiser approves it in the Shortlist tab." />
      );
    } else {
      const live = it.phase === 'pitch' && !it.voting_closed_at;
      const started = phaseIdx >= 2;
      body = (
        <div className="stack">
          {started ? (
            <TallyBlock
              rows={tally}
              ideas={ideas}
              winners={it.winners}
              live={live}
              votingClosedAt={it.voting_closed_at}
              org={isOrg && it.phase === 'pitch' && !it.voting_closed_at}
              busy={busy}
              onClose={async () => {
                if (
                  await dialog.confirm({
                    title: 'Close voting?',
                    message: 'Panel scores and audience votes are locked.',
                    confirmLabel: 'Close voting',
                    danger: true,
                  })
                ) {
                  void run(async () => {
                    await ideathonsApi.closeVoting(it.id);
                  });
                }
              }}
            />
          ) : (
            <div className="notice">
              <Icon name="info" size={16} />
              <span>
                Pitch day has not started. You can preview the pitch order
                below.
              </span>
            </div>
          )}
          {it.shortlist.map((iid, n) => {
            const idea = ideas.get(iid);
            const own =
              idea &&
              user &&
              (idea.author_id === user.id ||
                idea.co_author_ids.includes(user.id));
            const left = timers.left[iid] ?? PITCH_SECONDS;
            const mine = myScores[iid];
            return (
              <article className="card pitch-card" key={iid}>
                <div className="pitch-card__head">
                  <span className="pitch-no">{n + 1}</span>
                  <div className="grow" style={{ minWidth: 0 }}>
                    <Link className="listrow__title" to={`/ideas/${iid}`}>
                      {ideaTitle(ideas, iid)}
                    </Link>
                    <div className="meta-row muted small">
                      {idea
                        ? STATUS_META[idea.status]?.label ?? idea.status
                        : ''}
                    </div>
                  </div>
                  <div className="row" style={{ gap: 10 }}>
                    <div
                      className={`timer ${left <= 30 ? 'timer--low' : ''}`}
                      role="timer"
                      aria-label="Pitch timer"
                    >
                      {fmtClock(left)}
                    </div>
                    <div className="row" style={{ gap: 6 }}>
                      <button
                        type="button"
                        className="btn btn--sm"
                        onClick={() => timers.start(iid)}
                      >
                        Start
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm"
                        onClick={() => timers.pause(iid)}
                      >
                        Pause
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--ghost"
                        onClick={() => timers.reset(iid)}
                      >
                        Reset
                      </button>
                    </div>
                  </div>
                </div>
                {idea ? (
                  <details>
                    <summary className="muted" style={{ cursor: 'pointer' }}>
                      Pitch summary
                    </summary>
                    <dl className="dl hs-wrap" style={{ marginTop: 8 }}>
                      <dt>Problem</dt>
                      <dd>{idea.problem || '—'}</dd>
                      <dt>Solution</dt>
                      <dd>{idea.solution || '—'}</dd>
                      <dt>Success</dt>
                      <dd>{idea.success_metrics || '—'}</dd>
                    </dl>
                  </details>
                ) : null}
                <div className="grid grid-2" style={{ alignItems: 'start' }}>
                  <div>
                    <div className="label" style={{ marginBottom: 6 }}>
                      Panel score (1 to 10)
                    </div>
                    {canScore ? (
                      own ? (
                        <p className="muted small">
                          You wrote this idea, so you cannot score it.
                        </p>
                      ) : (
                        <>
                          <div className="score-btns">
                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((v) => (
                              <button
                                key={v}
                                type="button"
                                className="btn btn--sm"
                                disabled={!live || busy}
                                aria-pressed={mine === v}
                                onClick={() =>
                                  void run(async () => {
                                    await ideathonsApi.score(it.id, iid, v);
                                    setMyScores((s) => ({ ...s, [iid]: v }));
                                  })
                                }
                              >
                                {v}
                              </button>
                            ))}
                          </div>
                          <p className="muted small" style={{ marginTop: 6 }}>
                            {mine
                              ? `Your score: ${mine}.`
                              : live
                                ? 'You have not scored this pitch.'
                                : 'Scoring is not open.'}
                          </p>
                        </>
                      )
                    ) : (
                      <p className="muted small">
                        Panel scoring is for reviewers, leadership and
                        administrators.
                      </p>
                    )}
                  </div>
                  <div>
                    <div className="label" style={{ marginBottom: 6 }}>
                      Audience vote
                    </div>
                    {own ? (
                      <p className="muted small">
                        You cannot vote for your own idea.
                      </p>
                    ) : (
                      <>
                        <button
                          type="button"
                          className={`btn ${myVote === iid ? 'btn--primary' : ''}`}
                          disabled={!live || busy}
                          aria-pressed={myVote === iid}
                          onClick={() =>
                            void run(async () => {
                              const r = await ideathonsApi.vote(it.id, iid);
                              setMyVote(r.voted ? iid : null);
                            })
                          }
                        >
                          <Icon name="up" size={16} />{' '}
                          {myVote === iid ? 'Your vote' : 'Vote for this pitch'}
                        </button>
                        <p className="muted small" style={{ marginTop: 6 }}>
                          One vote each. You can change it until voting closes.
                        </p>
                      </>
                    )}
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      );
    }
  } else if (tab === 'results') {
    if (phaseIdx < 3) {
      body = (
        <LockedNote text="Results appear after voting is closed and the organiser moves the ideathon to Results." />
      );
    } else {
      const orgWin = isOrg && it.phase === 'results' && !it.winners.length;
      const rank = tally.length
        ? tally
        : it.shortlist.map((iid) => ({
            idea_id: iid,
            panel_avg: 0,
            panel_n: 0,
            panel_pct: 0,
            audience_votes: 0,
            aud_pct: 0,
            combined: 0,
          }));
      body = (
        <div className="stack">
          {it.winners.map((iid) => {
            const r = rank.find((x) => x.idea_id === iid);
            return (
              <div className="winner-banner" role="status" key={iid}>
                <span className="winner-ic">
                  <Icon name="trophy" size={24} />
                </span>
                <div style={{ minWidth: 0 }}>
                  <div
                    className="eyebrow eyebrow--plain"
                    style={{ color: 'var(--gold-ink)' }}
                  >
                    Winner · {it.title}
                  </div>
                  <h3>
                    <Link to={`/ideas/${iid}`}>{ideaTitle(ideas, iid)}</Link>
                  </h3>
                  <p className="small" style={{ marginTop: 4 }}>
                    Combined score {r ? r.combined.toFixed(0) : '–'} of 100 ·
                    winner points shared between the authors.
                  </p>
                </div>
              </div>
            );
          })}
          {!it.winners.length ? (
            <AgentBlock
              agent="Ideathon"
              kind="Computed"
              how={`Ranking = ${PANEL_WEIGHT}% panel + ${AUDIENCE_WEIGHT}% audience. The organiser confirms.`}
            >
              <p>
                <strong>Proposal:</strong>{' '}
                {rank[0]
                  ? `${ideaTitle(ideas, rank[0].idea_id)} leads with ${rank[0].combined.toFixed(0)} out of 100.`
                  : 'No tally yet.'}{' '}
                Confirm below.
              </p>
            </AgentBlock>
          ) : null}
          <div className="card">
            <div className="card__head">
              <h2>
                {it.winners.length ? 'Final ranking' : 'Proposed ranking'}
              </h2>
              {it.winners.length ? (
                <Pill variant="success" icon="check">
                  Confirmed {it.results_at ? fmtDate(it.results_at) : ''}
                </Pill>
              ) : (
                <Pill variant="warning">Proposal</Pill>
              )}
            </div>
            {rank.map((r, n) => (
              <div className="sl-row" key={r.idea_id}>
                <span className="pitch-no" style={{ width: 26, height: 26 }}>
                  {n + 1}
                </span>
                {orgWin ? (
                  <input
                    type="checkbox"
                    checked={winSel.includes(r.idea_id)}
                    aria-label={`Winner: ${ideaTitle(ideas, r.idea_id)}`}
                    onChange={(e) => {
                      setWinSel((prev) => {
                        let next = e.target.checked
                          ? [...prev, r.idea_id]
                          : prev.filter((x) => x !== r.idea_id);
                        if (next.length > 2) next = next.slice(-2);
                        return next;
                      });
                    }}
                  />
                ) : (
                  <span />
                )}
                <div style={{ minWidth: 0 }}>
                  <Link className="listrow__title" to={`/ideas/${r.idea_id}`}>
                    {ideaTitle(ideas, r.idea_id)}
                  </Link>
                  {it.winners.includes(r.idea_id) ? (
                    <>
                      {' '}
                      <Pill variant="gold" icon="trophy">
                        Winner
                      </Pill>
                    </>
                  ) : it.winners.length ? (
                    <>
                      {' '}
                      <Pill>Finalist</Pill>
                    </>
                  ) : null}
                  <div className="muted small">
                    panel {r.panel_n ? `${r.panel_avg.toFixed(1)}/10` : 'none'} ·{' '}
                    {r.audience_votes} audience
                  </div>
                </div>
                <div className="pts" style={{ color: 'var(--text)' }}>
                  {r.combined.toFixed(0)}
                </div>
              </div>
            ))}
            {orgWin ? (
              <div className="row" style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="btn btn--primary"
                  disabled={busy || !winSel.length}
                  onClick={async () => {
                    if (
                      await dialog.confirm({
                        title: `Confirm ${winSel.length === 2 ? '2 winners' : 'the winner'}?`,
                        message: 'This cannot be undone.',
                        confirmLabel: 'Confirm winners',
                        danger: true,
                      })
                    ) {
                      void run(async () => {
                        await ideathonsApi.confirmWinners(it.id, winSel);
                      });
                    }
                  }}
                >
                  <Icon name="trophy" size={16} /> Confirm winner
                  {winSel.length === 2 ? 's' : ''}
                </button>
                <span className="muted small">
                  {winSel.length} selected (choose 1 or 2)
                </span>
              </div>
            ) : null}
            {!orgWin && !it.winners.length ? (
              <p className="muted small" style={{ marginTop: 12 }}>
                Waiting for the organiser to confirm the winners.
              </p>
            ) : null}
          </div>
          {it.winners.length ? (
            <div className="notice notice--brand">
              <Icon name="award" size={16} />
              <span>
                Points for winners and finalists were added to the{' '}
                <Link to="/recognition?tab=how">recognition ledger</Link>.
              </span>
            </div>
          ) : null}
        </div>
      );
    }
  } else {
    // handoff
    if (phaseIdx < 4) {
      body = (
        <LockedNote text="Handoff opens after winners are confirmed and the organiser moves the ideathon to Handoff." />
      );
    } else {
      const sentMap = new Map(handoffs.map((h) => [h.idea_id, h]));
      body = (
        <div className="stack">
          <div className="notice">
            <Icon name="info" size={16} />
            <span>
              <strong>Simulated handoff.</strong> Sending creates a backlog item
              inside IdeaKonnekt only. No external hackathon tool is connected.
            </span>
          </div>
          {it.winners.map((iid) => {
            const sent = sentMap.get(iid);
            const idea = ideas.get(iid);
            const draftDefault =
              hoDrafts[iid] ??
              [
                `Hackathon problem from ideathon “${it.title}”`,
                '',
                `Challenge: ${it.challenges[0] ?? it.theme}`,
                '',
                `Problem: ${idea?.problem ?? ''}`,
                '',
                `Proposed approach: ${idea?.solution ?? ''}`,
                '',
                `Success measure: ${idea?.success_metrics ?? ''}`,
                '',
                `Effort estimate: ${idea?.effort ?? '—'}`,
              ].join('\n');
            if (sent) {
              return (
                <div className="card" key={iid}>
                  <div className="card__head">
                    <h3>
                      <Link to={`/ideas/${iid}`}>{ideaTitle(ideas, iid)}</Link>
                    </h3>
                    <Pill variant="success" icon="check">
                      Sent to backlog (simulated)
                    </Pill>
                  </div>
                  <div
                    className="quote hs-wrap"
                    style={{ whiteSpace: 'pre-wrap' }}
                  >
                    {sent.statement}
                  </div>
                  <p className="muted small" style={{ marginTop: 8 }}>
                    Sent {fmtDate(sent.created_at, true)}
                    {sent.edited ? ' after editing the draft' : ' as drafted'}.
                  </p>
                </div>
              );
            }
            return (
              <div className="card" key={iid}>
                <div className="card__head">
                  <h3>
                    <Link to={`/ideas/${iid}`}>{ideaTitle(ideas, iid)}</Link>
                  </h3>
                  <Pill variant="warning">Not sent yet</Pill>
                </div>
                <AgentBlock
                  agent="Ideathon"
                  kind="Templated"
                  how="The statement is a fixed template filled from the challenge and winning idea fields. Edit freely before sending."
                >
                  <p>
                    Drafted a hackathon problem statement
                    {org ? '. Edit it below, then send it.' : '.'}
                  </p>
                </AgentBlock>
                <div className="field" style={{ marginTop: 12 }}>
                  <label htmlFor={`ho-${iid}`}>Problem statement</label>
                  <textarea
                    className="textarea"
                    id={`ho-${iid}`}
                    rows={12}
                    readOnly={!org}
                    value={draftDefault}
                    onChange={(e) =>
                      setHoDrafts((d) => ({ ...d, [iid]: e.target.value }))
                    }
                  />
                </div>
                {org ? (
                  <div className="row">
                    <button
                      type="button"
                      className="btn btn--primary"
                      disabled={busy}
                      onClick={async () => {
                        const text = (hoDrafts[iid] ?? draftDefault).trim();
                        if (
                          await dialog.confirm({
                            title: 'Send to the hackathon backlog?',
                            message: 'This is a simulated handoff inside IdeaKonnekt.',
                            confirmLabel: 'Send',
                          })
                        ) {
                          void run(async () => {
                            await ideathonsApi.sendHandoff(
                              it.id,
                              iid,
                              text,
                              text !== draftDefault.trim(),
                            );
                          });
                        }
                      }}
                    >
                      <Icon name="send" size={16} /> Send to hackathon backlog
                    </button>
                  </div>
                ) : (
                  <p className="muted small">The organiser edits and sends this.</p>
                )}
              </div>
            );
          })}
          <div className="card">
            <div className="card__head">
              <h2>Hackathon backlog</h2>
              <span className="muted small">
                {handoffs.length} item{handoffs.length === 1 ? '' : 's'}
              </span>
            </div>
            {handoffs.length ? (
              handoffs.map((h) => (
                <div className="listrow" key={h.id}>
                  <div className="listrow__main">
                    <Link className="listrow__title" to={`/ideas/${h.idea_id}`}>
                      {ideaTitle(ideas, h.idea_id)}
                    </Link>
                    <div className="muted small">
                      Sent {fmtDate(h.created_at, true)}
                    </div>
                  </div>
                  <Pill variant="info">{h.status}</Pill>
                </div>
              ))
            ) : (
              <EmptyState
                icon="layers"
                title="Nothing in the backlog yet"
                body="Winners appear here once the organiser sends them."
              />
            )}
          </div>
          {it.completed_at ? (
            <div className="notice notice--ok">
              <Icon name="checkcircle" size={16} />
              <span>
                This ideathon was completed on {fmtDate(it.completed_at, true)}.
              </span>
            </div>
          ) : null}
        </div>
      );
    }
  }

  return (
    <div className="stack stack--lg">
      <p>
        <Link to="/ideathons">← Ideathons</Link>
      </p>
      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="card">
        <div className="row" style={{ gap: 6 }}>
          <StatusPillFor it={it} />
          <Pill icon="flag">{it.theme}</Pill>
        </div>
        <h1 className="idea-title">{it.title}</h1>
        {isOrg && !it.completed_at ? (
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Link className="btn btn--ghost" to={`/ideathons/${it.id}/edit`}>
              <Icon name="edit" size={14} /> Edit details
            </Link>
          </div>
        ) : null}
        <div className="meta-row">
          <span className="muted">Sponsor</span>
          {sponsor ? (
            <span className="person">
              <Avatar name={sponsor.name} avatar={sponsor.avatar} size="sm" />
              <Link to={`/people/${sponsor.id}`}>{sponsor.name}</Link>
            </span>
          ) : (
            <span className="muted">{shortId(it.sponsor_id)}</span>
          )}
          <span className="muted">Organiser</span>
          {organiser ? (
            <Link to={`/people/${organiser.id}`}>{organiser.name}</Link>
          ) : (
            <span className="muted">{shortId(it.organiser_id)}</span>
          )}
          <span className="muted">
            {fmtDate(it.start_at, true)} to {fmtDate(it.end_at, true)}
          </span>
        </div>
        <div
          className="stack stack--sm"
          style={{ margin: 'var(--space-3) 0' }}
        >
          {it.challenges.map((c, n) => (
            <div className="quote" key={n}>
              <span className="muted small">Challenge {n + 1}</span>
              <br />
              {c}
            </div>
          ))}
        </div>
        <div className="ith-metrics" style={{ marginBottom: 'var(--space-4)' }}>
          <span>
            <strong>{it.entry_idea_ids.length}</strong> entries
          </span>
          <span>
            <strong>{it.shortlist.length}</strong> shortlisted
          </span>
          <span>
            <strong>{it.winners.length}</strong> winners
          </span>
        </div>
        <IdeathonStepper it={it} />
        {org && next ? (
          <div className="row" style={{ marginTop: 'var(--space-4)' }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={async () => {
                const label =
                  ITH_PHASES.find((p) => p.id === next)?.label ?? next;
                if (
                  await dialog.confirm({
                    title: `Advance to ${label}?`,
                    message: 'Phases cannot be skipped.',
                    confirmLabel: 'Advance',
                  })
                ) {
                  void run(async () => {
                    await ideathonsApi.advance(it.id);
                  });
                }
              }}
            >
              <Icon name="chevronR" size={16} /> Advance to{' '}
              {ITH_PHASES.find((p) => p.id === next)?.label}
            </button>
            <span className="muted small">{advanceHint}</span>
          </div>
        ) : null}
        {org && !next ? (
          <div className="row" style={{ marginTop: 'var(--space-4)' }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy || !!it.completed_at}
              onClick={async () => {
                if (
                  await dialog.confirm({
                    title: 'Mark this ideathon complete?',
                    message: 'It moves to Past.',
                    confirmLabel: 'Mark complete',
                  })
                ) {
                  void run(async () => {
                    await ideathonsApi.complete(it.id);
                  });
                }
              }}
            >
              <Icon name="check" size={16} /> Mark ideathon complete
            </button>
            <span className="muted small">{advanceHint}</span>
          </div>
        ) : null}
        {org ? (
          <AgentRunsPanel
            ideathonId={it.id}
            panelWeight={PANEL_WEIGHT}
            audienceWeight={AUDIENCE_WEIGHT}
            titles={Object.fromEntries([...ideas].map(([id, idea]) => [id, idea.title]))}
          />
        ) : null}
        {!isOrg && !it.completed_at ? (
          <p className="muted small" style={{ marginTop: 'var(--space-3)' }}>
            Leadership and administrators run the phases. You can see every step
            and take part where your role allows.
          </p>
        ) : null}
      </div>

      <TabsNav
        tabs={[
          {
            id: 'submissions',
            label: 'Submissions',
            count: it.entry_idea_ids.length,
          },
          {
            id: 'shortlist',
            label: 'Shortlist',
            count: it.shortlist.length || null,
          },
          { id: 'pitch', label: 'Pitch day' },
          { id: 'results', label: 'Results' },
          { id: 'handoff', label: 'Handoff' },
        ]}
        active={tab}
        onSelect={setTab}
      />
      {body}
    </div>
  );
}

export default IdeathonDetailPage;
