import { describe, expect, it } from 'vitest';
import {
  fmtClock,
  fmtDate,
  fmtNum,
  ithPhaseIdx,
  ithStatus,
  quarterKey,
  quarterLabel,
} from './ideathons';

describe('ideathon constants helpers', () => {
  it('resolves phase index', () => {
    expect(ithPhaseIdx('pitch')).toBe(2);
    expect(ithPhaseIdx('nope')).toBe(0);
  });

  it('computes status from dates', () => {
    const now = new Date('2026-06-15T12:00:00Z').getTime();
    expect(ithStatus('2026-01-01', '2026-12-31', '2026-05-01', now)).toBe('past');
    expect(ithStatus('2026-07-01', '2026-08-01', null, now)).toBe('upcoming');
    expect(ithStatus('2026-01-01', '2026-06-01', null, now)).toBe('active');
    expect(ithStatus('2026-01-01', '2026-12-31', null, now)).toBe('active');
  });

  it('formats dates, numbers, and clocks', () => {
    expect(fmtDate('bogus')).toBe('—');
    expect(fmtDate('2026-03-04T00:00:00Z', true)).toMatch(/Mar/);
    expect(fmtNum(1234.6)).toMatch(/1/);
    expect(fmtClock(125)).toBe('2:05');
    expect(fmtClock(-1)).toBe('0:00');
  });

  it('quarter helpers', () => {
    expect(quarterKey(new Date('2026-04-02'))).toBe('2026-Q2');
    expect(quarterLabel('2026-Q3')).toBe('Jul–Sep 2026');
    expect(quarterLabel('bad')).toBe('bad');
  });
});
