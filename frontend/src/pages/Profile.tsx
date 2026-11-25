/** Person profile — mirrors idea-hub.html `viewPerson()`. */

import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { groupsApi } from '../api/groups';
import { profilesApi } from '../api/profiles';
import { recognitionApi } from '../api/recognition';
import { usersApi, type Team } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Avatar, Icon } from '../components/Icons';
import { DimBar } from '../components/ui/DimBar';
import { EmptyState } from '../components/ui/EmptyState';
import { Kpi } from '../components/ui/Kpi';
import { Pill } from '../components/ui/Pill';
import { TabsNav } from '../components/ui/TabsNav';
import { fmtDate, fmtNum } from '../constants/ideathons';
import { roleLabel, sortRoles } from '../constants/roles';
import { STATUS_META } from '../constants/status';
import type { Profile } from '../types/profile';
import type { RecognitionRules } from '../types/recognition';

const TABS = ['contributions', 'badges', 'ledger', 'recognition'] as const;
type TabId = (typeof TABS)[number];

const ROLE_ICON: Record<string, string> = {
  Author: 'edit',
  'Co-author': 'users',
  Owner: 'target',
  Contributor: 'hand',
  Collaborator: 'hand',
  Reviewer: 'checkcircle',
};

export function ProfilePage() {
  const { id = '' } = useParams();
  const [params, setParams] = useSearchParams();
  const { user: me } = useAuth();
  const navigate = useNavigate();
  const [dmBusy, setDmBusy] = useState(false);
  const [dmError, setDmError] = useState<string | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [rules, setRules] = useState<RecognitionRules | null>(null);
  const [team, setTeam] = useState<Team | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const tabParam = params.get('tab');
  const tab: TabId = TABS.includes(tabParam as TabId)
    ? (tabParam as TabId)
    : 'contributions';

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      profilesApi.get(id),
      recognitionApi.rules().catch(() => null),
      usersApi.teams().catch(() => [] as Team[]),
    ])
      .then(([p, r, teams]) => {
        if (cancelled) return;
        setProfile(p);
        setRules(r);
        const t = teams.find((x) => x.id === p.team_id) ?? null;
        setTeam(t);
      })
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
  }, [id]);

  const levelProgress = useMemo(() => {
    if (!profile) return { pct: 0, next: null as string | null, toNext: 0 };
    const pts = profile.points;
    const nextMin = profile.level.next_min;
    if (nextMin == null) return { pct: 100, next: null, toNext: 0 };
    const span = Math.max(1, nextMin - profile.level.min);
    const done = Math.max(0, pts - profile.level.min);
    return {
      pct: Math.min(100, Math.round((100 * done) / span)),
      next: null as string | null,
      toNext: Math.max(0, nextMin - pts),
    };
  }, [profile]);

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }
  if (loading || !profile) {
    return <p className="muted">Loading profile…</p>;
  }

  const self = profile.is_self || profile.user_id === me?.id;

  async function onMessage() {
    if (!profile) return;
    setDmBusy(true);
    setDmError(null);
    try {
      const dm = await groupsApi.openDm(profile.user_id);
      navigate(`/dms/${dm.id}`);
    } catch (e) {
      setDmError(e instanceof Error ? e.message : 'Could not open chat');
      setDmBusy(false);
    }
  }
  const name = profile.name || 'Unnamed member';
  const escrow = self
    ? profile.ledger.filter((r) => r.escrow)
    : [];
  const publicLedger = profile.ledger.filter((r) => !r.escrow);
  const earnedIds = new Set(profile.badges.map((b) => b.badge_id));
  const catalog = rules?.badges ?? [];

  let body: React.ReactNode = null;

  if (tab === 'contributions') {
    const tl = profile.history;
    body = (
      <div className="card">
        <div className="card__head">
          <h2>Contribution history</h2>
          <span className="muted small">
            {tl.length} entr{tl.length === 1 ? 'y' : 'ies'}, across every role
          </span>
        </div>
        {tl.length ? (
          <div className="timeline">
            {tl.map((e, i) => (
              <div className="timeline__item" key={`${e.idea_id}-${i}`}>
                <span className="timeline__dot">
                  <Icon name={ROLE_ICON[e.role] || 'user'} size={14} />
                </span>
                <div style={{ minWidth: 0, overflowWrap: 'anywhere' }}>
                  <div className="row" style={{ gap: 6 }}>
                    <Pill
                      variant={e.role === 'Reviewer' ? 'info' : 'brand'}
                    >
                      {e.role}
                    </Pill>
                    <Link className="strong" to={`/ideas/${e.idea_id}`}>
                      {e.idea_title || e.idea_id.slice(0, 8)}
                    </Link>
                  </div>
                  <div className="timeline__when">
                    {fmtDate(e.at, true)}
                    {e.extra ? ` · ${e.extra}` : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            icon="user"
            title="No contributions yet"
            body="Ideas this person writes, co-authors, owns, helps build or reviews will appear here."
          />
        )}
      </div>
    );
  } else if (tab === 'badges') {
    const rows =
      catalog.length > 0
        ? catalog.map((b) => ({
            id: b.id,
            name: b.name,
            icon: b.icon,
            rule: b.rule,
            earned: earnedIds.has(b.id),
            note:
              profile.badges.find((x) => x.badge_id === b.id)?.note ?? '',
          }))
        : profile.badges.map((b) => ({
            id: b.badge_id,
            name: b.name,
            icon: b.icon,
            rule: b.note || b.badge_id,
            earned: true,
            note: b.note,
          }));
    const n = rows.filter((x) => x.earned).length;
    body = (
      <div className="card">
        <div className="card__head">
          <h2>Badges</h2>
        </div>
        <p className="muted small" style={{ marginBottom: 'var(--space-3)' }}>
          {n} of {rows.length || n} earned. Badges are computed from the ledger
          and history.
        </p>
        {rows.length ? (
          <div className="grid grid-2">
            {rows.map((x) => (
              <div
                className={`badge-card ${x.earned ? 'badge-card--earned' : 'badge-card--locked'}`}
                key={x.id}
              >
                <span className="badge-ic">
                  <Icon name={x.earned ? x.icon || 'award' : 'lock'} size={18} />
                </span>
                <div>
                  <div className="strong">
                    {x.name}{' '}
                    {x.earned ? (
                      <Pill variant="gold">Earned</Pill>
                    ) : (
                      <Pill>Locked</Pill>
                    )}
                  </div>
                  <div className="muted small" style={{ marginTop: 2 }}>
                    {x.rule}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState icon="award" title="No badges yet" />
        )}
      </div>
    );
  } else if (tab === 'ledger') {
    body = (
      <div className="card">
        <div className="card__head">
          <h2>Points ledger</h2>
          <span className="muted small">
            {publicLedger.length} row{publicLedger.length === 1 ? '' : 's'} ·{' '}
            {fmtNum(profile.points)} points
          </span>
        </div>
        <p className="muted small" style={{ marginBottom: 8 }}>
          Append-only. Every row cites the rule that produced it.{' '}
          <Link to="/recognition?tab=how">See all rules</Link>.
          {self ? ' Escrowed points are shown separately above.' : ''}
        </p>
        {publicLedger.length ? (
          publicLedger.slice(0, 100).map((r) => (
            <div className="ledger-row" key={r.id}>
              <div className="muted">{fmtDate(r.created_at, true)}</div>
              <div className="pts">+{r.points}</div>
              <div>
                <Link className="strong" to="/recognition?tab=how">
                  {r.rule_label || r.rule_id}
                </Link>{' '}
                <span className="mono muted small">{r.rule_id}</span>
                {r.idea_id ? (
                  <div>
                    <Link to={`/ideas/${r.idea_id}`}>
                      Idea {r.idea_id.slice(0, 8)}…
                    </Link>
                  </div>
                ) : null}
                {r.note ? (
                  <div className="muted small">{r.note}</div>
                ) : null}
              </div>
            </div>
          ))
        ) : (
          <EmptyState
            icon="award"
            title="No points yet"
            body="Points appear when ideas are accepted, built, implemented or verified."
          />
        )}
      </div>
    );
  } else {
    body = (
      <div className="stack">
        {profile.badges.length ? (
          <div className="card">
            <div className="card__head">
              <h2>Recognised badges</h2>
            </div>
            {profile.badges.map((b) => (
              <div className="listrow" key={b.badge_id}>
                <div className="listrow__main">
                  <strong>{b.name}</strong>
                  <div className="muted small">{b.note}</div>
                </div>
                <Pill variant="gold" icon="award">
                  Earned
                </Pill>
              </div>
            ))}
          </div>
        ) : null}
        <div className="card">
          <div className="card__head">
            <h2>Idea lists</h2>
          </div>
          <div className="stack stack--sm">
            <h3 className="muted small">Submitted</h3>
            <IdeaRefs items={profile.submitted} />
            <h3 className="muted small">Co-authored</h3>
            <IdeaRefs items={profile.co_authored} />
            <h3 className="muted small">Implemented</h3>
            <IdeaRefs items={profile.implemented} />
          </div>
        </div>
        {!profile.badges.length ? (
          <div className="card">
            <EmptyState
              icon="award"
              title="No awards yet"
              body="Idea of the Quarter, the Annual Innovation Award and ideathon wins appear here."
            />
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className="stack stack--lg">
      <div className="card">
        <div className="profile-head">
          <Avatar name={name} avatar={1} size="lg" />
          <div className="grow" style={{ minWidth: 0 }}>
            <div className="eyebrow eyebrow--plain">
              {sortRoles(profile.roles).map(roleLabel).join(' · ') || 'Member'}
              {self ? ' · this is you' : ''}
            </div>
            <h1>{name}</h1>
            <p className="muted">
              {profile.title || '—'}
              {team ? (
                <>
                  {' '}
                  · <span>{team.name}</span>
                </>
              ) : null}
            </p>
            <div className="row" style={{ gap: 6 }} aria-label="Roles held">
              {sortRoles(profile.roles).map((r) => (
                <Pill
                  key={r}
                  variant={
                    self && me?.active_role === r ? 'brand' : undefined
                  }
                >
                  {roleLabel(r)}
                  {self && me?.active_role === r ? ' · working as' : ''}
                </Pill>
              ))}
            </div>
            <div className="row" style={{ marginTop: 8, gap: 8 }}>
              <Pill variant="gold" icon="award">
                {profile.level.name}
              </Pill>
              <span className="pts-chip">
                <Icon name="award" size={14} />
                {fmtNum(profile.points)}
              </span>
              {self ? null : (
                <button
                  type="button"
                  className="btn btn--sm"
                  disabled={dmBusy}
                  onClick={() => void onMessage()}
                >
                  <Icon name="message" size={14} /> Message
                </button>
              )}
            </div>
            {dmError ? (
              <div className="notice notice--danger" role="alert" style={{ marginTop: 8 }}>
                {dmError}
              </div>
            ) : null}
          </div>
          <div style={{ minWidth: 220, flex: 1, maxWidth: 340 }}>
            <div className="row row--between small">
              <span className="strong">{profile.level.name}</span>
              <span className="muted">
                {profile.level.next_min != null
                  ? `${levelProgress.toNext} points to next`
                  : 'Top level reached'}
              </span>
            </div>
            <div
              className="prog"
              role="img"
              aria-label={`${levelProgress.pct} percent of the way to the next level`}
              style={{ marginTop: 6 }}
            >
              <i style={{ width: `${levelProgress.pct}%` }} />
            </div>
            <DimBar dims={profile.dims} />
            <div className="muted small" style={{ marginTop: 4 }}>
              Quality {profile.dims.quality ?? 0} · Collaboration{' '}
              {profile.dims.collab ?? 0} · Delivery{' '}
              {profile.dims.delivery ?? 0} · Impact{' '}
              {profile.dims.impact ?? 0}
            </div>
          </div>
        </div>

        <div
          className="grid grid-5 kpi-row"
          style={{ marginTop: 'var(--space-5)' }}
        >
          <Kpi label="Ideas submitted" value={profile.submitted.length} />
          <Kpi label="Co-authored" value={profile.co_authored.length} />
          <Kpi
            label="Implemented"
            value={profile.implemented.length}
            sub="contributions credited"
          />
          <Kpi
            label="Hours saved"
            value={fmtNum(Math.round(profile.impact.hours_saved))}
            sub={
              profile.impact.hours_verified
                ? `per month (${fmtNum(Math.round(profile.impact.hours_verified))} verified)`
                : 'per month, by share'
            }
          />
          <Kpi
            label="Other impact"
            value={`$${fmtNum(Math.round(profile.impact.usd_influenced))}`}
            sub="cost avoided and revenue / month"
          />
        </div>
      </div>

      {escrow.length ? (
        <div className="escrow">
          <h3 style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Icon name="lock" size={18} /> Escrow: points held for your
            anonymous ideas
          </h3>
          <p className="small" style={{ margin: '6px 0 10px' }}>
            Only you can see this. These points are sealed: they are not in your
            total, any leaderboard, level or badge until you reveal and claim.
          </p>
          {escrow.map((x) => (
            <div
              className="listrow"
              style={{ borderColor: 'var(--gold)' }}
              key={x.id}
            >
              <div className="listrow__main">
                <span className="listrow__title">
                  {x.rule_label || x.rule_id}
                </span>
                <div className="muted small">{x.note || 'Escrowed points'}</div>
              </div>
              <span className="pts-chip">
                <Icon name="lock" size={12} />
                {x.points}
              </span>
            </div>
          ))}
        </div>
      ) : null}

      <TabsNav
        tabs={[
          {
            id: 'contributions',
            label: 'Contributions',
            href: `/people/${profile.user_id}`,
          },
          {
            id: 'badges',
            label: 'Badges',
            href: `/people/${profile.user_id}?tab=badges`,
            count: profile.badges.length || null,
          },
          {
            id: 'ledger',
            label: 'Points ledger',
            href: `/people/${profile.user_id}?tab=ledger`,
          },
          {
            id: 'recognition',
            label: 'Recognition',
            href: `/people/${profile.user_id}?tab=recognition`,
          },
        ]}
        active={tab}
        onSelect={(t) => {
          const next = new URLSearchParams(params);
          if (t === 'contributions') next.delete('tab');
          else next.set('tab', t);
          setParams(next);
        }}
      />
      {body}
    </div>
  );
}

function IdeaRefs({
  items,
}: {
  items: Array<{ id: string; title: string; status: string; role: string }>;
}) {
  if (!items.length) return <p className="muted small">None.</p>;
  return (
    <div>
      {items.map((i) => (
        <div className="listrow" key={`${i.id}-${i.role}`}>
          <div className="listrow__main">
            <Link className="listrow__title" to={`/ideas/${i.id}`}>
              {i.title}
            </Link>
            <div className="muted small">
              {STATUS_META[i.status as keyof typeof STATUS_META]?.label ??
                i.status}{' '}
              · {i.role}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ProfilePage;
