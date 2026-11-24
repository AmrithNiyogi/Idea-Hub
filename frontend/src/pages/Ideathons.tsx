/** Ideathons list — mirrors idea-hub.html `viewIdeathons()`. */

import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ideathonsApi } from '../api/ideathons';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { EmptyState } from '../components/ui/EmptyState';
import { Pill } from '../components/ui/Pill';
import {
  EVENT_KIND_LABEL,
  ORG_ROLES,
  fmtDate,
  ithPhaseIdx,
  ithStatus,
  ITH_PHASES,
} from '../constants/ideathons';
import type { IdeathonSummary } from '../types/ideathon';
import type { User } from '../types/auth';

function StatusPill({ it }: { it: IdeathonSummary }) {
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

function IdeathonCard({
  it,
  sponsorName,
}: {
  it: IdeathonSummary;
  sponsorName?: string;
}) {
  const blurb = it.challenges?.[0] || it.theme;
  return (
    <article className="card ith-card">
      <div className="row" style={{ gap: 6 }}>
        <StatusPill it={it} />
        <Pill icon={it.kind === 'hackathon' ? 'layers' : 'spark'}>
          {EVENT_KIND_LABEL[it.kind ?? 'ideathon']}
        </Pill>
        <Pill icon="flag">{it.theme}</Pill>
      </div>
      <h3>
        <Link to={`/ideathons/${it.id}`}>{it.title}</Link>
      </h3>
      <p className="muted clamp">{blurb}</p>
      <div className="ith-metrics">
        <span>
          <strong>{it.entry_count}</strong> entries
        </span>
        <span>
          <strong>{it.shortlist_count}</strong> shortlisted
        </span>
      </div>
      <div className="muted small">
        {fmtDate(it.start_at, true)} to {fmtDate(it.end_at, true)}
        {sponsorName ? ` · Sponsor ${sponsorName}` : ''}
      </div>
      <div className="row">
        <Link className="btn btn--sm btn--primary" to={`/ideathons/${it.id}`}>
          Open
        </Link>
      </div>
    </article>
  );
}

export function IdeathonsPage() {
  const { user } = useAuth();
  const [items, setItems] = useState<IdeathonSummary[]>([]);
  const [people, setPeople] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const isOrg = !!user && ORG_ROLES.includes(user.active_role as (typeof ORG_ROLES)[number]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [list, users] = await Promise.all([
          ideathonsApi.list(),
          usersApi.list().catch(() => [] as User[]),
        ]);
        if (!cancelled) {
          setItems(list);
          setPeople(users);
        }
      } catch (e) {
        if (!cancelled)
          setError(e instanceof Error ? e.message : 'Failed to load ideathons');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const nameOf = useMemo(() => {
    const m = new Map(people.map((u) => [u.id, u.name]));
    return (id: string) => m.get(id);
  }, [people]);

  const groups = useMemo(() => {
    const g: Record<'active' | 'upcoming' | 'past', IdeathonSummary[]> = {
      active: [],
      upcoming: [],
      past: [],
    };
    items.forEach((it) => g[ithStatus(it.start_at, it.end_at, it.completed_at)].push(it));
    const byStart = (a: IdeathonSummary, b: IdeathonSummary) =>
      new Date(a.start_at).getTime() - new Date(b.start_at).getTime();
    g.active.sort(byStart);
    g.upcoming.sort(byStart);
    g.past.sort(
      (a, b) => new Date(b.start_at).getTime() - new Date(a.start_at).getTime(),
    );
    return g;
  }, [items]);

  const section = (
    key: 'active' | 'upcoming' | 'past',
    title: string,
    blurb: string,
  ) => {
    const list = groups[key];
    if (!list.length) return null;
    return (
      <section key={key}>
        <div className="card__head" style={{ marginBottom: 'var(--space-3)' }}>
          <h2>{title}</h2>
          <span className="muted small">{blurb}</span>
        </div>
        <div className="grid grid-3">
          {list.map((it) => (
            <IdeathonCard
              key={it.id}
              it={it}
              sponsorName={nameOf(it.sponsor_id)}
            />
          ))}
        </div>
      </section>
    );
  };

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Campaigns</div>
          <h1>Ideathons</h1>
          <p>
            Time-boxed campaigns around a challenge. Entries are ordinary ideas
            tagged to the campaign, so they keep their full lifecycle, review
            and decision history.
          </p>
        </div>
        {isOrg ? (
          <Link className="btn btn--primary" to="/ideathons/new">
            <Icon name="plus" size={16} /> Create ideathon
          </Link>
        ) : null}
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? (
        <p className="muted">Loading campaigns…</p>
      ) : (
        <div className="stack" style={{ gap: 'var(--space-6)' }}>
          {section(
            'active',
            'Active',
            `${groups.active.length} campaign${groups.active.length === 1 ? '' : 's'}`,
          )}
          {section('upcoming', 'Upcoming', 'Not open for entries yet')}
          {section('past', 'Past', 'Results and handoffs')}
          {!items.length ? (
            <div className="card">
              <EmptyState
                icon="flag"
                title="No ideathons yet"
                body={
                  isOrg
                    ? 'Create the first campaign.'
                    : 'Leadership and administrators create ideathon campaigns.'
                }
                action={
                  isOrg ? (
                    <Link className="btn btn--primary" to="/ideathons/new">
                      Create ideathon
                    </Link>
                  ) : undefined
                }
              />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default IdeathonsPage;
