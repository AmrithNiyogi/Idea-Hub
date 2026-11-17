import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { agentsApi } from '../api/agents';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { EFFORT_LABELS, TAG_VOCAB } from '../constants/status';
import type { Category, Effort, IdeaWrite } from '../types/idea';

const empty: IdeaWrite = {
  title: '',
  category_id: null,
  problem: '',
  solution: '',
  beneficiaries: '',
  effort: 'M',
  success_metrics: '',
  tags: [],
  anonymous: false,
};

const CAT_HELP: Record<string, string> = {
  tech: 'Engineering, infrastructure, tooling and platform improvements.',
  business: 'Revenue, customers, pricing, partners and go-to-market.',
  process: 'How we work: handoffs, checklists, meetings, approvals.',
  innovation:
    'New products, features and agent capabilities for Kompass or internal use.',
};

type SimilarHit = {
  idea_id?: string;
  id?: string;
  title?: string;
  status?: string;
  similarity?: number;
  shared_terms?: string[];
  sharedTerms?: string[];
};

export function SubmitPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const draftParam = params.get('draft');
  const [form, setForm] = useState<IdeaWrite>(empty);
  const [draftId, setDraftId] = useState<string | null>(draftParam);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [similar, setSimilar] = useState<SimilarHit[]>([]);
  const [assistNote, setAssistNote] = useState<string | null>(null);
  const assistTimer = useRef<number | null>(null);

  useEffect(() => {
    ideasApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!draftParam) return;
    ideasApi
      .get(draftParam)
      .then((idea) => {
        setDraftId(idea.id);
        setForm({
          title: idea.title,
          category_id: idea.category_id,
          problem: idea.problem,
          solution: idea.solution,
          beneficiaries: idea.beneficiaries,
          effort: idea.effort,
          success_metrics: idea.success_metrics,
          tags: idea.tags,
          anonymous: idea.anonymous,
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Draft not found'));
  }, [draftParam]);

  // Debounced similar-ideas via idea-intelligence agent when title/problem change
  useEffect(() => {
    if (assistTimer.current) window.clearTimeout(assistTimer.current);
    const title = form.title.trim();
    const problem = (form.problem ?? '').trim();
    if (title.length < 8 && problem.length < 20) {
      setSimilar([]);
      return;
    }
    assistTimer.current = window.setTimeout(() => {
      agentsApi
        .run({
          agent_id: 'idea-intelligence',
          event: 'idea.drafted',
          record: false,
          context: {
            draft: {
              title: form.title,
              problem: form.problem,
              solution: form.solution,
              tags: form.tags,
              category_id: form.category_id,
            },
          },
        })
        .then((run) => {
          const out = run.output as Record<string, unknown>;
          const hits = (out.similar_ideas ||
            out.similarIdeas ||
            []) as SimilarHit[];
          setSimilar(Array.isArray(hits) ? hits.slice(0, 4) : []);
          const missing = out.missing_fields || out.missingFields;
          if (Array.isArray(missing) && missing.length) {
            setAssistNote(
              `Checklist: ${missing.length} field${missing.length === 1 ? '' : 's'} still look incomplete.`,
            );
          } else {
            setAssistNote(run.summary || null);
          }
        })
        .catch(() => {
          /* agent optional — don't block submit */
        });
    }, 500);
    return () => {
      if (assistTimer.current) window.clearTimeout(assistTimer.current);
    };
  }, [
    form.title,
    form.problem,
    form.solution,
    form.tags,
    form.category_id,
  ]);

  const set = <K extends keyof IdeaWrite>(key: K, value: IdeaWrite[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const addTag = (t: string) => {
    const tag = t.trim().toLowerCase().replace(/[^a-z0-9\- ]/g, '').replace(/\s+/g, '-');
    if (!tag || (form.tags ?? []).includes(tag)) return;
    if ((form.tags ?? []).length >= 8) {
      setError('You can add up to 8 tags.');
      return;
    }
    set('tags', [...(form.tags ?? []), tag]);
    setTagInput('');
  };

  const saveDraft = async () => {
    if (!form.title.trim()) {
      setError('Title is required to save a draft.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const idea = await ideasApi.saveDraft(
        { ...form, title: form.title.trim() },
        draftId,
      );
      setDraftId(idea.id);
      setSavedAt(new Date().toLocaleTimeString());
      if (!draftParam) {
        navigate(`/submit?draft=${idea.id}`, { replace: true });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save draft');
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e?: FormEvent) => {
    e?.preventDefault();
    if (!form.title.trim() || !form.problem?.trim() || !form.solution?.trim()) {
      setError('Title, problem, and solution are required to submit.');
      return;
    }
    if (!form.category_id) {
      setError('Pick a category before submitting.');
      return;
    }
    if (!form.beneficiaries?.trim() || !form.success_metrics?.trim()) {
      setError('Beneficiaries and success metrics are required.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const idea = await ideasApi.submit(
        { ...form, title: form.title.trim() },
        draftId,
      );
      navigate(`/ideas/${idea.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed');
    } finally {
      setBusy(false);
    }
  };

  const titleLen = form.title.length;

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">New idea</div>
          <h1>{draftId ? 'Continue your draft' : 'Submit an idea'}</h1>
          <p>
            Five short fields. Idea Hub will check for similar ideas as you type,
            and you keep full control of what you apply.
          </p>
        </div>
        <div className="row">
          <Link className="btn btn--ghost" to="/my">
            My drafts
          </Link>
          <button
            type="button"
            className="btn"
            disabled={busy}
            onClick={saveDraft}
          >
            <Icon name="edit" size={16} /> Save draft
          </button>
          <button
            type="button"
            className="btn btn--primary"
            disabled={busy}
            onClick={() => submit()}
          >
            <Icon name="send" size={16} /> Submit idea
          </button>
        </div>
      </div>

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="layout-rail layout-rail--submit">
        <form className="card sf-section" onSubmit={submit}>
          <div className="field">
            <span className="label" id="sf-cat-label">
              Category
            </span>
            <div
              className="radio-cards"
              role="radiogroup"
              aria-labelledby="sf-cat-label"
            >
              {categories.map((c) => (
                <label key={c.id} className="radio-card">
                  <input
                    type="radio"
                    name="sf-cat"
                    value={c.id}
                    checked={form.category_id === c.id}
                    onChange={() => set('category_id', c.id)}
                  />
                  <span className="radio-card__title">
                    <span
                      className="dot"
                      style={{
                        background: c.color || 'var(--brand)',
                        width: 8,
                        height: 8,
                        borderRadius: 99,
                        display: 'inline-block',
                      }}
                    />
                    {c.label}
                  </span>
                  <span className="radio-card__desc">
                    {CAT_HELP[c.slug] || c.description || ''}
                  </span>
                </label>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="sf-title">Title</label>
            <input
              className="input"
              id="sf-title"
              value={form.title}
              onChange={(e) => set('title', e.target.value)}
              placeholder="A short, specific title"
              maxLength={120}
              autoComplete="off"
              required
            />
            <span className="hint" aria-live="polite">
              {titleLen}/120
            </span>
          </div>

          <div className="field">
            <label htmlFor="sf-problem">Problem statement</label>
            <textarea
              className="textarea"
              id="sf-problem"
              rows={4}
              value={form.problem}
              onChange={(e) => set('problem', e.target.value)}
              placeholder="Who is affected, what goes wrong, and how often?"
            />
            <span className="hint">
              {form.category_id
                ? 'Say who is affected, how often it happens and what it costs.'
                : 'Pick a category for a tailored prompt.'}
            </span>
          </div>

          <div className="field">
            <label htmlFor="sf-solution">Proposed solution</label>
            <textarea
              className="textarea"
              id="sf-solution"
              rows={4}
              value={form.solution}
              onChange={(e) => set('solution', e.target.value)}
              placeholder="What would you build or change?"
            />
          </div>

          <div className="sf-grid2">
            <div className="field">
              <label htmlFor="sf-beneficiaries">Who benefits</label>
              <textarea
                className="textarea"
                id="sf-beneficiaries"
                rows={3}
                value={form.beneficiaries}
                onChange={(e) => set('beneficiaries', e.target.value)}
                placeholder="Teams, roles or customers, with rough numbers"
              />
            </div>
            <div className="field">
              <span className="label" id="sf-effort-label">
                Rough effort
              </span>
              <div
                className="segmented"
                role="radiogroup"
                aria-labelledby="sf-effort-label"
              >
                {(Object.keys(EFFORT_LABELS) as Effort[]).map((k) => (
                  <label key={k}>
                    <input
                      type="radio"
                      name="sf-effort"
                      value={k}
                      checked={(form.effort ?? 'M') === k}
                      onChange={() => set('effort', k)}
                    />
                    <span title={EFFORT_LABELS[k]}>{k}</span>
                  </label>
                ))}
              </div>
              <div className="hint">
                S = days, M = weeks, L = a quarter, XL = multi-quarter
              </div>
            </div>
          </div>

          <div className="field">
            <label htmlFor="sf-success">What success looks like</label>
            <textarea
              className="textarea"
              id="sf-success"
              rows={3}
              value={form.success_metrics}
              onChange={(e) => set('success_metrics', e.target.value)}
              placeholder="Use a number: from X to Y by when"
            />
          </div>

          <div className="field">
            <span className="label">Tags</span>
            <div className="chip-row" style={{ marginBottom: 8 }}>
              {(form.tags ?? []).map((t) => (
                <span key={t} className="tag tag--removable">
                  {t}
                  <button
                    type="button"
                    aria-label={`Remove ${t}`}
                    onClick={() =>
                      set(
                        'tags',
                        (form.tags ?? []).filter((x) => x !== t),
                      )
                    }
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
            <input
              className="input"
              id="sf-taginput"
              value={tagInput}
              list="tag-vocab"
              placeholder="Type a tag and press Enter"
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  addTag(tagInput);
                }
              }}
            />
            <datalist id="tag-vocab">
              {TAG_VOCAB.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>

          <label className="switch">
            <input
              type="checkbox"
              checked={!!form.anonymous}
              onChange={(e) => set('anonymous', e.target.checked)}
            />
            <span className="switch__track" />
            <span>
              <strong>Submit anonymously</strong>
              <br />
              <span className="muted small">
                Your name is hidden from everyone, including reviewers, on the
                idea and in discussion. You will still see it as yours.
              </span>
            </span>
          </label>

          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={saveDraft}
            >
              Save draft
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={busy}
            >
              {busy ? 'Working…' : 'Submit idea'}
            </button>
          </div>
          {savedAt ? (
            <p className="muted small">Draft saved at {savedAt}</p>
          ) : null}
        </form>

        <aside className="stack sticky">
          <details className="card card--tight sf-details" open>
            <summary>
              <Icon name="spark" size={16} /> Idea Hub assistants{' '}
              <span className="pill pill--agent">Simulated</span>
            </summary>
            <div className="stack">
              {assistNote ? (
                <div className="agent">
                  <div className="agent__head">
                    <span className="agent__name">Idea Intelligence</span>
                    <span className="agent__kind">Computed</span>
                  </div>
                  <div className="agent__body">
                    <p className="muted small">{assistNote}</p>
                  </div>
                </div>
              ) : (
                <p className="muted small">
                  Keep typing. Similar ideas and completeness tips appear here.
                </p>
              )}

              {similar.length ? (
                <div className="stack stack--sm">
                  <h4 style={{ margin: 0 }}>Similar ideas</h4>
                  {similar.map((s, idx) => {
                    const sid = String(s.idea_id || s.id || idx);
                    const shared =
                      s.shared_terms || s.sharedTerms || [];
                    const pct = Math.round((s.similarity ?? 0) * 100);
                    return (
                      <div key={sid} className="similar">
                        <div className="row row--between">
                          <Link
                            className="listrow__title"
                            to={`/ideas/${sid}`}
                          >
                            {s.title || sid}
                          </Link>
                          {pct ? (
                            <span className="similar__pct">{pct}%</span>
                          ) : null}
                        </div>
                        <div className="row" style={{ gap: 6 }}>
                          {s.status ? <StatusPill status={s.status} /> : null}
                          {shared.slice(0, 3).map((t) => (
                            <span key={t} className="tag">
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : null}

              <div className="card card--tight">
                <h4 style={{ marginTop: 0 }}>Checklist</h4>
                <ul className="bullets" style={{ paddingLeft: 18 }}>
                  {(
                    [
                      ['Title', !!form.title.trim()],
                      ['Category', !!form.category_id],
                      ['Problem', !!(form.problem ?? '').trim()],
                      ['Solution', !!(form.solution ?? '').trim()],
                      ['Beneficiaries', !!(form.beneficiaries ?? '').trim()],
                      ['Success', !!(form.success_metrics ?? '').trim()],
                      ['Effort', !!form.effort],
                    ] as const
                  ).map(([lab, ok]) => (
                    <li key={lab}>
                      {ok ? '✓' : '○'} {lab}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </details>
        </aside>
      </div>
    </div>
  );
}
