/**
 * In-app guide. Walks through the app one page at a time. The guide stays
 * open while you move between pages: Next, Back and the page button all
 * navigate and keep the guide on screen. Progress is kept for the browser
 * session, so a reload resumes the same step.
 *
 * Shown once per user in this browser on first visit, and replayable from
 * the account menu (dispatches GUIDE_REPLAY_EVENT). Only local flags are
 * stored; nothing is sent to the server.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/AuthProvider';
import { Icon } from '../Icons';

export const GUIDE_REPLAY_EVENT = 'ih:guide-replay';
const STEP_KEY = 'ih.guide.step';

interface Step {
  title: string;
  body: string;
  /** The page this step is about. The guide opens it. */
  to: string;
  /** Short label for the button that opens the page. */
  pageLabel: string;
}

function stepsFor(canReview: boolean): Step[] {
  const steps: Step[] = [
    {
      title: 'Welcome to Idea Hub',
      body: 'Ideas move from shaping to review, build and recognition. The sidebar follows that order, so you can see where you are in the journey. This guide walks you through each part, one page at a time.',
      to: '/',
      pageLabel: 'Open Home',
    },
    {
      title: 'Start an idea',
      body: 'Use New idea in the top bar, or the button on this page. A complete idea earns points, and reviewers see it in their queue.',
      to: '/submit',
      pageLabel: 'Open the idea form',
    },
    {
      title: 'Find ideas to join',
      body: 'Explore lists every idea in the company. Upvote, follow or offer to help with the ones you care about.',
      to: '/explore',
      pageLabel: 'Open Explore',
    },
    {
      title: 'Track your own ideas',
      body: 'My ideas shows what you submitted and whether it needs anything from you, such as an answer to a reviewer.',
      to: '/my',
      pageLabel: 'Open My ideas',
    },
  ];
  if (canReview) {
    steps.push({
      title: 'Review',
      body: 'The review queue lists ideas waiting for a decision. Every decision needs a written reason.',
      to: '/review',
      pageLabel: 'Open the review queue',
    });
  }
  steps.push(
    {
      title: 'Recognition',
      body: 'Points come from outcomes and collaboration, never from the number of ideas. My standing shows the ways to earn, and Say thanks lets you recognise a teammate.',
      to: '/recognition?tab=standing',
      pageLabel: 'Open My standing',
    },
    {
      title: 'Help when you need it',
      body: 'Look for the (i) buttons. They explain a term where you meet it. The chat button in the corner answers questions about the app. You can replay this guide from the account menu.',
      to: '/',
      pageLabel: 'Back to Home',
    },
  );
  return steps;
}

function readStep(max: number): number {
  try {
    const n = Number(window.sessionStorage.getItem(STEP_KEY) ?? 0);
    return Number.isFinite(n) ? Math.min(Math.max(0, n), max) : 0;
  } catch {
    return 0;
  }
}

function writeStep(n: number): void {
  try {
    window.sessionStorage.setItem(STEP_KEY, String(n));
  } catch {
    /* ignore: the guide restarts at step one after a reload */
  }
}

export function GuideTour() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const storageKey = user ? `ih.guide.v1.${user.id}` : null;
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(() => readStep(20));

  useEffect(() => {
    if (!storageKey) return;
    try {
      if (!window.localStorage.getItem(storageKey)) setOpen(true);
    } catch {
      /* storage unavailable: no first-visit guide */
    }
  }, [storageKey]);

  useEffect(() => {
    const replay = () => {
      setStep(0);
      writeStep(0);
      setOpen(true);
    };
    window.addEventListener(GUIDE_REPLAY_EVENT, replay);
    return () => window.removeEventListener(GUIDE_REPLAY_EVENT, replay);
  }, []);

  if (!open || !user) return null;

  const canReview = ['reviewer', 'admin'].includes(user.active_role);
  const steps = stepsFor(canReview);
  const index = Math.min(step, steps.length - 1);
  const current = steps[index];
  const last = index >= steps.length - 1;

  const goTo = (n: number) => {
    const next = Math.min(Math.max(0, n), steps.length - 1);
    setStep(next);
    writeStep(next);
    navigate(steps[next].to);
  };

  const close = () => {
    setOpen(false);
    writeStep(0);
    try {
      if (storageKey) window.localStorage.setItem(storageKey, '1');
    } catch {
      /* ignore: the guide simply shows again next visit */
    }
  };

  return (
    <aside className="guide" aria-label="Idea Hub guide">
      <div className="guide__head">
        <span className="guide__count">
          Step {index + 1} of {steps.length}
        </span>
        <button type="button" className="guide__close" onClick={close} aria-label="Close guide">
          <Icon name="x" size={16} />
        </button>
      </div>

      <div className="guide__progress" aria-hidden="true">
        {steps.map((s, i) => (
          <span key={s.title} className={i <= index ? 'is-reached' : ''} />
        ))}
      </div>

      <h2 className="guide__title">{current.title}</h2>
      <p className="guide__body">{current.body}</p>

      <button type="button" className="btn btn--sm guide__page" onClick={() => goTo(index)}>
        {current.pageLabel}
        <Icon name="arrowRight" size={14} />
      </button>

      <details className="guide__steps">
        <summary>All steps</summary>
        <ol>
          {steps.map((s, i) => (
            <li key={s.title}>
              <button
                type="button"
                className={i === index ? 'is-current' : ''}
                onClick={() => goTo(i)}
              >
                {s.title}
              </button>
            </li>
          ))}
        </ol>
      </details>

      <div className="guide__foot">
        <button type="button" className="btn btn--ghost btn--sm" onClick={close}>
          {last ? 'Done' : 'Skip guide'}
        </button>
        <div className="guide__nav">
          <button
            type="button"
            className="btn btn--sm"
            onClick={() => goTo(index - 1)}
            disabled={index === 0}
          >
            Back
          </button>
          <button
            type="button"
            className="btn btn--sm btn--primary"
            onClick={() => (last ? close() : goTo(index + 1))}
          >
            {last ? 'Finish' : 'Next'}
          </button>
        </div>
      </div>
    </aside>
  );
}
