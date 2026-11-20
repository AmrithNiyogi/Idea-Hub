/**
 * Recognition sub-views. Points still come only from outcomes, collaboration
 * and verified impact. Upvotes and idea counts earn nothing, and nothing here
 * expires, decays or asks for a daily check-in.
 *
 * view="standing"  your level, first steps, ways to earn
 * view="board"     period filter, podium, ranked list, strongest per area
 * view="thanks"    written thanks
 */
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Team } from '../../api/users';
import { PERIODS, fmtNum } from '../../constants/ideathons';
import type { User } from '../../types/auth';
import type {
  LeaderboardRow,
  LedgerEntry,
  RecognitionRules,
  ThanksItem,
} from '../../types/recognition';
import { relTime } from '../../utils/format';
import { Avatar, Icon } from '../Icons';
import { EmptyState } from '../ui/EmptyState';
import { ThanksCard } from './ThanksCard';
import { InfoTip } from '../ui/InfoTip';
import { LEVEL_MOTTO, LevelMark } from './LevelMark';

export type BoardView = 'standing' | 'board' | 'thanks';

const DIMS = ['quality', 'collab', 'delivery', 'impact'] as const;
type Dim = (typeof DIMS)[number];

const DIM_DOT: Record<Dim, string> = {
  quality: 'lg-q',
  collab: 'lg-c',
  delivery: 'lg-d',
  impact: 'lg-i',
};

const DIM_WHY: Record<Dim, string> = {
  quality: 'Complete ideas and sound decisions',
  collab: 'Joining, merging and helping others',
  delivery: 'Getting ideas built and shipped',
  impact: 'Impact that a second person confirms',
};

/** Ways to earn, in the order an idea travels. Awards are excluded on purpose. */
const WAYS_TO_EARN = [
  'submit',
  'dedupe',
  'accepted',
  'prototype',
  'implemented',
  'helpful',
  'thanks',
  'ontime_review',
  'volunteer',
  'impact_verified',
  'pitch_finalist',
];

/** Where each way to earn starts, when a page exists for it. */
const START_AT: Record<string, { to: string; label: string }> = {
  submit: { to: '/submit', label: 'Start a complete idea' },
  ontime_review: { to: '/review', label: 'Open the review queue' },
  pitch_finalist: { to: '/ideathons', label: 'See open ideathons' },
};

/** The first things to try, so a new person sees a way in. */
const FIRST_STEPS = [
  { rule: 'submit', title: 'Submit a complete idea', detail: 'Eight template items, checked on submit.', to: '/submit', cta: 'Start an idea' },
  { rule: 'dedupe', title: 'Join an idea that already exists', detail: 'Joining beats duplicating. Co-authors earn points too.', to: '/explore', cta: 'Find an idea' },
  { rule: 'helpful', title: 'Comment on an idea that matters to you', detail: 'The author can mark a comment helpful, and that earns you points.', to: '/explore', cta: 'Browse ideas' },
];

interface Props {
  view: BoardView;
  board: LeaderboardRow[];
  rules: RecognitionRules;
  me: User | null;
  people: Map<string, User>;
  teams: Map<string, Team>;
  recent: LedgerEntry[];
  period: string;
  thanks: ThanksItem[];
  onChanged: () => void;
}

/** Movement on the board: rank change and points this week, in plain words. */
function moveText(r: LeaderboardRow): string {
  const weekly = r.week_points ? `+${fmtNum(r.week_points)} this week` : '';
  if (r.rank_change === undefined || r.rank_change === null) return weekly;
  const move =
    r.rank_change > 0 ? `Up ${r.rank_change}` : r.rank_change < 0 ? `Down ${-r.rank_change}` : 'Same place';
  return weekly ? `${move} · ${weekly}` : move;
}

function capText(r: Record<string, unknown>): string | null {
  if (typeof r.cap_per_month === 'number') return `Up to ${r.cap_per_month} a month`;
  if (typeof r.max_per_idea === 'number') return `Up to ${r.max_per_idea} per idea`;
  if (typeof r.max_points === 'number') return `Up to ${fmtNum(r.max_points)} per idea`;
  return null;
}

