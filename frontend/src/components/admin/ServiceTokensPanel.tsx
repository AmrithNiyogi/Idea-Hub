/**
 * Admin panel for service tokens: issue one for a Kompass tool or workflow, see its use, revoke it.
 * The token is shown once, right after it is created. It cannot be read again.
 */
import { useEffect, useState, type FormEvent } from 'react';
import { serviceTokensApi, type ServiceToken } from '../../api/serviceTokens';
import { useDialog } from '../DialogProvider';

const EXPIRY_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'Never' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
  { value: '365', label: '1 year' },
];

function when(iso: string | null): string {
  return iso ? new Date(iso).toLocaleString() : '–';
}

export function ServiceTokensPanel() {
  const dialog = useDialog();
  const [rows, setRows] = useState<ServiceToken[]>([]);
  const [name, setName] = useState('');
  const [expiry, setExpiry] = useState('');
  const [issued, setIssued] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setRows(await serviceTokensApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load service tokens.');
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await serviceTokensApi.create({
        name: name.trim(),
        expires_in_days: expiry ? Number(expiry) : null,
      });
      setIssued(res.token);
      setName('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create the token.');
    } finally {
      setBusy(false);
    }
  }

  async function onRevoke(row: ServiceToken) {
    if (
      !(await dialog.confirm({
        title: `Revoke "${row.name}"?`,
        message: 'Anything using it stops working immediately.',
        confirmLabel: 'Revoke',
        danger: true,
      }))
    ) {
      return;
    }
    setError(null);
    try {
      await serviceTokensApi.revoke(row.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not revoke the token.');
    }
  }

  async function copyIssued() {
    if (!issued) return;
    try {
      await navigator.clipboard.writeText(issued);
      setCopied(true);
    } catch {
      setError('Copy failed. Select the token and copy it by hand.');
    }
  }

  return (
    <section className="card stack" aria-label="Service tokens">
      <div>
        <div className="eyebrow eyebrow--plain">Service tokens</div>
        <p className="muted small">
          For Kompass tools and workflows that call the IdeaKonnekt. A token works on the agent read
          routes only, not on user routes. Revoke a token to stop it at once.
        </p>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          {error}
        </div>
      ) : null}

      <form className="stack" onSubmit={onCreate}>
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <div className="field" style={{ flex: '1 1 240px' }}>
            <label htmlFor="st-name">Name</label>
            <input
              className="input"
              id="st-name"
              maxLength={80}
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="For example: Kompass ideathon workflows"
              required
            />
          </div>
          <div className="field" style={{ flex: '0 1 160px' }}>
            <label htmlFor="st-expiry">Expires</label>
            <select
              className="select"
              id="st-expiry"
              value={expiry}
              onChange={(e) => setExpiry(e.target.value)}
            >
              {EXPIRY_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="row" style={{ justifyContent: 'flex-end' }}>
          <button className="btn btn--primary" type="submit" disabled={busy || !name.trim()}>
            {busy ? 'Creating…' : 'Create token'}
          </button>
        </div>
      </form>

      {issued ? (
        <div className="notice" role="status">
          <div>
            <strong>Copy this token now.</strong> It is shown once and cannot be read again.
          </div>
          <div className="row" style={{ gap: 8, marginTop: 8 }}>
            <input
              className="input"
              readOnly
              value={issued}
              aria-label="New service token"
              onFocus={(e) => e.currentTarget.select()}
            />
            <button className="btn" type="button" onClick={() => void copyIssued()}>
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        </div>
      ) : null}

      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Token</th>
              <th scope="col">Status</th>
              <th scope="col">Created</th>
              <th scope="col">Last used</th>
              <th scope="col">Expires</th>
              <th scope="col" aria-label="Actions" />
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="muted small">
                  No service tokens yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>
                    <code>{row.prefix}…</code>
                  </td>
                  <td>
                    <span className={`pill${row.status === 'active' ? ' pill--brand' : ''}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>{when(row.created_at)}</td>
                  <td>{when(row.last_used_at)}</td>
                  <td>{when(row.expires_at)}</td>
                  <td>
                    {row.status === 'active' ? (
                      <button className="btn btn--ghost" type="button" onClick={() => void onRevoke(row)}>
                        Revoke
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
