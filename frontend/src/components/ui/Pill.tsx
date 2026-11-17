/** Status / label pill matching idea-hub.html `pill()`. */

import type { ReactNode } from 'react';
import { Icon } from '../Icons';

const VARIANT: Record<string, string> = {
  brand: 'pill--brand',
  info: 'pill--info',
  success: 'pill--success',
  warning: 'pill--warning',
  danger: 'pill--danger',
  gold: 'pill--gold',
  agent: 'pill--agent',
};

export function Pill({
  children,
  variant = '',
  icon,
  title,
}: {
  children: ReactNode;
  variant?: string;
  icon?: string;
  title?: string;
}) {
  const cls = VARIANT[variant] ?? '';
  return (
    <span className={`pill ${cls}`.trim()} title={title}>
      {icon ? <Icon name={icon} size={12} /> : null}
      {children}
    </span>
  );
}