export function ContributionBoard({
  view,
  board,
  rules,
  me,
  people,
  teams,
  recent,
  period,
  thanks,
  onChanged,
}: Props) {
  const levels = [...rules.levels].sort((a, b) => a.min - b.min);
  const meRow = me ? board.find((r) => r.user_id === me.id) : undefined;
  // Development only: preview any level on the standing card without earning points.
  const [previewPts, setPreviewPts] = useState<number | null>(null);
  const myPoints = previewPts ?? meRow?.points ?? 0;
  const myIdx = levels.reduce((acc, l, i) => (myPoints >= l.min ? i : acc), 0);
  const myLevel = levels[myIdx];
  const nextLevel = levels[myIdx + 1];
  const pct = nextLevel
    ? Math.min(100, ((myPoints - myLevel.min) / (nextLevel.min - myLevel.min)) * 100)
    : 100;

  const protoPts = Number(rules.rules.prototype?.points) || 0;
  const storageKey = me ? `ih.level.${me.id}` : null;
  const currentLevelId = myLevel?.id;
  // Level-up moment: remembered per viewer in this browser only. Skipped when storage is unavailable.
  const [levelUp, setLevelUp] = useState<string | null>(() => {
    try {
      const prev = storageKey ? window.localStorage.getItem(storageKey) : null;
      const prevIdx = prev ? levels.findIndex((l) => l.id === prev) : -1;
      return prevIdx >= 0 && prevIdx < myIdx && myLevel ? myLevel.name : null;
    } catch {
      return null;
    }
  });
  useEffect(() => {
    if (!storageKey || !currentLevelId) return;
    try {
      window.localStorage.setItem(storageKey, currentLevelId);
    } catch {
      /* storage unavailable: the level-up moment is simply not remembered */
    }
  }, [storageKey, currentLevelId]);

  const myDims = meRow?.dims ?? {};
  const strongest = DIMS.reduce<Dim | null>((best, d) => {
    const v = myDims[d] ?? 0;
    if (v <= 0) return best;
    return !best || v > (myDims[best] ?? 0) ? d : best;
  }, null);

  const spotlights = DIMS.map((d) => {
    const top = board
      .filter((r) => (r.dims?.[d] ?? 0) > 0)
      .sort((a, b) => (b.dims?.[d] ?? 0) - (a.dims?.[d] ?? 0))[0];
    return { dim: d, row: top };
  });

  const ways = WAYS_TO_EARN.map((id) => ({ id, rule: rules.rules[id] })).filter(
    (w): w is { id: string; rule: Record<string, unknown> } => !!w.rule,
  );

  const nameOf = (uid: string) => people.get(uid)?.name ?? `${uid.slice(0, 8)}…`;
  const teamOf = (uid: string) => {
    const t = people.get(uid)?.team_id;
    return t ? teams.get(t)?.name ?? null : null;
  };

  const [first, second, third] = board;

  /** The area where a person has the most points, so each row says what they are known for. */
  const bestArea = (r: LeaderboardRow): Dim | null => {
    let best: Dim | null = null;
    for (const d of DIMS) {
      const v = r.dims?.[d] ?? 0;
      if (v > 0 && (!best || v > (r.dims?.[best] ?? 0))) best = d;
    }
    return best;
  };
  const restRows = board.slice(3, 25);

  if (view === 'thanks') {
    return (
      <div className="cb">
        <ThanksCard me={me} people={people} recent={thanks} nameOf={nameOf} onSent={onChanged} />
      </div>
    );
  }

  if (view === 'board') {
    return (
      <div className="cb">
        {/* Ranked */}
        <section className="cb-section" aria-labelledby="cb-rank">
          <div className="cb-section__head">
            <h2 id="cb-rank">
              Ranked by points{" "}
              <InfoTip label="How ranking works">
                Ranked by points in the selected period. Levels still use lifetime
                points, so switching period never changes anyone's level.
              </InfoTip>
            </h2>
            <div className="chip-row" role="group" aria-label="Period">
              {Object.entries(PERIODS).map(([k, label]) => (
                <Link
                  key={k}
                  className="chip-link"
                  to={`/recognition?tab=leaderboard&period=${k}`}
                  aria-current={k === period ? 'true' : undefined}
                >
                  {label}
                </Link>
              ))}
            </div>
            <p className="muted small">
              Points from outcomes, collaboration and verified impact. Ideas are
              never counted as a score.
            </p>
          </div>

          {board.length ? (
            <>
              <ol className="cb-podium" aria-label="Top three">
                {[first, second, third].map((r, i) =>
                  r ? (
                    <li
                      key={r.user_id}
                      className={`cb-podium__item cb-podium__item--${i + 1} ${r.user_id === me?.id ? 'is-me' : ''}`}
                      data-level={r.level_id}
                    >
                      <div className="cb-podium__head">
                        <Avatar name={nameOf(r.user_id)} avatar={people.get(r.user_id)?.avatar ?? 1} size="lg" />
                        <span className="cb-podium__rankbig" aria-label={`Rank ${i + 1}`}>{i + 1}</span>
                      </div>
                      <Link className="strong cb-podium__name" to={`/people/${r.user_id}`}>
                        {nameOf(r.user_id)}
                        {r.user_id === me?.id ? " (you)" : ""}
                      </Link>
                      <span className="cb-podium__level lvl" data-level={r.level_id}>
                        <LevelMark levelId={r.level_id} size={16} />
                        {r.level_name}
                      </span>
                      <div className="cb-podium__foot">
                        <span className="cb-podium__pts">{fmtNum(r.points)}</span>
                        <span className="cb-podium__best">
                          {bestArea(r) ? `Best at ${rules.dims[bestArea(r) as Dim]}` : "Still finding their area"}
                        </span>
                      </div>
                      <span
                        className="cb-podium__base"
                        aria-hidden="true"
                        style={{ width: `${Math.max(4, Math.round((r.points / (board[0]?.points || 1)) * 100))}%` }}
                      />
                    </li>
                  ) : (
                    <li
                      key={`open-${i + 1}`}
                      className={`cb-podium__item cb-podium__item--${i + 1} cb-podium__item--open`}
                    >
                      <span className="cb-podium__rank">{i + 1}</span>
                      <span className="strong cb-podium__open">Open place</span>
                      <span className="muted small">Earn your way here</span>
                    </li>
                  ),
                )}
              </ol>

              {restRows.length ? (
                <div className="cb-list">
                  {restRows.map((r, n) => (
                    <div
                      key={r.user_id}
                      className={`cb-row ${r.user_id === me?.id ? "is-me" : ""}`}
                      data-level={r.level_id}
                    >
                      <span className="cb-row__rankbig">{n + 4}</span>
                      <div className="cb-row__who">
                        <Avatar name={nameOf(r.user_id)} avatar={people.get(r.user_id)?.avatar ?? 1} />
                        <div className="cb-row__names">
                          <Link className="strong" to={`/people/${r.user_id}`}>
                            {nameOf(r.user_id)}
                            {r.user_id === me?.id ? " (you)" : ""}
                          </Link>
                          <span className="cb-row__level lvl" data-level={r.level_id}>
                            <LevelMark levelId={r.level_id} size={14} />
                            {r.level_name}
                            {teamOf(r.user_id) ? ` · ${teamOf(r.user_id)}` : ""}
                          </span>
                        </div>
                      </div>
                      <div className="cb-row__foot">
                        <span className="cb-row__pts">{fmtNum(r.points)}</span>
                        <span className="cb-row__best">
                          {bestArea(r) ? `Best at ${rules.dims[bestArea(r) as Dim]}` : ""}
                          {moveText(r) ? <span className="cb-move">{moveText(r)}</span> : null}
                        </span>
                      </div>
                      <span
                        className="cb-row__base"
                        aria-hidden="true"
                        style={{ width: `${Math.max(4, Math.round((r.points / (board[0]?.points || 1)) * 100))}%` }}
                      />
                    </div>
                  ))}
                </div>
              ) : null}
            </>
          ) : (
            <EmptyState
              icon="award"
              title="The board starts with the first outcome"
              body="Points appear when ideas are accepted, prototyped, implemented or verified."
            />
          )}
        </section>

        {/* Spotlights: several ways to stand out, not one number */}
        <section className="cb-section" aria-labelledby="cb-spots">
          <div className="cb-section__head">
            <h2 id="cb-spots">Strongest in each area</h2>
            <p className="muted small">
              A different kind of contribution can lead. Nobody has to win every area.
            </p>
          </div>
          <div className="cb-spots">
            {spotlights.map(({ dim, row }) => (
              <div key={dim} className={`cb-spot cb-spot--${dim}`}>
                <div className="cb-spot__area">
                  <span className={`cb-way__dot ${DIM_DOT[dim]}`} aria-hidden="true" />
                  {rules.dims[dim] ?? dim}
                </div>
                {row ? (
                  <>
                    <div className="cb-spot__who">
                      <Avatar name={nameOf(row.user_id)} avatar={people.get(row.user_id)?.avatar ?? 1} />
                      <div>
                        <div className="strong">{nameOf(row.user_id)}</div>
                        <div className="muted small">{teamOf(row.user_id) ?? DIM_WHY[dim]}</div>
                      </div>
                    </div>
                    <div className="cb-spot__pts">
                      {fmtNum(row.dims?.[dim] ?? 0)}
                      <span className="muted small"> points</span>
                    </div>
                  </>
                ) : (
                  <p className="muted small">Be the first. {DIM_WHY[dim]}.</p>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  const gap = nextLevel ? nextLevel.min - myPoints : 0;
  const ideasToNext = protoPts > 0 ? Math.ceil(gap / protoPts) : 0;
  const protoHint =
    nextLevel && protoPts > 0 && gap <= protoPts * 10
      ? `About ${ideasToNext} ${ideasToNext === 1 ? "idea" : "ideas"} reaching Prototype would get you there.`
      : "";
  const ringLength = 326.73;
  const ringGap = 10;

  // view === 'standing'
  return (
    <div className="cb">
      {levelUp ? (
        <div className="cb-levelup" role="status">
          <LevelMark levelId={levels.find((l) => l.name === levelUp)?.id ?? "spark"} size={40} />
          <div>
            <div className="eyebrow eyebrow--plain">Level up</div>
            <p>
              <span className="strong">You reached {levelUp}.</span> Your ideas and
              points carried you here.
            </p>
          </div>
          <button type="button" className="btn btn--ghost btn--sm" onClick={() => setLevelUp(null)}>
            Dismiss
          </button>
        </div>
      ) : null}

      {import.meta.env.DEV ? (
        <div className="cb-preview" role="group" aria-label="Preview a level (development only)">
          <span className="cb-preview__label">Preview level · development only</span>
          {levels.map((l) => (
            <button
              key={l.id}
              type="button"
              className="chip-link"
              aria-pressed={previewPts !== null && myLevel?.id === l.id}
              onClick={() => setPreviewPts(l.min + 10)}
            >
              {l.name}
            </button>
          ))}
          <button
            type="button"
            className="chip-link"
            aria-pressed={previewPts === null}
            onClick={() => setPreviewPts(null)}
          >
            Real points
          </button>
        </div>
      ) : null}

      <section className="cb-hero" data-level={myLevel?.id ?? "spark"} aria-label="Your standing">
        <div className="cb-hero__ring" aria-hidden="true">
          <svg viewBox="0 0 120 120">
            {levels.map((l, i) => {
              const slot = ringLength / levels.length;
              const segLen = slot - ringGap;
              const offset = -(i * slot + ringGap / 2);
              const fill = i < myIdx ? segLen : i === myIdx ? (segLen * pct) / 100 : 0;
              return (
                <g key={l.id}>
                  <circle
                    className="cb-hero__seg"
                    cx="60"
                    cy="60"
                    r="52"
                    style={{ strokeDasharray: `${segLen} ${ringLength}`, strokeDashoffset: offset }}
                  />
                  {fill > 0 ? (
                    <circle
                      className="cb-hero__fill"
                      cx="60"
                      cy="60"
                      r="52"
                      style={{
                        strokeDasharray: `${fill} ${ringLength}`,
                        strokeDashoffset: offset,
                        stroke: i < myIdx ? `var(--lvl-${l.id})` : "var(--lvl)",
                      }}
                    />
                  ) : null}
                </g>
              );
            })}
          </svg>
          <div className="cb-hero__ringlabel">
            <span className="cb-hero__levelnum">{myIdx + 1}</span>
            <span className="cb-hero__of">of {levels.length}</span>
          </div>
        </div>

        <div className="cb-hero__main">
          <div className="eyebrow eyebrow--plain">
            Your level{" "}
            <InfoTip label="How levels work">
              Levels come from lifetime points: Spark, Contributor, Builder, Catalyst
              and Pioneer. A quiet quarter never lowers your level.
            </InfoTip>
          </div>
          <div className="cb-hero__name">
            <LevelMark levelId={myLevel?.id ?? "spark"} size={30} />
            {myLevel?.name ?? "Spark"}
          </div>
          <p className="cb-hero__motto">{LEVEL_MOTTO[myLevel?.id ?? "spark"]}</p>
          <div className="cb-hero__meta">
            <span className="cb-hero__pts">{fmtNum(myPoints)} points</span>
            {nextLevel ? (
              <span>
                {" · "}
                {fmtNum(gap)} to {nextLevel.name}
              </span>
            ) : (
              <span> · top level reached</span>
            )}
          </div>
          <p className="cb-hero__next">
            {strongest ? (
              <>
                Strongest area: <strong>{rules.dims[strongest] ?? strongest}</strong>.{" "}
              </>
            ) : myPoints === 0 ? (
              "Your first points come from moving one idea forward. "
            ) : null}
            {protoHint}
          </p>
          <ol className="cb-ladder2" aria-label="Levels">
            {levels.map((l, i) => (
              <li
                key={l.id}
                className={`cb-ladder2__step${i <= myIdx ? " is-reached" : ""}${i === myIdx ? " is-here" : ""}`}
              >
                <span className="cb-ladder2__dot" aria-hidden="true" />
                <span className="cb-ladder2__name">{l.name}</span>
                <span className="cb-ladder2__min">{fmtNum(l.min)}</span>
              </li>
            ))}
          </ol>
        </div>

        <aside className="cb-hero__recent" aria-label="Recent points">
          <div className="eyebrow eyebrow--plain">Recent</div>
          {recent.length ? (
            <ol className="cb-timeline">
              {recent.slice(0, 4).map((e) => (
                <li key={e.id}>
                  <span className="cb-timeline__pts">+{fmtNum(e.points)}</span>
                  <span className="cb-timeline__text">
                    {e.rule_label ?? e.note}
                    {e.escrow ? " (held until confirmed)" : ""}
                  </span>
                  <span className="muted small">{relTime(e.created_at)}</span>
                </li>
              ))}
            </ol>
          ) : (
            <div className="cb-hero__empty">
              <p>No points yet. The first one comes from moving an idea forward.</p>
              <Link className="btn btn--sm btn--primary" to="/submit">
                Start a complete idea
              </Link>
            </div>
          )}
        </aside>
      </section>

      {me && myPoints < 50 ? (
        <section className="cb-section" aria-labelledby="cb-first">
          <div className="cb-section__head">
            <h2 id="cb-first">First steps</h2>
            <p className="muted small">
              Three small things that earn points and show how the hub works. Done steps stay marked.
            </p>
          </div>
          <ol className="cb-steps">
            {FIRST_STEPS.map((s) => {
              const done = recent.some((e) => e.rule_id === s.rule);
              return (
                <li key={s.rule} className={done ? 'is-done' : ''}>
                  <span className="cb-steps__mark">{done ? 'Done' : 'To do'}</span>
                  <span className="cb-steps__text">
                    <span className="strong">{s.title}</span>
                    <span className="muted small">{s.detail}</span>
                  </span>
                  {!done ? (
                    <Link className="cb-way__go" to={s.to}>
                      {s.cta}
                      <Icon name="arrowRight" size={14} />
                    </Link>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </section>
      ) : null}

      <section className="cb-section" aria-labelledby="cb-ways">
        <div className="cb-section__head">
          <h2 id="cb-ways">
            Ways to earn{" "}
            <InfoTip label="How ways to earn work">
              Each way shows its points and its limit. Nothing is required. Limits
              stop any one person from farming a single area.
            </InfoTip>
          </h2>
          <p className="muted small">
            Pick what fits your work. Nothing here is required, and each limit is shown up front.
          </p>
        </div>
        <div className="cb-ways">
          {ways.map(({ id, rule }) => {
            const dim = (rule.dim as Dim) ?? 'quality';
            const cap = capText(rule);
            const start = START_AT[id];
            return (
              <article key={id} className="cb-way">
                <div className="cb-way__top">
                  <span className={`cb-way__dot ${DIM_DOT[dim] ?? ''}`} aria-hidden="true" />
                  <span className="cb-way__pts">+{fmtNum(Number(rule.points))}</span>
                </div>
                <h3 className="cb-way__title">{String(rule.label)}</h3>
                <p className="cb-way__when">{String(rule.when ?? '')}</p>
                <div className="cb-way__foot">
                  <span className="muted small">
                    {DIM_WHY[dim] ?? ''}
                    {cap ? ` · ${cap}` : ''}
                  </span>
                  {start ? (
                    <Link className="cb-way__go" to={start.to}>
                      {start.label}
                      <Icon name="arrowRight" size={14} />
                    </Link>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}
