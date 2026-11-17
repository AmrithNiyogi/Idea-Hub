/** Create ideathon — mirrors idea-hub.html `viewIdeathonNew()` (form core). */

import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ideathonsApi } from '../api/ideathons';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { AgentBlock } from '../components/ui/AgentBlock';
import { ORG_ROLES } from '../constants/ideathons';
import type { User } from '../types/auth';

function toDateInput(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function IdeathonNewPage() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [sponsors, setSponsors] = useState<User[]>([]);
  const [title, setTitle] = useState('');
  const [theme, setTheme] = useState('');
  const [challenges, setChallenges] = useState('');
  const [sponsorId, setSponsorId] = useState('');
  const [startAt, setStartAt] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return toDateInput(d);
  });
  const [endAt, setEndAt] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 22);
    return toDateInput(d);
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isOrg =
    !!user && ORG_ROLES.includes(user.active_role as (typeof ORG_ROLES)[number]);

  useEffect(() => {
    usersApi
      .list()
      .then((all) => {
        const list = all
          .filter((u) =>
            u.roles.some((r) => r === 'leadership' || r === 'admin' || r === 'lead'),
          )
          .sort((a, b) => a.name.localeCompare(b.name));
        setSponsors(list);
        if (user && !sponsorId) setSponsorId(user.id);
      })
      .catch(() => setSponsors([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  if (!isOrg) {
    return (
      <div className="card">
        <div className="notice notice--warn">
          <Icon name="lock" size={16} />
          <span>Only leadership and administrators can create ideathons.</span>
        </div>
        <Link className="btn" to="/ideathons" style={{ marginTop: 12 }}>
          Back to Ideathons
        </Link>
      </div>
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const ch = challenges
        .split('\n')
        .map((c) => c.trim())
        .filter(Boolean);
      const res = await ideathonsApi.create({
        title: title.trim(),
        theme: theme.trim(),
        challenges: ch,
        sponsor_id: sponsorId,
        start_at: new Date(startAt).toISOString(),
        end_at: new Date(`${endAt}T23:59:59`).toISOString(),
      });
      nav(`/ideathons/${res.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">New campaign</div>
          <h1>Create an ideathon</h1>
          <p>
            Set the theme, the challenge and the dates. The Ideathon agent
            suggests wording; you decide what to use.
          </p>
        </div>
        <Link className="btn btn--ghost" to="/ideathons">
          Cancel
        </Link>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="ph5-two">
        <form className="card stack" onSubmit={onSubmit} noValidate>
          <div className="field">
            <label htmlFor="ic-title">Name</label>
            <input
              className="input"
              id="ic-title"
              maxLength={80}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="For example: Customers First Challenge"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="ic-theme">Theme</label>
            <input
              className="input"
              id="ic-theme"
              maxLength={60}
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              placeholder="A few words, for example: Delight the customer"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="ic-challenges">Challenge statements</label>
            <textarea
              className="textarea"
              id="ic-challenges"
              rows={5}
              value={challenges}
              onChange={(e) => setChallenges(e.target.value)}
              placeholder='One per line, up to three. Start with “How might we…”'
              required
            />
            <div className="hint">
              One statement per line, 20 to 300 characters each.
            </div>
          </div>
          <div className="field">
            <label htmlFor="ic-sponsor">Sponsor</label>
            <select
              className="select"
              id="ic-sponsor"
              value={sponsorId}
              onChange={(e) => setSponsorId(e.target.value)}
              required
            >
              {sponsors.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name}
                </option>
              ))}
            </select>
          </div>
          <div className="sf-grid2">
            <div className="field">
              <label htmlFor="ic-start">Start date</label>
              <input
                className="input"
                type="date"
                id="ic-start"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="ic-end">End date</label>
              <input
                className="input"
                type="date"
                id="ic-end"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button className="btn btn--primary" type="submit" disabled={busy}>
              <Icon name="flag" size={16} /> Create ideathon
            </button>
          </div>
        </form>

        <aside className="stack sticky">
          <AgentBlock
            agent="Ideathon"
            kind="Computed + templated"
            how="Theme ideas come from strategic themes and active tags. Challenge wording is templated from your theme text. Nothing is applied until you press Apply — edit freely in the form."
          >
            <p className="muted small">
              Type a theme and challenge statements on the left. Agent
              suggestions for the idea pool are available in the full prototype;
              this build uses the form you fill in.
            </p>
          </AgentBlock>
        </aside>
      </div>
    </div>
  );
}

export default IdeathonNewPage;
