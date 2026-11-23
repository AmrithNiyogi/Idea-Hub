/**
 * Status line shown while an agent runs: a spinner, a label, and the seconds waited.
 * The backend returns one reply at the end, so this shows no progress. The counter is real.
 */
import { useEffect, useState } from 'react';

export function AgentWaiting({ label }: { label: string }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const id = window.setInterval(() => {
      setSeconds(Math.floor((Date.now() - started) / 1000));
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <div className="agent-waiting" role="status" aria-live="polite">
      <span className="agent-waiting__spinner" aria-hidden="true" />
      <span className="agent-waiting__label">{label}</span>
      <span className="agent-waiting__time">{seconds}s</span>
    </div>
  );
}
