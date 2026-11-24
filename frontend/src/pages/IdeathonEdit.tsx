/** Edit ideathon — organiser edits to title, dates, and (while open) theme and challenges. */

import { useEffect, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { EventKindChips } from '../components/ideathon/EventKindChips';
import { ideathonsApi } from '../api/ideathons';
import { useAuth } from '../auth/AuthProvider';
import { Icon } from '../components/Icons';
import { ORG_ROLES } from '../constants/ideathons';
import type { EventKind, IdeathonDetail, IdeathonUpdateBody } from '../types/ideathon';

function toDateInput(iso: string): string {
  const d = new Date(iso);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function IdeathonEditPage() {
  const { id = '' } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [detail, setDetail] = useState<IdeathonDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [kind, setKind] = useState<EventKind>('ideathon');
  const [title, setTitle] = useState('');
  const [theme, setTheme] = useState('');
  const [challenges, setChallenges] = useState('');
  const [startAt, setStartAt] = useState('');
  const [endAt, setEndAt] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const isOrg =
    !!user && ORG_ROLES.includes(user.active_role as (typeof ORG_ROLES)[number]);

  useEffect(() => {
    let alive = true;
    ideathonsApi
      .get(id)
      .then((d) => {
        if (!alive) return;
        setDetail(d);
        setTitle(d.title);
        setKind(d.kind ?? 'ideathon');
        setTheme(d.theme);
        setChallenges(d.challenges.join('\n'));
        setStartAt(toDateInput(d.start_at));
        setEndAt(toDateInput(d.end_at));
      })
      .catch((err) => {
        if (alive) setLoadError(err instanceof Error ? err.message : 'Failed to load');
      });
    return () => {
      alive = false;
    };
  }, [id]);

  if (loadError) {
    return (
      <div className="card">
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={16} />
          <span>{loadError}</span>
        </div>
        <Link className="btn" to="/ideathons" style={{ marginTop: 12 }}>
          Back to Ideathons
        </Link>
      </div>
    );
  }

  if (!detail) {
    return <div className="card muted">Loading…</div>;
  }

  if (!isOrg) {
    return (
      <div className="card">
        <div className="notice notice--warn">
          <Icon name="lock" size={16} />
          <span>Only leadership and administrators can edit ideathons.</span>
        </div>
        <Link className="btn" to={`/ideathons/${id}`} style={{ marginTop: 12 }}>
          Back to ideathon
        </Link>
      </div>
    );
  }

  const completed = !!detail.completed_at || detail.phase === 'complete';
  const isOpen = detail.phase === 'open';

  if (completed) {
    return (
      <div className="card">
        <div className="notice notice--warn">
          <Icon name="lock" size={16} />
          <span>This ideathon is complete, so its details are locked.</span>
        </div>
        <Link className="btn" to={`/ideathons/${id}`} style={{ marginTop: 12 }}>
          Back to ideathon
        </Link>
      </div>
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!detail) return;
    setBusy(true);
    setError(null);
    const body: IdeathonUpdateBody = {
      title: title.trim(),
      start_at: new Date(`${startAt}T00:00:00`).toISOString(),
      end_at: new Date(`${endAt}T23:59:59`).toISOString(),
    };
    // Backend only accepts theme and challenges while the ideathon is open.
    if (isOpen) {
      body.kind = kind;
      body.theme = theme.trim();
      body.challenges = challenges
        .split('\n')
        .map((c) => c.trim())
        .filter(Boolean);
    }
    try {
      await ideathonsApi.update(id, body);
      nav(`/ideathons/${id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Edit campaign</div>
          <h1>Edit ideathon</h1>
          <p>
            Title and dates can change until the ideathon completes. Theme and
            challenges can change only while submissions are open. The sponsor
            is fixed once the ideathon is created.
          </p>
        </div>
        <Link className="btn btn--ghost" to={`/ideathons/${id}`}>
          Cancel
        </Link>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {!isOpen ? (
        <div className="notice notice--warn">
          <Icon name="lock" size={16} />
          <span>
            Submissions are closed, so the event type, theme and challenges are locked.
          </span>
        </div>
      ) : null}

      <form className="card stack" onSubmit={onSubmit} noValidate>
        <EventKindChips value={kind} onChange={setKind} disabled={busy || !isOpen} />
        <div className="field">
          <label htmlFor="ie-title">Name</label>
          <input
            className="input"
            id="ie-title"
            maxLength={80}
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="ie-theme">Theme</label>
          <input
            className="input"
            id="ie-theme"
            maxLength={60}
            value={theme}
            onChange={(e) => setTheme(e.target.value)}
            disabled={!isOpen}
            required
          />
        </div>
        <div className="field">
          <label htmlFor="ie-challenges">Challenge statements</label>
          <textarea
            className="textarea"
            id="ie-challenges"
            rows={5}
            value={challenges}
            onChange={(e) => setChallenges(e.target.value)}
            disabled={!isOpen}
            required
          />
          <div className="hint">
            One statement per line, up to three, 20 to 300 characters each.
          </div>
        </div>
        <div className="field">
          <label>Sponsor</label>
          <div className="muted small">Fixed after creation.</div>
        </div>
        <div className="sf-grid2">
          <div className="field">
            <label htmlFor="ie-start">Start date</label>
            <input
              className="input"
              type="date"
              id="ie-start"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="ie-end">End date</label>
            <input
              className="input"
              type="date"
              id="ie-end"
              value={endAt}
              onChange={(e) => setEndAt(e.target.value)}
              required
            />
          </div>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn--primary" type="submit" disabled={busy}>
            <Icon name="check" size={16} /> Save changes
          </button>
        </div>
      </form>
    </div>
  );
}

export default IdeathonEditPage;
