/** Ideathon / Hackathon selector, as chips (same pattern as Integrations filters). */
import { EVENT_KIND_LABEL } from '../../constants/ideathons';
import type { EventKind } from '../../types/ideathon';

const HINT: Record<EventKind, string> = {
  ideathon: 'Entries are ideas. A GitHub link and documents are optional.',
  hackathon: 'Entries are built projects. Each needs a GitHub repository and at least one document.',
};

interface Props {
  value: EventKind;
  onChange: (kind: EventKind) => void;
  disabled?: boolean;
}

export function EventKindChips({ value, onChange, disabled }: Props) {
  return (
    <div className="field">
      <span className="label" id="event-kind-label">
        Event type
      </span>
      <div className="chip-row" role="group" aria-labelledby="event-kind-label">
        {(Object.keys(EVENT_KIND_LABEL) as EventKind[]).map((k) => (
          <button
            key={k}
            type="button"
            className="chip-link"
            aria-pressed={value === k}
            aria-current={value === k ? 'true' : undefined}
            disabled={disabled}
            onClick={() => onChange(k)}
          >
            {EVENT_KIND_LABEL[k]}
          </button>
        ))}
      </div>
      <span className="hint">{HINT[value]}</span>
    </div>
  );
}
