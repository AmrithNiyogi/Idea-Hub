import { STATUS_META } from '../constants/status';
import type { IdeaStatus } from '../types/idea';

const VARIANT_CLASS: Record<string, string> = {
  brand: 'pill--brand',
  info: 'pill--info',
  success: 'pill--success',
  warning: 'pill--warning',
  danger: 'pill--danger',
  gold: 'pill--gold',
  neutral: '',
};

/** Dot colour per status variant so pills read as multi-hue, not purple-only. */
const VARIANT_DOT: Record<string, string> = {
  brand: 'var(--brand)',
  info: 'var(--info)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  danger: 'var(--danger)',
  gold: 'var(--gold)',
  neutral: 'var(--text-3)',
};

export function StatusPill({ status }: { status: string }) {
  const meta = STATUS_META[status as IdeaStatus];
  const label = meta?.label ?? status;
  const variant = meta?.variant ?? 'neutral';
  const cls = VARIANT_CLASS[variant] ?? '';
  const dot = VARIANT_DOT[variant] ?? VARIANT_DOT.neutral;
  return (
    <span className={`pill ${cls}`.trim()}>
      <i className="dot" style={{ background: dot }} aria-hidden="true" />
      {label}
    </span>
  );
}
