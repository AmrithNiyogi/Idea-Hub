import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Icon } from './Icons';

export type ToastKind = 'ok' | 'error';

type ToastItem = {
  id: number;
  message: string;
  kind: ToastKind;
};

interface ToastContextValue {
  toast: (message: string, kind?: ToastKind) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const DEFAULT_MS = 4200;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);
  const timers = useRef<Map<number, number>>(new Map());

  const dismiss = useCallback((id: number) => {
    const t = timers.current.get(id);
    if (t) window.clearTimeout(t);
    timers.current.delete(id);
    setItems((prev) => prev.filter((x) => x.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, kind: ToastKind = 'ok') => {
      const text = message.trim();
      if (!text) return;
      const id = ++seq.current;
      setItems((prev) => [...prev.slice(-4), { id, message: text, kind }]);
      const handle = window.setTimeout(() => dismiss(id), DEFAULT_MS);
      timers.current.set(id, handle);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" id="toast-root" aria-live="polite">
        {items.map((t) => (
          <div
            key={t.id}
            className={`toast ${t.kind === 'error' ? 'toast--error' : 'toast--ok'}`}
            role={t.kind === 'error' ? 'alert' : 'status'}
          >
            <Icon
              name={t.kind === 'error' ? 'alert' : 'checkcircle'}
              size={16}
              className="icon"
            />
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
