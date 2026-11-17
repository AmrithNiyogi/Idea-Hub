/** Floating help chatbot — simulated FAQ map (no external LLM). */

import { FormEvent, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { agentsApi } from '../api/agents';
import { Icon } from './Icons';

type Msg = {
  role: 'user' | 'assistant';
  text: string;
  links?: Array<{ label: string; href: string }>;
};

const STARTERS = [
  'How do I submit an idea?',
  'How does review work?',
  'What roles exist?',
  'SSO and MFA?',
];

export function HelpChatFab() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: 'assistant',
      text: 'Hi — I am the Idea Hub help bot (Simulated — Kompass soon). Ask about Submit, Review, roles, Explore, Admin, or SSO/MFA. I never need passwords or OTP codes.',
      links: [
        { label: 'Submit', href: '/submit' },
        { label: 'Review', href: '/review' },
      ],
    },
  ]);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (open) endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [msgs, open]);

  const ask = async (text: string) => {
    const q = text.trim();
    if (!q || busy) return;
    setInput('');
    setMsgs((m) => [...m, { role: 'user', text: q }]);
    setBusy(true);
    try {
      const turn = await agentsApi.help(q);
      setMsgs((m) => [
        ...m,
        { role: 'assistant', text: turn.reply, links: turn.links },
      ]);
    } catch (e) {
      setMsgs((m) => [
        ...m,
        {
          role: 'assistant',
          text:
            e instanceof Error
              ? e.message
              : 'Help is temporarily unavailable.',
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

  return (
    <div className={`help-fab ${open ? 'is-open' : ''}`}>
      {open ? (
        <div
          className="help-fab__panel agent"
          role="dialog"
          aria-label="Idea Hub help"
        >
          <div className="agent__head">
            <Icon name="help" size={16} />
            <span className="agent__name">Help</span>
            <span className="pill pill--agent">Simulated — Kompass soon</span>
            <button
              type="button"
              className="btn btn--sm btn--ghost"
              style={{ marginLeft: 'auto' }}
              onClick={() => setOpen(false)}
              aria-label="Close help"
            >
              <Icon name="x" size={14} />
            </button>
          </div>
          <div className="agent__body">
            <div className="help-fab__log" role="log" aria-live="polite">
              {msgs.map((m, i) => (
                <div
                  key={i}
                  className={`sf-chat__bubble sf-chat__bubble--${m.role}`}
                >
                  <p style={{ margin: 0 }}>{m.text}</p>
                  {m.links?.length ? (
                    <div className="chip-row" style={{ marginTop: 8 }}>
                      {m.links.map((l) => (
                        <Link
                          key={l.href}
                          className="btn btn--sm"
                          to={l.href}
                          onClick={() => setOpen(false)}
                        >
                          {l.label}
                        </Link>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
              {busy ? <p className="muted small">Looking that up…</p> : null}
              <div ref={endRef} />
            </div>
            <div className="chip-row">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  type="button"
                  className="btn btn--sm"
                  disabled={busy}
                  onClick={() => void ask(s)}
                >
                  {s}
                </button>
              ))}
            </div>
            <form className="sf-chat__compose" onSubmit={onSubmit}>
              <input
                className="input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask about Idea Hub…"
                disabled={busy}
                aria-label="Help question"
              />
              <button
                type="submit"
                className="btn btn--sm btn--primary"
                disabled={busy || !input.trim()}
              >
                <Icon name="send" size={14} />
              </button>
            </form>
          </div>
          <div className="agent__foot">
            Canned FAQ stub — no secrets, no live Kompass.
          </div>
        </div>
      ) : null}

      <button
        type="button"
        className="help-fab__btn"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={open ? 'Close help chat' : 'Open help chat'}
      >
        <Icon name={open ? 'x' : 'help'} size={20} />
      </button>
    </div>
  );
}
