/**
 * Small info button that explains a term where people meet it.
 * Opens on click, closes on outside click or Escape. Text stays short.
 */
import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { Icon } from '../Icons';

interface Props {
  label: string;
  children: ReactNode;
}

export function InfoTip({ label, children }: Props) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <span className="infotip" ref={ref}>
      <button
        type="button"
        className="infotip__btn"
        aria-label={label}
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
      >
        <Icon name="info" size={14} />
      </button>
      {open ? (
        <span id={id} role="tooltip" className="infotip__pop">
          {children}
        </span>
      ) : null}
    </span>
  );
}
