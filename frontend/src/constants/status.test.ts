import { describe, expect, it } from 'vitest';
import { EFFORT_LABELS, STAGE_KEYS, STAGE_LABELS, STATUS_META, TAG_VOCAB } from './status';

describe('status constants', () => {
  it('exposes full status map and stage vocab', () => {
    expect(STATUS_META.submitted.label).toBe('Submitted');
    expect(STAGE_KEYS).toHaveLength(STAGE_LABELS.length);
    expect(EFFORT_LABELS.M).toMatch(/weeks/i);
    expect(TAG_VOCAB).toContain('ci-cd');
  });
});
