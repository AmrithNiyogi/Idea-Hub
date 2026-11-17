import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  firstName,
  fmtDate,
  greeting,
  nextStep,
  relTime,
  trunc,
} from './format';
import { makeIdea } from '../test/fixtures';

describe('relTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-15T12:00:00.000Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns em dash for empty or invalid', () => {
    expect(relTime(null)).toBe('—');
    expect(relTime(undefined)).toBe('—');
    expect(relTime('not-a-date')).toBe('—');
  });

  it('formats minutes, hours, days, and older dates', () => {
    expect(relTime('2026-06-15T11:59:30.000Z')).toBe('just now');
    expect(relTime('2026-06-15T11:45:00.000Z')).toBe('15m ago');
    expect(relTime('2026-06-15T08:00:00.000Z')).toBe('4h ago');
    expect(relTime('2026-06-10T12:00:00.000Z')).toBe('5d ago');
    expect(relTime('2026-01-01T12:00:00.000Z')).toMatch(/\d/);
  });
});

describe('fmtDate', () => {
  it('handles missing / invalid and year flag', () => {
    expect(fmtDate(null)).toBe('—');
    expect(fmtDate('bogus')).toBe('—');
    const withYear = fmtDate('2026-03-04T00:00:00.000Z', true);
    expect(withYear).toMatch(/Mar/);
    expect(withYear).toMatch(/2026|4/);
  });
});

describe('greeting / firstName / trunc', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it('greets by hour of day', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-06-15T08:00:00'));
    expect(greeting()).toBe('Good morning');
    vi.setSystemTime(new Date('2026-06-15T14:00:00'));
    expect(greeting()).toBe('Good afternoon');
    vi.setSystemTime(new Date('2026-06-15T20:00:00'));
    expect(greeting()).toBe('Good evening');
  });

  it('firstName falls back to there', () => {
    expect(firstName('Alice Example')).toBe('Alice');
    expect(firstName('')).toBe('there');
    expect(firstName(null)).toBe('there');
    expect(firstName('   ')).toBe('there');
  });

  it('truncates with ellipsis', () => {
    expect(trunc('hi', 10)).toBe('hi');
    expect(trunc('hello world', 8)).toBe('hello w…');
    expect(trunc('', 3)).toBe('');
  });
});

describe('nextStep', () => {
  it('covers lifecycle statuses', () => {
    expect(nextStep(makeIdea({ status: 'draft' })).who).toBe('Author');
    expect(nextStep(makeIdea({ status: 'submitted' })).who).toBe('Review panel');
    expect(nextStep(makeIdea({ status: 'under_review' })).text).toMatch(/awaiting pickup/);
    expect(
      nextStep(makeIdea({ status: 'under_review', picked_up_at: '2026-01-02T00:00:00Z' }))
        .text,
    ).toMatch(/scoring/);
    expect(
      nextStep(
        makeIdea({ status: 'needs_info', needs_info_question: 'What metrics?' }),
      ).text,
    ).toContain('What metrics?');
    expect(nextStep(makeIdea({ status: 'needs_info' })).text).toMatch(/question/);
    expect(nextStep(makeIdea({ status: 'accepted' })).who).toBe('Team lead');
    expect(
      nextStep(makeIdea({ status: 'accepted', owner_id: 'u2' })).who,
    ).toBe('Owner');
    expect(
      nextStep(makeIdea({ status: 'parked', revisit_at: '2026-07-01T00:00:00Z' })).text,
    ).toMatch(/Parked until/);
    expect(nextStep(makeIdea({ status: 'parked' })).text).toMatch(/Waiting/);
    expect(
      nextStep(makeIdea({ status: 'merged', merged_into_id: 'x' })).text,
    ).toMatch(/credited/);
    expect(nextStep(makeIdea({ status: 'merged' })).text).toMatch(/Merged/);
    expect(nextStep(makeIdea({ status: 'declined' })).who).toBe('—');
    expect(nextStep(makeIdea({ status: 'prototype' })).who).toBe('Owner');
    expect(nextStep(makeIdea({ status: 'implemented' })).text).toMatch(/Delivered/);
    expect(nextStep(makeIdea({ status: 'withdrawn' })).text).toMatch(/Withdrawn/);
    expect(nextStep(makeIdea({ status: 'unknown' as never })).text).toMatch(
      /See the idea page/,
    );
  });
});

