/**
 * Journey stepper: every stage shows what moves it on and who owns that move,
 * so a person can read the whole path from the current stage to the end.
 */
import type { ReactNode } from 'react';
import { Icon } from '../Icons';

export interface JourneyStage {
  label: string;
  /** What has to happen before the item moves to the next stage. */
  gate: string;
  /** Who makes that happen. */
  owner: string;
}

interface Props {
  stages: JourneyStage[];
  /** Index of the stage the item is in. */
  current: number;
  /** True when the whole journey is finished (every stage done). */
  finished?: boolean;
  /** Optional per-stage date line, shown once the stage has been reached. */
  when?: (index: number) => string | undefined;
  /** Current situation shown under the track. */
  now?: ReactNode;
  ariaLabel: string;
  /** Marks the current stage as stopped (declined, withdrawn) or paused (parked). */
  tone?: 'normal' | 'stopped' | 'paused';
}

export function JourneyStepper({
  stages,
  current,
  finished = false,
  when,
  now,
  ariaLabel,
  tone = 'normal',
}: Props) {
  return (
    <div className="journey">
      <ol className="journey__track" aria-label={ariaLabel}>
        {stages.map((s, i) => {
          const done = finished || i < current;
          const isCurrent = !finished && i === current;
          const cls = [
            'journey__stage',
            done ? 'is-done' : '',
            isCurrent ? 'is-current' : '',
            isCurrent && tone !== 'normal' ? `is-${tone}` : '',
          ]
            .filter(Boolean)
            .join(' ');
          const date = i <= current || finished ? when?.(i) : undefined;
          return (
            <li
              key={s.label}
              className={cls}
              aria-current={isCurrent ? 'step' : undefined}
            >
              <span className="journey__dot" aria-hidden="true">
                {done ? <Icon name="check" size={14} /> : i + 1}
              </span>
              <span className="journey__label">{s.label}</span>
              {date ? <span className="journey__date">{date}</span> : null}
              {!done && !isCurrent ? (
                <span className="journey__gate">{s.gate}</span>
              ) : null}
              {isCurrent && !finished ? (
                <span className="journey__gate journey__gate--now">
                  {s.gate}
                </span>
              ) : null}
              <span className="journey__owner">
                {done ? 'Done' : `Owner: ${s.owner}`}
              </span>
            </li>
          );
        })}
      </ol>
      {now ? <div className="journey__now">{now}</div> : null}
    </div>
  );
}
