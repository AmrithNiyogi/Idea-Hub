/**
 * New-poll sheet (WhatsApp-style): Cancel / Poll / Send, question, options, settings.
 */

import { useEffect, useState } from 'react';

export type PollDraft = {
  question: string;
  options: string[];
  multi: boolean;
  endsAt: string | null;
};

type Props = {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onSubmit: (draft: PollDraft) => void | Promise<void>;
};

const MAX_OPTIONS = 10;
const DEFAULT_WINDOW_MS = 24 * 60 * 60 * 1000;

/** Local "YYYY-MM-DDTHH:mm" for <input type="datetime-local">. */
function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function PollCreateSheet({ open, busy, onClose, onSubmit }: Props) {
  const [question, setQuestion] = useState('');
  const [options, setOptions] = useState<string[]>(['', '']);
  const [multi, setMulti] = useState(false);
  const [timed, setTimed] = useState(false);
  const [endsLocal, setEndsLocal] = useState('');
  // Clock snapshot taken when the sheet opens (keeps render pure).
  const [openedAt, setOpenedAt] = useState(0);

  // Start fresh each time the sheet opens.
  useEffect(() => {
    if (!open) return;
    const now = Date.now();
    setQuestion('');
    setOptions(['', '']);
    setMulti(false);
    setTimed(false);
    setOpenedAt(now);
    setEndsLocal(toLocalInput(new Date(now + DEFAULT_WINDOW_MS)));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const cleaned = options.map((o) => o.trim()).filter(Boolean);
  const endsDate = timed && endsLocal ? new Date(endsLocal) : null;
  const endsValid = !timed || (!!endsDate && endsDate.getTime() > openedAt);
  const canSend = !busy && question.trim().length > 0 && cleaned.length >= 2 && endsValid;

  function send() {
    if (!canSend) return;
    void onSubmit({
      question: question.trim(),
      options: cleaned,
      multi,
      endsAt: endsDate ? endsDate.toISOString() : null,
    });
  }

  return (
    <div className="poll-sheet-overlay" role="presentation" onMouseDown={(e) => {
      if (e.target === e.currentTarget) onClose();
    }}>
      <div className="poll-sheet" role="dialog" aria-modal="true" aria-label="New poll">
        <header className="poll-sheet__head">
          <button type="button" className="poll-sheet__link" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <h2>Poll</h2>
          <button type="button" className="poll-sheet__link poll-sheet__link--strong" onClick={send} disabled={!canSend}>
            Send
          </button>
        </header>

        <div className="poll-sheet__body">
          <div className="poll-sheet__label">Question</div>
          <div className="poll-sheet__card">
            <textarea
              className="poll-sheet__question"
              rows={2}
              maxLength={300}
              placeholder="Ask a question"
              value={question}
              disabled={busy}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </div>

          <div className="poll-sheet__label">Options</div>
          <div className="poll-sheet__card">
            {options.map((opt, i) => (
              <div key={i} className="poll-sheet__row">
                <input
                  className="poll-sheet__input"
                  placeholder={`Option ${i + 1}`}
                  value={opt}
                  maxLength={200}
                  disabled={busy}
                  onChange={(e) =>
                    setOptions((prev) => prev.map((o, j) => (j === i ? e.target.value : o)))
                  }
                />
                {options.length > 2 ? (
                  <button
                    type="button"
                    className="poll-sheet__remove"
                    aria-label={`Remove option ${i + 1}`}
                    disabled={busy}
                    onClick={() => setOptions((prev) => prev.filter((_, j) => j !== i))}
                  >
                    −
                  </button>
                ) : null}
              </div>
            ))}
            <button
              type="button"
              className="poll-sheet__add"
              disabled={busy || options.length >= MAX_OPTIONS}
              onClick={() => setOptions((prev) => [...prev, ''])}
            >
              + Add option
            </button>
          </div>

          <div className="poll-sheet__card">
            <label className="poll-sheet__setting">
              <span>Allow multiple answers</span>
              <input
                type="checkbox"
                role="switch"
                className="poll-switch"
                checked={multi}
                disabled={busy}
                onChange={(e) => setMulti(e.target.checked)}
              />
            </label>
            <label className="poll-sheet__setting">
              <span>Set an end time</span>
              <input
                type="checkbox"
                role="switch"
                className="poll-switch"
                checked={timed}
                disabled={busy}
                onChange={(e) => setTimed(e.target.checked)}
              />
            </label>
            {timed ? (
              <div className="poll-sheet__setting poll-sheet__setting--sub">
                <input
                  type="datetime-local"
                  className="poll-sheet__datetime"
                  value={endsLocal}
                  min={toLocalInput(new Date(openedAt))}
                  disabled={busy}
                  aria-label="Poll end time"
                  onChange={(e) => setEndsLocal(e.target.value)}
                />
              </div>
            ) : null}
            {timed && !endsValid ? (
              <p className="poll-sheet__hint">Pick a time in the future.</p>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}

export default PollCreateSheet;
