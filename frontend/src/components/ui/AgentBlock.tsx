/** Agent callout matching idea-hub.html `agentBlock()`. */

import type { ReactNode } from 'react';
import { Icon } from '../Icons';

export function AgentBlock({
  agent,
  kind,
  how,
  children,
}: {
  agent: string;
  kind: string;
  how: string;
  children?: ReactNode;
}) {
  return (
    <aside className="agent">
      <div className="agent__head">
        <Icon name="spark" size={16} />
        <span className="agent__name">{agent}</span>
        <span className="pill pill--agent">Simulated</span>
        <span className="agent__kind">{kind}</span>
      </div>
      <div className="agent__body">{children}</div>
      <div className="agent__foot">{how}</div>
    </aside>
  );
}
