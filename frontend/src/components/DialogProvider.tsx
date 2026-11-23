/**
 * In-app replacements for window.confirm and window.prompt.
 *
 * Use `useDialog()` and `await confirm(...)` / `await prompt(...)`. Dialogs use
 * the app's modal styles (tokens.css `.modal-backdrop` / `.modal`), so they
 * match the rest of the UI instead of the browser's native popup.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react';

export interface ConfirmOptions {
  title: string;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Use for destructive actions; styles the confirm button as danger. */
  danger?: boolean;
  /**
   * When set, the confirm button stays disabled until the user types this
   * exact text (for example a user's email before a permanent delete).
   */
  requireText?: string;
}

export interface PromptOptions {
  title: string;
  message?: ReactNode;
  label: string;
  /** Styles the confirm button as destructive. */
  danger?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  placeholder?: string;
  /** Pre-filled text. */
  defaultValue?: string;
  /** Minimum length after trimming. Shown as an inline error. */
  minLength?: number;
  /** Set to true for longer notes. */
  multiline?: boolean;
}

interface DialogContextValue {
  /** Resolves true when confirmed, false when cancelled or dismissed. */
  confirm: (options: ConfirmOptions) => Promise<boolean>;
  /** Resolves the entered text when submitted, or null when cancelled. */
  prompt: (options: PromptOptions) => Promise<string | null>;
}

type ActiveDialog =
  | { kind: 'confirm'; options: ConfirmOptions; resolve: (ok: boolean) => void }
  | { kind: 'prompt'; options: PromptOptions; resolve: (value: string | null) => void };

const DialogContext = createContext<DialogContextValue | null>(null);

export function DialogProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<ActiveDialog | null>(null);

  // Opening a dialog while another is open cancels the first one. Resolving a
  // promise twice is a no-op, so this stays safe if React re-runs the updater.
  const open = useCallback((next: ActiveDialog) => {
    setActive((previous) => {
      if (previous) {
        if (previous.kind === 'confirm') previous.resolve(false);
        else previous.resolve(null);
      }
      return next;
    });
  }, []);

  const confirm = useCallback(
    (options: ConfirmOptions) =>
      new Promise<boolean>((resolve) => {
        open({ kind: 'confirm', options, resolve });
      }),
    [open],
  );

  const prompt = useCallback(
    (options: PromptOptions) =>
      new Promise<string | null>((resolve) => {
        open({ kind: 'prompt', options, resolve });
      }),
    [open],
  );

  const value = useMemo(() => ({ confirm, prompt }), [confirm, prompt]);

  const close = (result: { ok: boolean; text: string | null }) => {
    if (!active) return;
    if (active.kind === 'confirm') active.resolve(result.ok);
    else active.resolve(result.ok ? result.text : null);
    setActive(null);
  };

  return (
    <DialogContext.Provider value={value}>
      {children}
      {active ? <DialogView active={active} onClose={close} /> : null}
    </DialogContext.Provider>
  );
}

interface DialogViewProps {
  active: ActiveDialog;
  onClose: (result: { ok: boolean; text: string | null }) => void;
}

function DialogView({ active, onClose }: DialogViewProps) {
  const [text, setText] = useState(
    active.kind === 'prompt' ? (active.options.defaultValue ?? '') : '',
  );
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement>(null);

  // Move focus into the dialog so Escape and Enter work straight away.
  useEffect(() => {
    formRef.current?.focus();
  }, []);

  const isPrompt = active.kind === 'prompt';
  const requireText = active.kind === 'confirm' ? active.options.requireText : undefined;
  const confirmDisabled = requireText
    ? text.trim().toLowerCase() !== requireText.trim().toLowerCase()
    : false;
  const title = active.options.title;
  const message = active.options.message;
  const confirmLabel =
    active.options.confirmLabel ?? (isPrompt ? 'Save' : 'OK');
  const cancelLabel = active.options.cancelLabel ?? 'Cancel';

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (active.kind === 'prompt') {
      const value = text.trim();
      const min = active.options.minLength ?? 0;
      if (value.length < min) {
        setError(`Write at least ${min} characters.`);
        return;
      }
      onClose({ ok: true, text: value });
      return;
    }
    if (confirmDisabled) return;
    onClose({ ok: true, text: null });
  };

  const titleId = 'app-dialog-title';

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        // Clicking the backdrop dismisses, like Escape. Clicks inside the modal do not.
        if (e.target === e.currentTarget) onClose({ ok: false, text: null });
      }}
    >
      <form
        ref={formRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        onSubmit={submit}
        onKeyDown={(e) => {
          // Focus starts on the dialog, so Escape works even without an input.
          if (e.key === 'Escape') onClose({ ok: false, text: null });
        }}
        noValidate
      >
        <div className="modal__head">
          <h2 id={titleId} style={{ fontSize: 18, margin: 0 }}>
            {title}
          </h2>
        </div>
        <div className="modal__body">
          {message ? (
            <div className="muted" style={{ whiteSpace: 'pre-line' }}>
              {message}
            </div>
          ) : null}

          {isPrompt ? (
            <div className="field">
              <label htmlFor="app-dialog-input">{active.options.label}</label>
              {active.options.multiline ? (
                <textarea
                  id="app-dialog-input"
                  className="textarea"
                  rows={4}
                  autoFocus
                  placeholder={active.options.placeholder}
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value);
                    setError(null);
                  }}
                />
              ) : (
                <input
                  id="app-dialog-input"
                  className="input"
                  autoFocus
                  placeholder={active.options.placeholder}
                  value={text}
                  onChange={(e) => {
                    setText(e.target.value);
                    setError(null);
                  }}
                />
              )}
              {error ? <div className="error" role="alert">{error}</div> : null}
            </div>
          ) : requireText ? (
            <div className="field">
              <label htmlFor="app-dialog-input">
                Type <strong>{requireText}</strong> to confirm
              </label>
              <input
                id="app-dialog-input"
                className="input"
                autoFocus
                autoComplete="off"
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
            </div>
          ) : null}
        </div>
        <div className="modal__foot">
          <button
            type="button"
            className="btn btn--ghost"
            onClick={() => onClose({ ok: false, text: null })}
          >
            {cancelLabel}
          </button>
          <button
            type="submit"
            className={`btn ${active.options.danger ? 'btn--danger' : 'btn--primary'}`}
            disabled={confirmDisabled}
          >
            {confirmLabel}
          </button>
        </div>
      </form>
    </div>
  );
}

export function useDialog(): DialogContextValue {
  const ctx = useContext(DialogContext);
  if (!ctx) throw new Error('useDialog must be used within DialogProvider');
  return ctx;
}
