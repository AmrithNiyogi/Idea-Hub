/** Admin — route `/admin`. Categories, people/roles, panels, SLAs, scoring, points, reset. */

import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import {
  adminApi,
  type AdminUser,
  type CategoryColorKey,
  type CategoryUpdateBody,
} from '../api/admin';
import { ApiError } from '../api/http';
import { usersApi } from '../api/users';
import { useAuth } from '../auth/AuthProvider';
import { ServiceTokensPanel } from '../components/admin/ServiceTokensPanel';
import { Icon } from '../components/Icons';
import { Pill } from '../components/ui/Pill';
import { ROLE_ORDER, roleLabel, sortRoles } from '../constants/roles';
import type { Role, User } from '../types/auth';
import type { AdminConfig } from '../types/phase456';
import { useDialog } from '../components/DialogProvider';

type Tab =
  | 'categories'
  | 'people'
  | 'panels'
  | 'scoring'
  | 'timelines'
  | 'points'
  | 'service-tokens'
  | 'data';

const COLOR_OPTIONS: Array<{ key: CategoryColorKey; label: string }> = [
  { key: 'tech', label: 'Blue' },
  { key: 'business', label: 'Teal' },
  { key: 'process', label: 'Slate' },
  { key: 'innovation', label: 'Magenta' },
  { key: 'amber', label: 'Amber' },
  { key: 'green', label: 'Green' },
  { key: 'violet', label: 'Violet' },
  { key: 'coral', label: 'Coral' },
];

function colorKeyFromCss(color: string): CategoryColorKey {
  const m = /^var\(--cat-([a-z]+)\)$/.exec(color.trim());
  if (m && COLOR_OPTIONS.some((o) => o.key === m[1])) {
    return m[1] as CategoryColorKey;
  }
  return 'amber';
}

function userLabel(u: User | undefined, id: string): string {
  return u ? u.name : id.slice(0, 8) + '…';
}

