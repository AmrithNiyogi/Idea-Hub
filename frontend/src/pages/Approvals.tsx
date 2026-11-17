/**
 * Leadership Approvals inbox — `/approvals`.
 * Innovation-hour requests waiting for a decision (and recent decided).
 */

import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { deliveryApi } from '../api/delivery';
import { ideasApi } from '../api/ideas';
import { Icon } from '../components/Icons';
import type { HoursRequest, Pool } from '../types/delivery';
import type { Idea } from '../types/idea';

type Row = HoursRequest & { idea?: Idea | null };

export function ApprovalsPage() {
  const [pending, setPending] = useState<Row[]>([]);
  const [recent, setRecent] = useState<Row[]>([]);
  const [pool, setPool] = useState<Pool | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [pend, all] = await Promise.all([
        deliveryApi.listHoursRequests({ state: 'pending', limit: 50 }),
        deliveryApi.listHoursRequests({ limit: 40 }),
      ]);
      const ideaIds = [
        ...new Set([...pend, ...all].map((r) => r.idea_id)),
      ];
      const ideaMap = new Map<string, Idea>();
      await Promise.all(
        ideaIds.map(async (id) => {
          try {
            ideaMap.set(id, await ideasApi.get(id));
          } catch {
            /* idea may be gone */
          }
        }),
      );
      const withIdea = (r: HoursRequest): Row => ({
        ...r,
        idea: ideaMap.get(r.idea_id) ?? null,
      });
      setPending(pend.map(withIdea));
      setRecent(
        all
          .filter((r) => r.state !== 'pending')
          .slice(0, 12)
          .map(withIdea),
      );
      // Pool rides on any delivery detail; try first pending idea.
      const sampleId = pend[0]?.idea_id ?? all[0]?.idea_id;
      if (sampleId) {
        try {
          const d = await deliveryApi.get(sampleId);
          setPool(d.pool ?? null);
        } catch {
          setPool(null);
        }
      } else {
        setPool(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load approvals');
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const decide = async (req: HoursRequest, approve: boolean) => {
    let reason = '';
    if (!approve) {
      reason =
        window.prompt('Reason for declining (min 10 characters)') || '';
      if (reason.trim().length < 10) {
        setError('A reason of at least 10 characters is required to decline.');
        return;
      }
    }
    setBusy(req.id);
    setError(null);
    try {
      await deliveryApi.decideHours(req.id, {
        approve,
        hours: req.hours,
        reason,
      });
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Decision failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow">Leadership</div>
          <h1>Innovation hour approvals</h1>
          <p>
            Owners of accepted ideas ask for innovation time here. Approving
            starts the prototype. Declining needs a reason the owner can act on.
          </p>
        </div>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="layout-rail">
        <div className="stack">
          <div className="card">
            <div className="card__head">
              <h2>Waiting for a decision</h2>
              <span className="muted small">{pending.length}</span>
            </div>
            {pending.length === 0 ? (
              <div className="empty">
                <Icon name="checkcircle" size={28} />
                <h3>Nothing waiting</h3>
                <p className="muted">Every request has a decision.</p>
              </div>
            ) : (
              <div className="stack">
                {pending.map((r) => (
                  <div key={r.id} className="listrow">
                    <div className="listrow__main">
                      <Link
                        className="listrow__title"
                        to={`/ideas/${r.idea_id}?tab=delivery`}
                      >
                        {r.idea?.title ?? `Idea ${r.idea_id.slice(0, 8)}`}
                      </Link>
                      <div className="muted small">
                        {r.hours} h requested · {r.justification}
                      </div>
                      <div className="muted small">
                        {new Date(r.created_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="row">
                      <button
                        type="button"
                        className="btn btn--sm btn--primary"
                        disabled={busy === r.id}
                        onClick={() => void decide(r, true)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={busy === r.id}
                        onClick={() => void decide(r, false)}
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card__head">
              <h2>Recent decisions</h2>
            </div>
            {recent.length === 0 ? (
              <p className="muted small">No decisions yet.</p>
            ) : (
              <div className="stack">
                {recent.map((r) => (
                  <div key={r.id} className="listrow">
                    <div className="listrow__main">
                      <Link
                        className="listrow__title"
                        to={`/ideas/${r.idea_id}?tab=delivery`}
                      >
                        {r.idea?.title ?? `Idea ${r.idea_id.slice(0, 8)}`}
                      </Link>
                      <div className="muted small">
                        {r.state}
                        {r.granted_hours != null
                          ? ` · ${r.granted_hours} h granted`
                          : ` · ${r.hours} h`}
                        {r.reason ? ` · ${r.reason}` : ''}
                      </div>
                    </div>
                    <span className="pill">
                      {r.state === 'approved' ? 'Approved' : 'Declined'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="stack">
          <div className="card">
            <div className="card__head">
              <h2>Innovation pool</h2>
            </div>
            {pool ? (
              <>
                <div className="kpi__label">{pool.period_key}</div>
                <div className="kpi__value">{pool.remaining}</div>
                <p className="muted small">
                  of {pool.budget_hours} h remaining · {pool.granted_hours} h
                  granted
                </p>
              </>
            ) : (
              <p className="muted small">
                Pool appears once there is at least one hours request or delivery
                project.
              </p>
            )}
            <div className="row" style={{ marginTop: 12 }}>
              <Link className="btn btn--sm" to="/pipeline">
                Open pipeline
              </Link>
              <Link className="btn btn--sm" to="/agents">
                Agent approvals
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
