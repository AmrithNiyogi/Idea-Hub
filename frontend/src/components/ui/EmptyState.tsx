/** Empty-state block matching idea-hub.html `emptyState()`. */

import type { ReactNode } from 'react';
import { Icon } from '../Icons';

export function EmptyState({
  icon = 'inbox',
  title,
  body,
  action,
}: {
  icon?: string;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <Icon name={icon} size={32} />
      <h3>{title}</h3>
      {body ? <p className="muted">{body}</p> : null}
      {action}
    </div>
  );
}