export function AdminPage() {
  const dialog = useDialog();
  const { user } = useAuth();
  const active = user?.active_role ?? user?.primary_role;
  const [tab, setTab] = useState<Tab>('categories');
  const [cfg, setCfg] = useState<AdminConfig | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [people, setPeople] = useState<AdminUser[]>([]);
  const [peopleQ, setPeopleQ] = useState('');
  const [addRoleSel, setAddRoleSel] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Add-category form
  const [newLabel, setNewLabel] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newColor, setNewColor] = useState<CategoryColorKey>('amber');
  const [newReviewer, setNewReviewer] = useState('');

  // Per-category edit drafts
  const [catDrafts, setCatDrafts] = useState<
    Record<
      string,
      { label: string; description: string; color_key: CategoryColorKey }
    >
  >({});

  // Panel add-member select values
  const [addMemberSel, setAddMemberSel] = useState<Record<string, string>>({});
  // Panel name drafts
  const [panelNameDrafts, setPanelNameDrafts] = useState<Record<string, string>>(
    {},
  );
  // Create-panel (orphan category) drafts
  const [orphanPanelName, setOrphanPanelName] = useState<Record<string, string>>(
    {},
  );
  const [orphanPanelReviewer, setOrphanPanelReviewer] = useState<
    Record<string, string>
  >({});
  // Add review panel (= new category + 1:1 panel)
  const [panelLabel, setPanelLabel] = useState('');
  const [panelDesc, setPanelDesc] = useState('');
  const [panelColor, setPanelColor] = useState<CategoryColorKey>('amber');
  const [panelCustomName, setPanelCustomName] = useState('');
  const [panelReviewer, setPanelReviewer] = useState('');

  /** People with the Reviewer role — HTML parity for panel seats / first reviewer. */
  const reviewers = useMemo(() => {
    const fromPeople = people.filter(
      (u) => u.is_active && u.roles.includes('reviewer'),
    );
    if (fromPeople.length) {
      return fromPeople.map((u) => ({
        id: u.id,
        name: u.name,
        title: u.title,
        email: u.email,
        roles: u.roles,
      }));
    }
    return users.filter((u) => u.roles.includes('reviewer'));
  }, [people, users]);

  const usersById = useMemo(() => {
    const m = new Map<string, User>();
    users.forEach((u) => m.set(u.id, u));
    // Prefer admin directory names when /users is empty or incomplete
    people.forEach((p) => {
      if (!m.has(p.id)) {
        m.set(p.id, {
          id: p.id,
          email: p.email,
          name: p.name,
          title: p.title,
          team_id: null,
          roles: p.roles,
          primary_role: p.primary_role,
          active_role: p.primary_role,
          status: p.status,
          avatar: 1,
          slug: p.id,
        });
      }
    });
    return m;
  }, [users, people]);

  const peopleFiltered = useMemo(() => {
    const q = peopleQ.trim().toLowerCase();
    const all = [...people].sort((a, b) => a.name.localeCompare(b.name));
    if (!q) return all;
    return all.filter((u) =>
      `${u.name} ${u.title} ${u.email}`.toLowerCase().includes(q),
    );
  }, [people, peopleQ]);

  const peopleShown = peopleFiltered.slice(0, 12);

  const reload = async () => {
    const [c, u, p] = await Promise.all([
      adminApi.config(),
      usersApi.list().catch(() => [] as User[]),
      adminApi.listUsers().catch(() => [] as AdminUser[]),
    ]);
    setCfg(c);
    setUsers(u);
    setPeople(p);
    const drafts: typeof catDrafts = {};
    c.categories.forEach((cat) => {
      drafts[cat.id] = {
        label: cat.label,
        description: cat.description,
        color_key: colorKeyFromCss(cat.color),
      };
    });
    setCatDrafts(drafts);
    const names: Record<string, string> = {};
    c.panels.forEach((p) => {
      names[p.id] = p.name;
    });
    setPanelNameDrafts(names);
  };

  useEffect(() => {
    reload().catch((e) =>
      setError(e instanceof Error ? e.message : 'Failed to load admin'),
    );
  }, []);

  // HTML prototype gates Admin to role `admin` only (not leadership).
  if (user && active !== 'admin') {
    return <Navigate to="/" replace />;
  }

  if (error) {
    return (
      <div className="notice notice--danger" role="alert">
        <Icon name="alert" size={18} />
        <span>{error}</span>
      </div>
    );
  }
  if (!cfg) return <p className="muted">Loading admin…</p>;

  const flash = (text: string) => {
    setMsg(text);
    setError(null);
  };

  const fail = (e: unknown) => {
    setMsg(null);
    setError(e instanceof Error ? e.message : 'Request failed');
  };

  const run = async (fn: () => Promise<void>, okMsg: string) => {
    setBusy(true);
    try {
      await fn();
      flash(okMsg);
      await reload();
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };

  const saveTimelines = () =>
    run(async () => {
      await adminApi.saveTimelines(cfg.timelines);
    }, 'Timelines saved');

  const saveScoring = () =>
    run(async () => {
      await adminApi.saveScoring(cfg.scoring);
    }, 'Scoring saved');

  const savePoints = () =>
    run(async () => {
      await adminApi.savePoints(cfg.point_overrides);
    }, 'Point values saved (future ledger rows only)');

  const reset = async () => {
    if (
      !(await dialog.confirm({
        title: 'Reset demo data?',
        message: 'All changes will be replaced by the original demo data.',
        confirmLabel: 'Reset',
        danger: true,
      }))
    )
      return;
    setBusy(true);
    try {
      const r = await adminApi.reset();
      flash(r.message);
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  };

  const onAddCategory = async (e: FormEvent) => {
    e.preventDefault();
    await run(async () => {
      await adminApi.createCategory({
        label: newLabel.trim(),
        description: newDesc.trim(),
        color_key: newColor,
        reviewer_id: newReviewer,
      });
      setNewLabel('');
      setNewDesc('');
      setNewColor('amber');
      setNewReviewer('');
    }, 'Category added. It is now open on Submit and has its own review panel.');
  };

  const onAddReviewPanel = async (e: FormEvent) => {
    e.preventDefault();
    await run(async () => {
      const cat = await adminApi.createCategory({
        label: panelLabel.trim(),
        description: panelDesc.trim(),
        color_key: panelColor,
        reviewer_id: panelReviewer,
      });
      const custom = panelCustomName.trim();
      if (custom) {
        const snap = await adminApi.config();
        const panel = snap.panels.find((p) => p.category_id === cat.id);
        if (panel && panel.name !== custom) {
          await adminApi.updatePanel(panel.id, { name: custom });
        }
      }
      setPanelLabel('');
      setPanelDesc('');
      setPanelColor('amber');
      setPanelCustomName('');
      setPanelReviewer('');
    }, 'Review panel created. It appears in the review queue for that category.');
  };

  const saveCategory = (id: string) =>
    run(async () => {
      const d = catDrafts[id];
      if (!d) return;
      const body: CategoryUpdateBody = {
        label: d.label.trim(),
        description: d.description.trim(),
        color_key: d.color_key,
      };
      await adminApi.updateCategory(id, body);
    }, 'Category saved.');

  const toggleCategory = (id: string, enabled: boolean) =>
    run(async () => {
      await adminApi.updateCategory(id, { enabled: !enabled });
    }, enabled ? 'Category disabled. It no longer appears on Submit.' : 'Category enabled. It is back on the Submit form.');

  const tabs: Array<[Tab, string]> = [
    ['categories', 'Categories'],
    ['people', 'People and roles'],
    ['panels', 'Review panels'],
    ['scoring', 'Scoring'],
    ['timelines', 'Timelines'],
    ['points', 'Points'],
    ['service-tokens', 'Service tokens'],
    ['data', 'Data'],
  ];

  const scoringTotal = cfg.scoring.reduce((a, c) => a + Number(c.weight || 0), 0);

  const addRole = (userId: string) => {
    const role = addRoleSel[userId] as Role | undefined;
    if (!role) return;
    void run(async () => {
      await adminApi.addUserRole(userId, role);
      setAddRoleSel((prev) => ({ ...prev, [userId]: '' }));
    }, `${roleLabel(role)} role added.`);
  };

  const setDefaultRole = (userId: string, role: Role) =>
    run(async () => {
      await adminApi.setUserPrimaryRole(userId, role);
    }, `${roleLabel(role)} is now the default role.`);

  const removeRole = (target: AdminUser, role: Role) =>
    run(async () => {
      try {
        await adminApi.removeUserRole(target.id, role, false);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          const detail = (
            e.body as {
              detail?: { needs_confirm?: boolean; panels?: string[] };
            }
          )?.detail;
          if (detail?.needs_confirm) {
            const panels = (detail.panels || []).join(', ');
            const ok = await dialog.confirm({
              title: 'Remove the Reviewer role?',
              message: `${target.name} will also be removed from these review panels: ${panels}. Ideas already in their queue stay with the panel.`,
              confirmLabel: 'Remove role',
              danger: true,
            });
            if (!ok) return;
            await adminApi.removeUserRole(target.id, role, true);
            return;
          }
        }
        throw e;
      }
    }, `${roleLabel(role)} role removed from ${target.name}.`);

  const toggleActive = async (target: AdminUser) => {
    if (user?.id === target.id) {
      fail(new Error('You cannot disable or enable your own account.'));
      return;
    }
    if (target.is_active) {
      const ok = await dialog.confirm({
        title: `Disable ${target.name}?`,
        message: `${target.email}\n\nThey will not be able to sign in (password or Microsoft SSO) until re-enabled.`,
        confirmLabel: 'Disable',
        danger: true,
      });
      if (!ok) return;
      void run(async () => {
        await adminApi.disableUser(target.id);
      }, `${target.name} disabled.`);
      return;
    }
    void run(async () => {
      await adminApi.enableUser(target.id);
    }, `${target.name} enabled.`);
  };

  const deleteAccount = async (target: AdminUser) => {
    if (user?.id === target.id) {
      fail(new Error('You cannot delete your own account.'));
      return;
    }
    // The dialog only enables Delete once the email is typed correctly.
    const ok = await dialog.confirm({
      title: `Delete ${target.name} permanently?`,
      message: 'This cannot be undone.',
      requireText: target.email,
      confirmLabel: 'Delete',
      danger: true,
    });
    if (!ok) return;
    void run(async () => {
      try {
        await adminApi.deleteUser(target.id, false);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          const detail = (
            e.body as {
              detail?: { needs_confirm?: boolean; panels?: string[]; message?: string };
            }
          )?.detail;
          if (detail?.needs_confirm) {
            const panels = (detail.panels || []).join(', ');
            const ok = await dialog.confirm({
              title: `Delete ${target.name}?`,
              message: `They will also be removed from these review panels: ${panels}.`,
              confirmLabel: 'Delete',
              danger: true,
            });
            if (!ok) return;
            await adminApi.deleteUser(target.id, true);
            return;
          }
        }
        throw e;
      }
    }, `${target.name} (${target.email}) deleted.`);
  };

  return (
    <div className="stack stack--lg page admin">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">Administration</div>
          <h1>Admin</h1>
          <p>
            Configure the platform. Every change is validated and applied at
            once.
          </p>
        </div>
      </div>

      <div className="tabs" role="tablist" aria-label="Admin sections">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {msg ? (
        <div className="notice notice--ok">
          <Icon name="check" size={16} />
          <span>{msg}</span>
        </div>
      ) : null}

      {tab === 'service-tokens' ? <ServiceTokensPanel /> : null}

      {tab === 'people' ? (
        <div className="stack">
          <div className="notice">
            <Icon name="info" size={16} />
            <span>
              A person holds one or more roles and signs in for one of them.
              Permissions follow the role they are working in, not all roles at
              once. Everyone keeps at least one role, there is always one active
              administrator, and the last reviewer on a panel cannot be removed.
              Disable blocks sign-in; Delete permanently removes the account.
            </span>
          </div>
          <div className="card">
            <div className="card__head">
              <h2>People and roles</h2>
            </div>
            <div
              className="field"
              style={{ maxWidth: 420, marginBottom: 'var(--space-3)' }}
            >
              <label htmlFor="adm-people-q">Search people</label>
              <input
                className="input"
                id="adm-people-q"
                type="search"
                value={peopleQ}
                placeholder="Name or title"
                autoComplete="off"
                onChange={(e) => setPeopleQ(e.target.value)}
              />
            </div>
            {!peopleShown.length ? (
              <p className="muted">
                {peopleQ.trim()
                  ? `No one matches “${peopleQ.trim()}”.`
                  : 'No users found.'}
              </p>
            ) : (
              peopleShown.map((u) => {
                const held = sortRoles(u.roles);
                const free = ROLE_ORDER.filter((r) => !held.includes(r));
                return (
                  <div
                    key={u.id}
                    className="listrow"
                    style={{
                      alignItems: 'flex-start',
                      flexWrap: 'wrap',
                    }}
                  >
                    <div
                      className="listrow__main"
                      style={{ minWidth: 220 }}
                    >
                      <Link className="listrow__title" to={`/people/${u.id}`}>
                        {u.name}
                      </Link>
                      <div className="muted small">
                        {u.email}
                        {u.title ? ` · ${u.title}` : ''}
                        {!u.is_active ? (
                          <>
                            {' · '}
                            <Pill variant="warning">Disabled</Pill>
                          </>
                        ) : null}
                      </div>
                      <div
                        className="row"
                        style={{ gap: 8, marginTop: 8, flexWrap: 'wrap' }}
                      >
                        {held.map((r) => (
                          <span
                            key={r}
                            className="row"
                            style={{ gap: 2 }}
                          >
                            <Pill
                              variant={
                                r === u.primary_role ? 'brand' : ''
                              }
                            >
                              {roleLabel(r)}
                              {r === u.primary_role ? ' · default' : ''}
                            </Pill>
                            {r !== u.primary_role ? (
                              <button
                                type="button"
                                className="btn btn--sm btn--ghost"
                                disabled={busy}
                                aria-label={`Make ${roleLabel(r)} the default role of ${u.name}`}
                                onClick={() =>
                                  void setDefaultRole(u.id, r)
                                }
                              >
                                Make default
                              </button>
                            ) : null}
                            <button
                              type="button"
                              className="btn btn--sm btn--ghost"
                              disabled={busy}
                              aria-label={`Remove the ${roleLabel(r)} role from ${u.name}`}
                              onClick={() => void removeRole(u, r)}
                            >
                              <Icon name="x" size={12} />
                            </button>
                          </span>
                        ))}
                      </div>
                    </div>
                    <div
                      className="row"
                      style={{ gap: 6, flexWrap: 'wrap', alignItems: 'center' }}
                    >
                      <label className="sr-only" htmlFor={`rl-add-${u.id}`}>
                        Add a role for {u.name}
                      </label>
                      <select
                        className="select"
                        id={`rl-add-${u.id}`}
                        style={{ width: 'auto' }}
                        disabled={!free.length || busy}
                        value={addRoleSel[u.id] || ''}
                        onChange={(e) =>
                          setAddRoleSel({
                            ...addRoleSel,
                            [u.id]: e.target.value,
                          })
                        }
                      >
                        <option value="">
                          {free.length ? 'Add a role' : 'Holds every role'}
                        </option>
                        {free.map((r) => (
                          <option key={r} value={r}>
                            {roleLabel(r)}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        className="btn btn--sm btn--primary"
                        disabled={busy || !addRoleSel[u.id]}
                        onClick={() => addRole(u.id)}
                      >
                        <Icon name="plus" size={14} /> Add
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={busy || user?.id === u.id}
                        aria-label={
                          u.is_active
                            ? `Disable ${u.name}`
                            : `Enable ${u.name}`
                        }
                        onClick={() => toggleActive(u)}
                      >
                        {u.is_active ? 'Disable' : 'Enable'}
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--danger"
                        disabled={busy || user?.id === u.id}
                        aria-label={`Delete ${u.name}`}
                        onClick={() => deleteAccount(u)}
                      >
                        <Icon name="trash" size={14} /> Delete
                      </button>
                    </div>
                  </div>
                );
              })
            )}
            <p className="muted small" style={{ marginTop: 8 }}>
              {peopleFiltered.length > peopleShown.length
                ? `Showing ${peopleShown.length} of ${peopleFiltered.length} people. Search to narrow the list.`
                : `${peopleFiltered.length} ${peopleFiltered.length === 1 ? 'person' : 'people'}`}
            </p>
          </div>
        </div>
      ) : null}

      {tab === 'categories' ? (
        <div className="stack">
          <div className="notice">
            <Icon name="info" size={16} />
            <span>
              A disabled category disappears from the Submit form. Ideas already
              in it keep their label and stay in their review queue. At least
              one category must stay enabled.
            </span>
          </div>

          {cfg.categories.map((c) => {
            const draft = catDrafts[c.id] ?? {
              label: c.label,
              description: c.description,
              color_key: colorKeyFromCss(c.color),
            };
            return (
              <form
                key={c.id}
                className="card"
                onSubmit={(e) => {
                  e.preventDefault();
                  void saveCategory(c.id);
                }}
                aria-label={`Edit category ${c.label}`}
              >
                <div className="card__head">
                  <h3>
                    <span
                      className="cat-swatch"
                      style={{ background: c.color }}
                    />
                    {c.label}{' '}
                    <span className="muted small mono">({c.slug})</span>
                  </h3>
                  <div className="row" style={{ gap: 6 }}>
                    <span
                      className={`pill${c.enabled ? ' pill--success' : ' pill--warning'}`}
                    >
                      {c.enabled ? 'Open for new ideas' : 'Disabled'}
                    </span>
                  </div>
                </div>
                <div className="adm-row">
                  <div className="field">
                    <label htmlFor={`ce-${c.id}-label`}>Name</label>
                    <input
                      className="input"
                      id={`ce-${c.id}-label`}
                      maxLength={40}
                      value={draft.label}
                      onChange={(e) =>
                        setCatDrafts({
                          ...catDrafts,
                          [c.id]: { ...draft, label: e.target.value },
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`ce-${c.id}-description`}>
                      Description (shown on Submit)
                    </label>
                    <input
                      className="input"
                      id={`ce-${c.id}-description`}
                      maxLength={160}
                      value={draft.description}
                      onChange={(e) =>
                        setCatDrafts({
                          ...catDrafts,
                          [c.id]: { ...draft, description: e.target.value },
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`ce-${c.id}-color`}>Colour</label>
                    <select
                      className="select"
                      id={`ce-${c.id}-color`}
                      value={draft.color_key}
                      onChange={(e) =>
                        setCatDrafts({
                          ...catDrafts,
                          [c.id]: {
                            ...draft,
                            color_key: e.target.value as CategoryColorKey,
                          },
                        })
                      }
                    >
                      {COLOR_OPTIONS.map((o) => (
                        <option key={o.key} value={o.key}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="row" style={{ paddingBottom: 2, gap: 6 }}>
                    <button
                      className="btn btn--primary btn--sm"
                      type="submit"
                      disabled={busy}
                    >
                      Save
                    </button>
                    <button
                      className="btn btn--sm"
                      type="button"
                      disabled={busy}
                      onClick={() => void toggleCategory(c.id, c.enabled)}
                    >
                      {c.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </div>
              </form>
            );
          })}

          <form
            className="card"
            onSubmit={(e) => void onAddCategory(e)}
            aria-label="Add a category"
          >
            <div className="card__head">
              <h3>Add a category</h3>
            </div>
            <p className="muted small" style={{ marginBottom: 10 }}>
              A new category gets its own review panel, starting with the
              reviewer you choose.
            </p>
            <div
              className="adm-row"
              style={{
                gridTemplateColumns:
                  'minmax(0,1fr) minmax(0,1.3fr) 140px minmax(0,1fr) auto',
              }}
            >
              <div className="field">
                <label htmlFor="ca-label">Name</label>
                <input
                  className="input"
                  id="ca-label"
                  maxLength={40}
                  required
                  value={newLabel}
                  onChange={(e) => setNewLabel(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="ca-description">Description</label>
                <input
                  className="input"
                  id="ca-description"
                  maxLength={160}
                  required
                  minLength={10}
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="ca-color">Colour</label>
                <select
                  className="select"
                  id="ca-color"
                  value={newColor}
                  onChange={(e) =>
                    setNewColor(e.target.value as CategoryColorKey)
                  }
                >
                  {COLOR_OPTIONS.map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="ca-reviewer">First reviewer</label>
                <select
                  className="select"
                  id="ca-reviewer"
                  required
                  value={newReviewer}
                  onChange={(e) => setNewReviewer(e.target.value)}
                >
                  <option value="">Choose a reviewer</option>
                  {reviewers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <button
                  className="btn btn--primary btn--sm"
                  type="submit"
                  disabled={busy || !newReviewer}
                >
                  <Icon name="plus" size={14} /> Add category
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      {tab === 'panels' ? (
        <div className="stack">
          <div className="notice">
            <Icon name="info" size={16} />
            <span>
              Each category has one review panel. Changes take effect in the
              review queue immediately. Only people who hold the Reviewer role
              can sit on a panel — grant that role in{' '}
              <button
                type="button"
                className="linkish"
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  color: 'var(--brand)',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  font: 'inherit',
                }}
                onClick={() => setTab('people')}
              >
                People and roles
              </button>
              . A panel needs at least one reviewer.
            </span>
          </div>
          {!reviewers.length ? (
            <div className="notice notice--warning" role="status">
              <Icon name="alert" size={16} />
              <span>
                No one has the Reviewer role yet. Add it under People and roles
                before creating or staffing a panel.
              </span>
            </div>
          ) : null}
          {cfg.categories.map((c) => {
            const panel = cfg.panels.find((p) => p.category_id === c.id);
            if (!panel) {
              const draftName =
                orphanPanelName[c.id] ?? `${c.label} review panel`;
              const draftRev = orphanPanelReviewer[c.id] || '';
              return (
                <div key={c.id} className="card">
                  <div className="card__head">
                    <h3>
                      <span
                        className="cat-swatch"
                        style={{ background: c.color }}
                      />
                      {c.label}
                    </h3>
                    <span className="muted small">No panel yet</span>
                  </div>
                  <p className="muted small" style={{ marginBottom: 10 }}>
                    This category is missing its review panel. Choose a name and
                    first reviewer to create it.
                  </p>
                  <div
                    className="adm-row"
                    style={{
                      gridTemplateColumns:
                        'minmax(0,1.4fr) minmax(0,1fr) auto',
                    }}
                  >
                    <div className="field">
                      <label htmlFor={`pn-orphan-name-${c.id}`}>
                        Panel name
                      </label>
                      <input
                        className="input"
                        id={`pn-orphan-name-${c.id}`}
                        maxLength={160}
                        value={draftName}
                        onChange={(e) =>
                          setOrphanPanelName({
                            ...orphanPanelName,
                            [c.id]: e.target.value,
                          })
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor={`pn-orphan-rev-${c.id}`}>
                        First reviewer
                      </label>
                      <select
                        className="select"
                        id={`pn-orphan-rev-${c.id}`}
                        required
                        disabled={!reviewers.length || busy}
                        value={draftRev}
                        onChange={(e) =>
                          setOrphanPanelReviewer({
                            ...orphanPanelReviewer,
                            [c.id]: e.target.value,
                          })
                        }
                      >
                        <option value="">Choose a reviewer</option>
                        {reviewers.map((u) => (
                          <option key={u.id} value={u.id}>
                            {u.name}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="row" style={{ paddingBottom: 2 }}>
                      <button
                        type="button"
                        className="btn btn--primary btn--sm"
                        disabled={
                          busy ||
                          !draftRev ||
                          !draftName.trim() ||
                          !reviewers.length
                        }
                        onClick={() =>
                          void run(async () => {
                            await adminApi.createPanel({
                              category_id: c.id,
                              name: draftName.trim(),
                              member_ids: [draftRev],
                              chair_id: draftRev,
                            });
                            setOrphanPanelName((prev) => {
                              const next = { ...prev };
                              delete next[c.id];
                              return next;
                            });
                            setOrphanPanelReviewer((prev) => {
                              const next = { ...prev };
                              delete next[c.id];
                              return next;
                            });
                          }, 'Panel created.')
                        }
                      >
                        <Icon name="plus" size={14} /> Create panel
                      </button>
                    </div>
                  </div>
                </div>
              );
            }
            const memberSet = new Set(panel.member_ids);
            const candidates = reviewers.filter((u) => !memberSet.has(u.id));
            const nameDraft = panelNameDrafts[panel.id] ?? panel.name;
            return (
              <div key={c.id} className="card">
                <div className="card__head">
                  <h3>
                    <span
                      className="cat-swatch"
                      style={{ background: c.color }}
                    />
                    {c.label}{' '}
                    <span className="muted small">{panel.name}</span>
                  </h3>
                  <span className="muted small">
                    {panel.member_ids.length} reviewer
                    {panel.member_ids.length === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="adm-row" style={{ marginBottom: 12 }}>
                  <div className="field" style={{ gridColumn: '1 / -2' }}>
                    <label htmlFor={`pn-name-${panel.id}`}>Panel name</label>
                    <input
                      className="input"
                      id={`pn-name-${panel.id}`}
                      value={nameDraft}
                      onChange={(e) =>
                        setPanelNameDrafts({
                          ...panelNameDrafts,
                          [panel.id]: e.target.value,
                        })
                      }
                    />
                  </div>
                  <div className="row" style={{ paddingBottom: 2 }}>
                    <button
                      type="button"
                      className="btn btn--sm btn--primary"
                      disabled={busy || nameDraft.trim() === panel.name}
                      onClick={() =>
                        void run(async () => {
                          await adminApi.updatePanel(panel.id, {
                            name: nameDraft.trim(),
                          });
                        }, 'Panel name saved.')
                      }
                    >
                      Save name
                    </button>
                  </div>
                </div>
                <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                  {panel.member_ids.map((uid) => {
                    const u = usersById.get(uid);
                    const isChair = panel.chair_id === uid;
                    return (
                      <li key={uid} className="listrow">
                        <div className="listrow__main">
                          <span className="listrow__title">
                            {userLabel(u, uid)}
                          </span>
                          <div className="muted small">
                            {u?.title || 'Reviewer'}
                          </div>
                        </div>
                        {isChair ? (
                          <span className="pill pill--brand">Chair</span>
                        ) : (
                          <button
                            type="button"
                            className="btn btn--sm"
                            disabled={busy}
                            onClick={() =>
                              void run(async () => {
                                await adminApi.setPanelChair(panel.id, uid);
                              }, 'Chair changed.')
                            }
                          >
                            Make chair
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn--sm btn--danger"
                          disabled={busy || panel.member_ids.length <= 1}
                          aria-label={`Remove ${userLabel(u, uid)} from ${panel.name}`}
                          onClick={() =>
                            void run(async () => {
                              await adminApi.removePanelMember(panel.id, uid);
                            }, 'Reviewer removed from the panel.')
                          }
                        >
                          <Icon name="trash" size={14} /> Remove
                        </button>
                      </li>
                    );
                  })}
                </ul>
                <div className="inline-form">
                  <div className="field" style={{ flex: '1 1 220px' }}>
                    <label htmlFor={`pn-add-${panel.id}`}>Add a reviewer</label>
                    <select
                      className="select"
                      id={`pn-add-${panel.id}`}
                      disabled={!candidates.length || busy}
                      value={addMemberSel[panel.id] || ''}
                      onChange={(e) =>
                        setAddMemberSel({
                          ...addMemberSel,
                          [panel.id]: e.target.value,
                        })
                      }
                    >
                      <option value="">
                        {candidates.length
                          ? 'Choose a reviewer'
                          : 'Every reviewer is already on this panel'}
                      </option>
                      {candidates.map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    style={{ alignSelf: 'flex-end' }}
                    disabled={busy || !addMemberSel[panel.id]}
                    onClick={() =>
                      void run(async () => {
                        const uid = addMemberSel[panel.id];
                        if (!uid) return;
                        await adminApi.addPanelMember(panel.id, uid);
                        setAddMemberSel({ ...addMemberSel, [panel.id]: '' });
                      }, 'Reviewer added. They see this panel’s queue now.')
                    }
                  >
                    <Icon name="plus" size={14} /> Add
                  </button>
                </div>
              </div>
            );
          })}

          <form
            className="card"
            onSubmit={(e) => void onAddReviewPanel(e)}
            aria-label="Add a review panel"
          >
            <div className="card__head">
              <h3>Add a review panel</h3>
            </div>
            <p className="muted small" style={{ marginBottom: 10 }}>
              Creates a new category and its dedicated review panel (one panel
              per category). The first reviewer becomes chair.
            </p>
            <div
              className="adm-row"
              style={{
                gridTemplateColumns:
                  'minmax(0,1fr) minmax(0,1.2fr) 140px minmax(0,1fr) minmax(0,1fr) auto',
              }}
            >
              <div className="field">
                <label htmlFor="pn-new-label">Category name</label>
                <input
                  className="input"
                  id="pn-new-label"
                  maxLength={40}
                  required
                  value={panelLabel}
                  onChange={(e) => setPanelLabel(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="pn-new-desc">Description</label>
                <input
                  className="input"
                  id="pn-new-desc"
                  maxLength={160}
                  required
                  minLength={10}
                  value={panelDesc}
                  onChange={(e) => setPanelDesc(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="pn-new-color">Colour</label>
                <select
                  className="select"
                  id="pn-new-color"
                  value={panelColor}
                  onChange={(e) =>
                    setPanelColor(e.target.value as CategoryColorKey)
                  }
                >
                  {COLOR_OPTIONS.map((o) => (
                    <option key={o.key} value={o.key}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="pn-new-name">Panel name (optional)</label>
                <input
                  className="input"
                  id="pn-new-name"
                  maxLength={160}
                  placeholder="Defaults to “{category} review panel”"
                  value={panelCustomName}
                  onChange={(e) => setPanelCustomName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="pn-new-reviewer">First reviewer</label>
                <select
                  className="select"
                  id="pn-new-reviewer"
                  required
                  value={panelReviewer}
                  onChange={(e) => setPanelReviewer(e.target.value)}
                >
                  <option value="">Choose a reviewer</option>
                  {reviewers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <button
                  className="btn btn--primary btn--sm"
                  type="submit"
                  disabled={busy || !panelReviewer || !reviewers.length}
                >
                  <Icon name="plus" size={14} /> Add panel
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      {tab === 'scoring' ? (
        <section className="card">
          <div className="card__head">
            <h2>Scoring criteria</h2>
            <span className="pill" role="status">
              Weights total {scoringTotal}
            </span>
          </div>
          <p className="muted" style={{ marginBottom: 6 }}>
            Reviewers score each criterion from 1 to 5. Weights must sum to 100.
          </p>
          {cfg.scoring.map((c, i) => (
            <div key={c.key} className="crit-row">
              <div>
                <strong>{c.label || c.key}</strong>
                <div className="muted small">Criterion key: {c.key}</div>
              </div>
              <div className="field">
                <label htmlFor={`sc-${c.key}-label`}>Label</label>
                <input
                  id={`sc-${c.key}-label`}
                  className="input"
                  value={c.label}
                  onChange={(e) => {
                    const next = [...cfg.scoring];
                    next[i] = { ...c, label: e.target.value };
                    setCfg({ ...cfg, scoring: next });
                  }}
                />
              </div>
              <div className="stack stack--sm">
                <div className="field">
                  <label htmlFor={`sc-${c.key}-low`}>Help text for score 1</label>
                  <input
                    id={`sc-${c.key}-low`}
                    className="input"
                    value={c.low}
                    onChange={(e) => {
                      const next = [...cfg.scoring];
                      next[i] = { ...c, low: e.target.value };
                      setCfg({ ...cfg, scoring: next });
                    }}
                  />
                </div>
                <div className="field">
                  <label htmlFor={`sc-${c.key}-high`}>
                    Help text for score 5
                  </label>
                  <input
                    id={`sc-${c.key}-high`}
                    className="input"
                    value={c.high}
                    onChange={(e) => {
                      const next = [...cfg.scoring];
                      next[i] = { ...c, high: e.target.value };
                      setCfg({ ...cfg, scoring: next });
                    }}
                  />
                </div>
              </div>
              <div className="field">
                <label htmlFor={`sc-${c.key}-weight`}>Weight %</label>
                <input
                  id={`sc-${c.key}-weight`}
                  className="input num-in"
                  type="number"
                  value={c.weight}
                  onChange={(e) => {
                    const next = [...cfg.scoring];
                    next[i] = { ...c, weight: Number(e.target.value) };
                    setCfg({ ...cfg, scoring: next });
                  }}
                />
              </div>
            </div>
          ))}
          <div className="row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy || scoringTotal !== 100}
              onClick={() => void saveScoring()}
            >
              Save scoring criteria
            </button>
            {scoringTotal !== 100 ? (
              <span className="muted small">
                Weights must sum to 100 (currently {scoringTotal}).
              </span>
            ) : (
              <span className="muted small">
                Past decisions keep the scores reviewers gave.
              </span>
            )}
          </div>
        </section>
      ) : null}

      {tab === 'timelines' ? (
        <section className="card">
          <div className="card__head">
            <h2>Timelines / SLAs</h2>
          </div>
          <div className="notice" style={{ marginBottom: 16 }}>
            <Icon name="info" size={16} />
            <span>
              Changes apply at once everywhere: overdue, stuck and stale counts
              on Home, the pipeline and Insights use the new values.
            </span>
          </div>
          <div className="grid grid-2">
            {(
              [
                ['pickup_days', 'Pickup (working days)'],
                ['decision_days', 'Decision (working days)'],
                ['stale_prototype_days', 'Stale prototype (days)'],
                ['needs_info_days', 'Needs info stuck after (days)'],
                ['owner_assign_days', 'Owner assignment (days)'],
              ] as const
            ).map(([key, label]) => (
              <div key={key} className="field">
                <label htmlFor={`tl-${key}`}>{label}</label>
                <input
                  id={`tl-${key}`}
                  className="input num-in"
                  type="number"
                  value={cfg.timelines[key] ?? 0}
                  onChange={(e) =>
                    setCfg({
                      ...cfg,
                      timelines: {
                        ...cfg.timelines,
                        [key]: Number(e.target.value),
                      },
                    })
                  }
                />
              </div>
            ))}
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={() => void saveTimelines()}
            >
              Save timelines
            </button>
          </div>
        </section>
      ) : null}

      {tab === 'points' ? (
        <section className="card">
          <div className="card__head">
            <h2>Point values</h2>
          </div>
          <p className="muted small">
            Changes apply to future ledger rows only.
          </p>
          <div className="grid grid-2">
            {Object.entries(cfg.point_overrides).map(([k, v]) => (
              <div key={k} className="field">
                <label htmlFor={`pt-${k}`}>{k}</label>
                <input
                  id={`pt-${k}`}
                  className="input num-in"
                  type="number"
                  value={v}
                  onChange={(e) =>
                    setCfg({
                      ...cfg,
                      point_overrides: {
                        ...cfg.point_overrides,
                        [k]: Number(e.target.value),
                      },
                    })
                  }
                />
              </div>
            ))}
          </div>
          <div className="row" style={{ marginTop: 12 }}>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy}
              onClick={() => void savePoints()}
            >
              Save points
            </button>
          </div>
        </section>
      ) : null}

      {tab === 'data' ? (
        <section className="card">
          <div className="card__head">
            <h2>Export / reset</h2>
          </div>
          <div className="row" style={{ gap: 8 }}>
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={async () => {
                const inv = await adminApi.exportInventory();
                flash(JSON.stringify(inv));
              }}
            >
              Export inventory
            </button>
            <button
              type="button"
              className="btn btn--danger"
              disabled={busy}
              onClick={() => void reset()}
            >
              Reset demo
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
