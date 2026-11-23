import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ideasApi } from '../api/ideas';
import { ideathonsApi } from '../api/ideathons';
import { useAuth } from '../auth/AuthProvider';
import { GITHUB_REPO_PATTERN } from '../constants/github';
import { TeamFields } from '../components/submit/TeamFields';
import { agentsApi } from '../api/agents';
import { Icon } from '../components/Icons';
import { StatusPill } from '../components/StatusPill';
import { EnhancePanel, type EnhanceField } from '../components/submit/EnhancePanel';
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
  co_author_ids: [],
  team_name: '',
  github_url: '',
};

const CAT_HELP: Record<string, string> = {
  tech: 'Engineering, infrastructure, tooling and platform improvements.',
  business: 'Revenue, customers, pricing, partners and go-to-market.',
  process: 'How we work: handoffs, checklists, meetings, approvals.',
  innovation:
    'New products, features and agent capabilities for Kompass or internal use.',
};

const FIELD_CHIP: Record<string, string> = {
  title: 'title',
  problem: 'problem',
  solution: 'solution',
  beneficiaries: 'beneficiaries',
  success_metrics: 'success metrics',
  tags: 'tags',
  effort: 'effort',
  category_slug: 'category',
  category_id: 'category',
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

type ChatMsg = {
  role: 'user' | 'assistant';
  text: string;
  updated?: string[];
};

type UndoToast = {
  snapshot: IdeaWrite;
  labels: string[];
};

function draftPayload(form: IdeaWrite): Record<string, unknown> {
  return {
    title: form.title,
    problem: form.problem,
    solution: form.solution,
    beneficiaries: form.beneficiaries,
    success_metrics: form.success_metrics,
    tags: form.tags,
    effort: form.effort,
    category_id: form.category_id,
  };
}

function patchLabels(patches: Record<string, unknown>): string[] {
  return Object.keys(patches)
    .map((k) => FIELD_CHIP[k] || k.replace(/_/g, ' '))
    .filter((v, i, a) => a.indexOf(v) === i);
}

export function SubmitPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { user } = useAuth();
  const draftParam = params.get('draft');
  const ideathonId = params.get('ideathon');
  const [ideathonTitle, setIdeathonTitle] = useState<string | null>(null);
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const [form, setForm] = useState<IdeaWrite>(empty);
  const [draftId, setDraftId] = useState<string | null>(draftParam);
  const [categories, setCategories] = useState<Category[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<string | null>(null);
  const [similar, setSimilar] = useState<SimilarHit[]>([]);
  const [assistNote, setAssistNote] = useState<string | null>(null);
  const [assistLive, setAssistLive] = useState<boolean | null>(null);
  const assistTimer = useRef<number | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const formRef = useRef(form);
  const categoriesRef = useRef(categories);
  const undoTimer = useRef<number | null>(null);
  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatBusy, setChatBusy] = useState(false);
  const [chatLive, setChatLive] = useState<boolean | null>(null);
  const [awaitingField, setAwaitingField] = useState<string | null>(null);
  const [assistConversationId, setAssistConversationId] = useState<
    string | null
  >(null);
  const [chatOpen, setChatOpen] = useState(true);
  const [undoToast, setUndoToast] = useState<UndoToast | null>(null);
  const [flashFields, setFlashFields] = useState<Set<string>>(new Set());
  const guideStarted = useRef(false);

  useEffect(() => {
    formRef.current = form;
  }, [form]);

  useEffect(() => {
    categoriesRef.current = categories;
  }, [categories]);

  useEffect(() => {
    ideasApi.categories().then(setCategories).catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    if (!ideathonId) {
      setIdeathonTitle(null);
      return;
    }
    ideathonsApi
      .get(ideathonId)
      .then((d) => setIdeathonTitle(d.title))
      .catch(() => setIdeathonTitle(null));
  }, [ideathonId]);

  const applyPatches = (
    patches: Record<string, unknown>,
    opts?: { skipUndo?: boolean },
  ): string[] => {
    if (!patches || !Object.keys(patches).length) return [];
    const labels = patchLabels(patches);
    const prev = formRef.current;

    setForm((f) => {
      const next = { ...f };
      if (typeof patches.title === 'string') next.title = patches.title;
      if (typeof patches.problem === 'string') next.problem = patches.problem;
      if (typeof patches.solution === 'string') next.solution = patches.solution;
      if (typeof patches.beneficiaries === 'string') {
        next.beneficiaries = patches.beneficiaries;
      }
      if (typeof patches.success_metrics === 'string') {
        next.success_metrics = patches.success_metrics;
      }
      if (Array.isArray(patches.tags)) {
        next.tags = patches.tags.map(String).slice(0, 8);
      }
      if (
        typeof patches.effort === 'string' &&
        ['S', 'M', 'L', 'XL'].includes(patches.effort)
      ) {
        next.effort = patches.effort as Effort;
      }
      if (typeof patches.category_slug === 'string') {
        const slug = patches.category_slug.toLowerCase();
        const match = categoriesRef.current.find(
          (c) => c.slug.toLowerCase() === slug,
        );
        if (match) next.category_id = match.id;
      }
      if (typeof patches.category_id === 'string') {
        next.category_id = patches.category_id;
      }
      return next;
    });

    if (!opts?.skipUndo) {
      if (undoTimer.current) window.clearTimeout(undoTimer.current);
      setUndoToast({ snapshot: prev, labels });
      undoTimer.current = window.setTimeout(() => setUndoToast(null), 8000);
    }

    const flashKeys = new Set(
      Object.keys(patches).flatMap((k) => {
        if (k === 'category_slug') return ['category_id'];
        return [k];
      }),
    );
    setFlashFields(flashKeys);
    window.setTimeout(() => setFlashFields(new Set()), 1200);

    return labels;
  };

  const undoLastApply = () => {
    if (!undoToast) return;
    setForm(undoToast.snapshot);
    setUndoToast(null);
    if (undoTimer.current) window.clearTimeout(undoTimer.current);
  };

  // Open the simulated Submit chat once on mount (blank form OK).
  useEffect(() => {
    if (guideStarted.current) return;
    guideStarted.current = true;
    setChatBusy(true);
    agentsApi
      .submitAssist({ draft: draftPayload(empty), message: '' })
      .then((turn) => {
        setChat([{ role: 'assistant', text: turn.reply }]);
        setChatLive(!turn.simulated);
        setAwaitingField(turn.awaiting_field);
        if (turn.conversation_id) setAssistConversationId(turn.conversation_id);
      })
      .catch(() => {
        setChat([
          {
            role: 'assistant',
            text: 'Simulated guide unavailable. You can still fill the draft form.',
          },
        ]);
      })
      .finally(() => setChatBusy(false));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat, chatBusy]);

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
          co_author_ids: idea.co_author_ids ?? [],
          team_name: idea.team_name ?? '',
          github_url: idea.github_url ?? '',
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
          setAssistLive(!run.simulated);
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

  useEffect(() => {
    return () => {
      if (undoTimer.current) window.clearTimeout(undoTimer.current);
    };
  }, []);

  const set = <K extends keyof IdeaWrite>(key: K, value: IdeaWrite[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const fieldClass = (key: string) =>
    flashFields.has(key) ? 'field field--flash' : 'field';

  const sendChatText = async (raw: string) => {
    const text = raw.trim();
    if (!text || chatBusy) return;
    setChatInput('');
    setChat((c) => [...c, { role: 'user', text }]);
    setChatBusy(true);
    try {
      const turn = await agentsApi.submitAssist({
        draft: draftPayload(formRef.current),
        message: text,
        awaiting_field: awaitingField,
        conversation_id: assistConversationId,
      });
      setChatLive(!turn.simulated);
      const labels =
        turn.patches && Object.keys(turn.patches).length
          ? applyPatches(turn.patches)
          : [];
      setChat((c) => [
        ...c,
        {
          role: 'assistant',
          text: turn.reply,
          updated: labels.length ? labels : undefined,
        },
      ]);
      setAwaitingField(turn.awaiting_field);
      if (turn.conversation_id) setAssistConversationId(turn.conversation_id);
    } catch (err) {
      setChat((c) => [
        ...c,
        {
          role: 'assistant',
          text:
            err instanceof Error
              ? err.message
              : 'Could not reach the simulated assistant.',
        },
      ]);
    } finally {
      setChatBusy(false);
    }
  };

  const sendChat = async (e?: FormEvent) => {
    e?.preventDefault();
    await sendChatText(chatInput);
  };

  const addTag = (t: string) => {
    const tag = t
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9\- ]/g, '')
      .replace(/\s+/g, '-');
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
    const github = (form.github_url ?? '').trim();
    if (github && !GITHUB_REPO_PATTERN.test(github)) {
      setError('GitHub link must look like https://github.com/owner/repo.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const idea = await ideasApi.submit(
        { ...form, title: form.title.trim(), github_url: github },
        draftId,
      );
      if (ideathonId) {
        try {
          await ideathonsApi.link(ideathonId, idea.id);
        } catch (linkErr) {
          // The idea is already submitted, so keep the page open and say how to fix it.
          setSubmittedId(idea.id);
          const why = linkErr instanceof Error ? linkErr.message : 'Link failed';
          setError(
            `Your idea was submitted, but it could not be added to the ideathon (${why}). Open the ideathon and link it from "Or link one of your existing ideas".`,
          );
          return;
        }
      }
      navigate(`/ideas/${idea.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Submit failed');
    } finally {
      setBusy(false);
    }
  };

  const titleLen = form.title.length;
  const quickPrompts = [
    'brainstorm',
    'make the title shorter',
    'add metrics',
    'change category to tech',
  ];

  return (
    <div className="stack stack--lg">
      <div className="page-head">
        <div>
          <div className="eyebrow eyebrow--plain">New idea</div>
          <h1>{draftId ? 'Continue your draft' : 'Submit an idea'}</h1>
          <p>
            Chat to discover or refine an idea — the draft form updates live.
            You can also type on the form yourself anytime.
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

      {ideathonId && !submittedId ? (
        <div className="notice">
          <Icon name="flag" size={16} />
          <span>
            {ideathonTitle
              ? `This idea will be added to the ideathon "${ideathonTitle}" when you submit.`
              : 'This idea will be added to the ideathon when you submit.'}
          </span>
        </div>
      ) : null}

      {error ? (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" size={18} />
          <span>{error}</span>
        </div>
      ) : null}

      {submittedId ? (
        <Link className="btn" to={`/ideas/${submittedId}`}>
          Open my submitted idea
        </Link>
      ) : null}

      <div className="layout-rail layout-rail--submit">
        <section className="card sf-chat-panel">
          <div className="row row--between" style={{ marginBottom: 8 }}>
            <div className="row" style={{ gap: 8 }}>
              <Icon name="spark" size={16} />
              <strong>Submit assistant</strong>
              <span className="pill pill--agent">{chatLive ? 'Live — Kompass' : 'Simulated'}</span>
            </div>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              onClick={() => setChatOpen((o) => !o)}
              aria-expanded={chatOpen}
            >
              {chatOpen ? 'Hide chat' : 'Show chat'}
            </button>
          </div>

          {chatOpen ? (
            <div className="agent sf-chat">
              <div className="agent__head">
                <Icon name="message" size={16} />
                <span className="agent__name">Idea chat</span>
                <span className="agent__kind">{chatLive ? 'Live' : 'Simulated'}</span>
              </div>
              <div className="agent__body">
                <div className="sf-chat__log" role="log" aria-live="polite">
                  {chat.map((m, i) => (
                    <div key={`${m.role}-${i}`}>
                      <div
                        className={`sf-chat__bubble sf-chat__bubble--${m.role}`}
                      >
                        {m.text.split('\n').map((line, j) => (
                          <p key={j} style={{ margin: j ? '6px 0 0' : 0 }}>
                            {line.replace(/\*\*/g, '')}
                          </p>
                        ))}
                      </div>
                      {m.updated?.length ? (
                        <div
                          className="sf-chat__chips"
                          aria-label="Fields updated"
                        >
                          {m.updated.map((lab) => (
                            <span key={lab} className="sf-chat__chip">
                              Updated {lab}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  ))}
                  {chatBusy ? (
                    <p className="muted small">Thinking…</p>
                  ) : null}
                  <div ref={chatEndRef} />
                </div>

                {!chatBusy && chat.length <= 2 ? (
                  <div className="chip-row sf-chat__prompts">
                    {quickPrompts.map((p) => (
                      <button
                        key={p}
                        type="button"
                        className="chip-link"
                        disabled={chatBusy}
                        onClick={() => {
                          void sendChatText(p);
                        }}
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                ) : null}

                <form className="sf-chat__compose" onSubmit={sendChat}>
                  <input
                    className="input"
                    value={chatInput}
                    onChange={(e) => setChatInput(e.target.value)}
                    placeholder="Describe a problem, or ask to refine the draft…"
                    disabled={chatBusy}
                    aria-label="Message the submit assistant"
                  />
                  <button
                    type="submit"
                    className="btn btn--sm btn--primary"
                    disabled={chatBusy || !chatInput.trim()}
                  >
                    <Icon name="send" size={14} />
                  </button>
                </form>
              </div>
              <div className="agent__foot">
                Patches apply to the draft automatically. Undo from the toast.
                Manual form edits always work.
              </div>
            </div>
          ) : (
            <p className="muted small" style={{ margin: 0 }}>
              Chat hidden — fill the draft on the right (manual-only).
            </p>
          )}

          {assistNote ? (
            <p className="muted small" style={{ marginTop: 12 }}>
              {assistNote}
            </p>
          ) : null}

          {similar.length ? (
            <div className="stack stack--sm" style={{ marginTop: 12 }}>
              <div className="row row--between" style={{ alignItems: 'center' }}>
                <h4 style={{ margin: 0 }}>Similar ideas</h4>
                {assistLive !== null ? (
                  <span className="pill pill--agent">{assistLive ? 'Live' : 'Simulated'}</span>
                ) : null}
              </div>
              {similar.map((s, idx) => {
                const sid = String(s.idea_id || s.id || idx);
                const shared = s.shared_terms || s.sharedTerms || [];
                const pct = Math.round((s.similarity ?? 0) * 100);
                return (
                  <div key={sid} className="similar">
                    <div className="row row--between">
                      <Link className="listrow__title" to={`/ideas/${sid}`}>
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

          <EnhancePanel
            draft={form}
            onApply={(f: EnhanceField, text: string) =>
              setForm((prev) => ({ ...prev, [f]: text }))
            }
          />

          <div className="card card--tight" style={{ marginTop: 12 }}>
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
                  <Icon name={ok ? 'check' : 'circle'} size={14} /> {lab}
                </li>
              ))}
            </ul>
          </div>
        </section>

        <form className="card sf-section" onSubmit={submit}>
          <div className="row row--between" style={{ marginBottom: 4 }}>
            <h4 style={{ margin: 0 }}>Your draft</h4>
            <span className="muted small">Live mirror of the chat</span>
          </div>

          <div className={fieldClass('category_id')}>
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

          <div className={fieldClass('title')}>
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

          <div className={fieldClass('problem')}>
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

          <div className={fieldClass('solution')}>
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
            <div className={fieldClass('beneficiaries')}>
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
            <div className={fieldClass('effort')}>
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

          <div className={fieldClass('success_metrics')}>
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

          <div className={fieldClass('tags')}>
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

          <TeamFields
            currentUserId={user?.id ?? null}
            coAuthorIds={form.co_author_ids ?? []}
            teamName={form.team_name ?? ''}
            githubUrl={form.github_url ?? ''}
            onCoAuthorsChange={(ids) => set('co_author_ids', ids)}
            onTeamNameChange={(v) => set('team_name', v)}
            onGithubUrlChange={(v) => set('github_url', v)}
          />

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
            <button type="submit" className="btn btn--primary" disabled={busy}>
              {busy ? 'Working…' : 'Submit idea'}
            </button>
          </div>
          {savedAt ? (
            <p className="muted small">Draft saved at {savedAt}</p>
          ) : null}
        </form>
      </div>

      {undoToast ? (
        <div className="toasts" role="status">
          <div className="toast toast--ok">
            <span className="grow">
              Updated {undoToast.labels.join(', ')}
            </span>
            <button
              type="button"
              className="btn btn--sm"
              onClick={undoLastApply}
            >
              Undo
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
