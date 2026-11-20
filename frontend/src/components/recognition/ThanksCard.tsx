/**
 * Written thanks: name what a teammate did. Earns them collaboration points.
 * Limits (3 a month, once per teammate per month) are enforced by the backend;
 * this form only checks the note length so people see the rule before sending.
 */
import { useState, type FormEvent } from 'react';
import { recognitionApi } from '../../api/recognition';
import type { User } from '../../types/auth';
import type { ThanksItem } from '../../types/recognition';
import { relTime } from '../../utils/format';

const MIN_LEN = 20;
const MAX_LEN = 280;

interface Props {
  me: User | null;
  people: Map<string, User>;
  recent: ThanksItem[];
  nameOf: (userId: string) => string;
  onSent: () => void;
}

export function ThanksCard({ me, people, recent, nameOf, onSent }: Props) {
  const options = [...people.values()]
    .filter((u) => u.id !== me?.id)
    .sort((a, b) => a.name.localeCompare(b.name));
  const [to, setTo] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSent(null);
    const text = note.trim();
    if (!to) {
      setError('Choose a teammate.');
      return;
    }
    if (text.length < MIN_LEN) {
      setError(`Write at least ${MIN_LEN} characters so the thanks says what it was for.`);
      return;
    }
    setBusy(true);
    try {
      await recognitionApi.sendThanks(to, text);
      setSent(`Thanks sent to ${nameOf(to)}.`);
      setNote('');
      setTo('');
      onSent();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not send thanks.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="cb-section" aria-labelledby="cb-thanks">
      <div className="cb-section__head">
        <h2 id="cb-thanks">Say thanks</h2>
        <p className="muted small">
          Name what a teammate did well. They earn 4 collaboration points. You
          can send 3 a month, and only one to each person.
        </p>
      </div>
      <div className="cb-thanks">
        <form className="cb-thanks__form" onSubmit={submit}>
          <label className="cb-thanks__label" htmlFor="cb-thanks-to">
            Teammate
          </label>
          <select
            id="cb-thanks-to"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            disabled={busy}
          >
            <option value="">Choose someone</option>
            {options.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
          </select>
          <label className="cb-thanks__label" htmlFor="cb-thanks-note">
            What they did
          </label>
          <textarea
            id="cb-thanks-note"
            rows={3}
            maxLength={MAX_LEN}
            value={note}
            onChange={(e) => setNote(e.target.value)}
            disabled={busy}
            placeholder="For example: reviewed my idea within a day and asked the question that made it stronger."
          />
          <div className="muted small">
            {note.trim().length}/{MAX_LEN} characters, at least {MIN_LEN}
          </div>
          {error ? (
            <p className="cb-thanks__error" role="alert">
              {error}
            </p>
          ) : null}
          {sent ? (
            <p className="cb-thanks__sent" role="status">
              {sent}
            </p>
          ) : null}
          <button type="submit" className="btn btn--primary" disabled={busy}>
            Send thanks
          </button>
        </form>

        <div className="cb-thanks__recent">
          <div className="eyebrow eyebrow--plain">Recent thanks</div>
          {recent.length ? (
            <ul className="cb-thanks__list">
              {recent.slice(0, 6).map((t) => (
                <li key={t.id}>
                  <span className="strong">{nameOf(t.from_user_id)}</span>
                  <span className="muted"> thanked </span>
                  <span className="strong">{nameOf(t.to_user_id)}</span>
                  <p>{t.note}</p>
                  <span className="muted small">{relTime(t.created_at)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted small">
              Nothing yet. Thank someone whose work helped you.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}
