/**
 * Local SVG / letter marks for Integrations gallery — no external CDN.
 * Simplified brand-inspired marks; polished enough for the tile grid.
 */

import type { ReactNode } from 'react';

type LogoProps = {
  providerId: string;
  size?: number;
  className?: string;
};

const MARK: Record<
  string,
  { bg: string; fg: string; label: string }
> = {
  clickup: { bg: '#7B68EE', fg: '#FFFFFF', label: 'ClickUp' },
  jira: { bg: '#2684FF', fg: '#FFFFFF', label: 'Jira' },
  custom_webhook: { bg: 'var(--surface-3)', fg: 'var(--text)', label: 'Webhook' },
  google_sheets: { bg: '#0F9D58', fg: '#FFFFFF', label: 'Sheets' },
  notion: { bg: '#191919', fg: '#FFFFFF', label: 'Notion' },
  teams: { bg: '#5059C9', fg: '#FFFFFF', label: 'Teams' },
};

function ClickUpMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#7B68EE" />
      <path
        d="M10 16.5c2.8 4.2 6.2 7 10 7s7.2-2.8 10-7"
        fill="none"
        stroke="#fff"
        strokeWidth="3.2"
        strokeLinecap="round"
      />
      <path
        d="M14 14c1.8 2.6 3.8 4.2 6 4.2s4.2-1.6 6-4.2"
        fill="none"
        stroke="#FF77CC"
        strokeWidth="2.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function JiraMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#2684FF" />
      <path
        d="M20 8c0 6.6-5.4 12-12 12 6.6 0 12 5.4 12 12 0-6.6 5.4-12 12-12-6.6 0-12-5.4-12-12z"
        fill="#fff"
      />
      <path
        d="M20 14.5c0 3.6-2.9 6.5-6.5 6.5 3.6 0 6.5 2.9 6.5 6.5 0-3.6 2.9-6.5 6.5-6.5-3.6 0-6.5-2.9-6.5-6.5z"
        fill="#0052CC"
        opacity="0.85"
      />
    </svg>
  );
}

function WebhookMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="var(--surface-3)" />
      <g
        fill="none"
        stroke="var(--text)"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="13" cy="14" r="3.2" />
        <circle cx="27" cy="14" r="3.2" />
        <circle cx="20" cy="27" r="3.2" />
        <path d="M16 15.5l2.2 7.2M24 15.5l-2.2 7.2M16.2 14h7.6" />
      </g>
    </svg>
  );
}

function SheetsMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#0F9D58" />
      <rect x="10" y="9" width="20" height="22" rx="2" fill="#fff" />
      <path d="M10 16h20M10 23h20M20 9v22" stroke="#0F9D58" strokeWidth="1.8" />
      <rect x="10" y="9" width="20" height="5" fill="#34A853" opacity="0.35" />
    </svg>
  );
}

function NotionMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#191919" />
      <path
        d="M13.5 11h10.2c.6 0 1.1.2 1.6.7l3.2 3.6c.4.4.5.9.5 1.4V29H15.8c-1.3 0-2.3-1-2.3-2.3V11z"
        fill="#fff"
      />
      <path
        d="M17.2 15.2h2.2v11.2h-2.8l5.8-11.2h2.4v11.2"
        fill="none"
        stroke="#191919"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TeamsMark({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill="#5059C9" />
      <rect x="9" y="14" width="14" height="14" rx="2.5" fill="#7B83EB" />
      <text
        x="16"
        y="25"
        textAnchor="middle"
        fill="#fff"
        fontSize="11"
        fontWeight="700"
        fontFamily="var(--font-sans), sans-serif"
      >
        T
      </text>
      <circle cx="27" cy="13" r="4" fill="#fff" />
      <rect x="23" y="18" width="9" height="10" rx="4.5" fill="#fff" opacity="0.92" />
    </svg>
  );
}

function LetterMark({
  size,
  bg,
  fg,
  letter,
}: {
  size: number;
  bg: string;
  fg: string;
  letter: string;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden="true">
      <rect width="40" height="40" rx="10" fill={bg} />
      <text
        x="20"
        y="26"
        textAnchor="middle"
        fill={fg}
        fontSize="16"
        fontWeight="700"
        fontFamily="var(--font-sans), sans-serif"
      >
        {letter}
      </text>
    </svg>
  );
}

export function IntegrationLogo({
  providerId,
  size = 40,
  className,
}: LogoProps) {
  const known = MARK[providerId];
  let mark: ReactNode;
  switch (providerId) {
    case 'clickup':
      mark = <ClickUpMark size={size} />;
      break;
    case 'jira':
      mark = <JiraMark size={size} />;
      break;
    case 'custom_webhook':
      mark = <WebhookMark size={size} />;
      break;
    case 'google_sheets':
      mark = <SheetsMark size={size} />;
      break;
    case 'notion':
      mark = <NotionMark size={size} />;
      break;
    case 'teams':
      mark = <TeamsMark size={size} />;
      break;
    default:
      mark = (
        <LetterMark
          size={size}
          bg={known?.bg ?? 'var(--brand-soft)'}
          fg={known?.fg ?? 'var(--brand-ink)'}
          letter={(providerId[0] || '?').toUpperCase()}
        />
      );
  }

  return (
    <span
      className={`integ-logo${className ? ` ${className}` : ''}`}
      style={{ width: size, height: size }}
      role="img"
      aria-label={known?.label ?? providerId}
    >
      {mark}
    </span>
  );
}
