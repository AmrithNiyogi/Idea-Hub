/** KPI tile matching idea-hub.html `kpi()`. */

const TONE_CLASS: Record<string, string> = {
  accent: 'kpi--accent',
  info: 'kpi--info',
  success: 'kpi--success',
  warning: 'kpi--warning',
  danger: 'kpi--danger',
  gold: 'kpi--gold',
};

export function Kpi({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string | number;
  sub?: string;
  /** Optional value colour — gold for recognition, success for delivered, etc. */
  tone?: keyof typeof TONE_CLASS | string;
}) {
  const toneCls = tone ? TONE_CLASS[tone] ?? '' : '';
  return (
    <div className={`kpi ${toneCls}`.trim()}>
      <span className="kpi__label">{label}</span>
      <span className="kpi__value">{value}</span>
      {sub ? <span className="kpi__sub">{sub}</span> : null}
    </div>
  );
}
