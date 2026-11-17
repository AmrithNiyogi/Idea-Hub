/**
 * Idea Hub Help chat widget — UX adapted from aistudio-chatbot-ui-v2
 * (DotAgent launcher + panel). Calls Idea Hub ``/agents/simulate/help``
 * (simulate or live runs/execute via backend) and echoes ``conversation_id``.
 */

import { FormEvent, KeyboardEvent, useEffect, useId, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { agentsApi } from '../api/agents';

type Msg = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  links?: Array<{ label: string; href: string }>;
  loading?: boolean;
  error?: boolean;
  at: Date;
};

const STARTERS = [
  'How do I submit an idea?',
  'How does review work?',
  'What roles exist?',
  'SSO and MFA?',
];

const WELCOME: Msg = {
  id: 'welcome',
  role: 'assistant',
  text:
    'Hi — I am the Idea Hub help guide. Ask about Submit, Review, roles, Explore, Admin, or SSO/MFA. I never need passwords or OTP codes.',
  links: [
    { label: 'Submit', href: '/submit' },
    { label: 'Review', href: '/review' },
  ],
  at: new Date(0),
};

function formatTime(d: Date) {
  if (d.getTime() === 0) return '';
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function HelpChatFab() {
  const titleId = useId();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [modeLabel, setModeLabel] = useState('Simulated');
  const [msgs, setMsgs] = useState<Msg[]>([{ ...WELCOME, at: new Date() }]);
  const logRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, open, busy]);

  useEffect(() => {
    if (open) {
      window.setTimeout(() => inputRef.current?.focus(), 120);
    }
  }, [open]);

  const clearChat = () => {
    setMsgs([{ ...WELCOME, id: `welcome-${Date.now()}`, at: new Date() }]);
    setConversationId(null);
    setModeLabel('Simulated');
    setInput('');
  };

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput('');
    const userMsg: Msg = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: q,
      at: new Date(),
    };
    const loadingId = `a-load-${Date.now()}`;
    setMsgs((m) => [
      ...m,
      userMsg,
      {
        id: loadingId,
        role: 'assistant',
        text: 'Thinking…',
        loading: true,
        at: new Date(),
      },
    ]);
    setBusy(true);
    try {
      const turn = await agentsApi.help(q, conversationId);
      if (turn.conversation_id) {
        setConversationId(turn.conversation_id);
      }
      setModeLabel(
        turn.mode === 'live' || turn.simulated === false ? 'Live' : 'Simulated',
      );
      setMsgs((m) => [
        ...m.filter((x) => x.id !== loadingId),
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: turn.reply,
          links: turn.links,
          at: new Date(),
        },
      ]);
    } catch (e) {
      setMsgs((m) => [
        ...m.filter((x) => x.id !== loadingId),
        {
          id: `a-err-${Date.now()}`,
          role: 'assistant',
          text:
            e instanceof Error
              ? e.message
              : 'Help is temporarily unavailable.',
          error: true,
          at: new Date(),
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void ask(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void ask(input);
    }
  };

  return (
    <div className={`ik-chat ${open ? 'ik-chat--open' : ''}`}>
      {open ? (
        <div
          className="ik-chat__panel"
          role="dialog"
          aria-modal="false"
          aria-labelledby={titleId}
        >
          <header className="ik-chat__header">
            <div className="ik-chat__brand">
              <img
                className="ik-chat__header-logo"
                src="/ideakonnect-mark.svg"
                alt=""
                width={28}
                height={28}
              />
              <div className="ik-chat__title-wrap">
                <h2 className="ik-chat__title" id={titleId}>
                  Idea Hub Help
                </h2>
                <span className="ik-chat__mode">{modeLabel}</span>
              </div>
            </div>
            <div className="ik-chat__header-actions">
              <button
                type="button"
                className="ik-chat__clear"
                onClick={clearChat}
              >
                Clear
              </button>
              <button
                type="button"
                className="ik-chat__close"
                onClick={() => setOpen(false)}
                aria-label="Close help chat"
              >
                ✕
              </button>
            </div>
          </header>

          <div className="ik-chat__messages" ref={logRef} role="log" aria-live="polite">
            {msgs.map((m) => (
              <div
                key={m.id}
                className={`ik-chat__msg ik-chat__msg--${m.role}${
                  m.error ? ' ik-chat__msg--error' : ''
                }${m.loading ? ' ik-chat__msg--loading' : ''}`}
              >
                <div className="ik-chat__msg-content">
                  <div className="ik-chat__msg-header">
                    <span>{m.role === 'user' ? 'You' : 'Help'}</span>
                    {formatTime(m.at) ? (
                      <span className="ik-chat__msg-time">{formatTime(m.at)}</span>
                    ) : null}
                  </div>
                  <div className="ik-chat__msg-text">
                    {m.loading ? <span className="ik-chat__loading-dot" /> : null}
                    {m.text}
                  </div>
                  {m.links?.length ? (
                    <div className="ik-chat__links">
                      {m.links.map((l) => (
                        <Link
                          key={l.href}
                          className="ik-chat__link"
                          to={l.href}
                          onClick={() => setOpen(false)}
                        >
                          {l.label}
                        </Link>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>

          <div className="ik-chat__input">
            <div className="ik-chat__starters">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="ik-chat__starter"
                  disabled={busy}
                  onClick={() => void ask(s)}
                >
                  {s}
                </button>
              ))}
            </div>
            <form className="ik-chat__form" onSubmit={onSubmit}>
              <textarea
                ref={inputRef}
                className="ik-chat__textarea"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Type your message here…"
                rows={1}
                disabled={busy}
                aria-label="Help question"
              />
              <button
                type="submit"
                className="ik-chat__send"
                disabled={busy || !input.trim()}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
                {busy ? 'Sending…' : 'Send'}
              </button>
            </form>
            <p className="ik-chat__tip">
              Enter to send · Shift+Enter for a new line · No passwords or OTP
            </p>
          </div>
        </div>
      ) : null}

      {!open ? (
        <button
          type="button"
          className="ik-chat__launcher"
          onClick={() => setOpen(true)}
          aria-expanded={false}
          aria-label="Open help chat"
        >
          <img
            className="ik-chat__launcher-icon"
            src="/ideakonnect-mark.svg"
            alt=""
            width={40}
            height={40}
          />
        </button>
      ) : null}
    </div>
  );
}
