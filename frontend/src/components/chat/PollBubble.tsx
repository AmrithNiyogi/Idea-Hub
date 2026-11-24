/**
 * Poll rendered inside a group chat transcript (Discord poll card + WhatsApp bubble).
 * Options show a vote bar and a radio (pick one) or checkbox (pick several) marker.
 */

import type { GroupPoll } from '../../types/groups';
import { relTime } from '../../utils/format';

type Props = {
  poll: GroupPoll | undefined;
  senderName: string;
  mine: boolean;
  createdAt: string;
  canVote: boolean;
  canClose: boolean;
  busy: boolean;
  onVote: (optionIndex: number) => void;
  onClose: () => void;
};

export function PollBubble({
  poll,
  senderName,
  mine,
  createdAt,
  canVote,
  canClose,
  busy,
  onVote,
  onClose,
}: Props) {
  const cls = `ts-bubble ts-bubble--poll ${mine ? 'ts-bubble--mine' : 'ts-bubble--theirs'}`;

  if (!poll) {
    return (
      <div className={cls}>
        {!mine ? <div className="ts-bubble__sender">{senderName}</div> : null}
        <div className="poll-card__question muted small">Poll unavailable</div>
        <div className="ts-bubble__time">{relTime(createdAt)}</div>
      </div>
    );
  }

  const closed = !!poll.closed_at;
  const total = poll.total_votes;
  const kind = poll.multi_select ? 'Select one or more' : 'Select one';

  return (
    <div className={cls}>
      {!mine ? <div className="ts-bubble__sender">{senderName}</div> : null}
      <div className="poll-card">
        <div className="poll-card__eyebrow">Poll</div>
        <div className="poll-card__question">{poll.question}</div>
        <ul className="poll-card__options">
          {poll.options.map((label, i) => {
            const count = poll.counts[i] ?? 0;
            const pct = total ? Math.round((count / total) * 100) : 0;
            const picked = poll.my_votes.includes(i);
            const disabled = closed || !canVote || busy;
            return (
              <li key={i}>
                <button
                  type="button"
                  className={`poll-card__opt${picked ? ' is-picked' : ''}`}
                  role={poll.multi_select ? 'checkbox' : 'radio'}
                  aria-checked={picked}
                  disabled={disabled}
                  onClick={() => onVote(i)}
                >
                  <span className="poll-card__bar" style={{ width: `${pct}%` }} aria-hidden />
                  <span
                    className={`poll-card__mark${poll.multi_select ? ' is-check' : ''}${picked ? ' is-on' : ''}`}
                    aria-hidden
                  />
                  <span className="poll-card__label">{label}</span>
                  <span className="poll-card__count">{count}</span>
                </button>
              </li>
            );
          })}
        </ul>
        <div className="poll-card__foot">
          <span>
            {closed ? 'Poll closed' : kind} · {total} vote{total === 1 ? '' : 's'}
          </span>
          {canClose && !closed ? (
            <button type="button" className="poll-card__close" disabled={busy} onClick={onClose}>
              Close
            </button>
          ) : null}
        </div>
      </div>
      <div className="ts-bubble__time">{relTime(createdAt)}</div>
    </div>
  );
}

export default PollBubble;
