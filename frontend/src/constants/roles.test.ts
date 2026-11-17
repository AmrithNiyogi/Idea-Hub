import { describe, expect, it } from 'vitest';
import { ROLE_LABELS, roleLabel, sortRoles } from './roles';

describe('roles helpers', () => {
  it('maps known roles and falls back for unknown', () => {
    expect(roleLabel('admin')).toBe(ROLE_LABELS.admin);
    expect(roleLabel('mystery')).toBe('mystery');
  });

  it('sorts roles by ROLE_ORDER', () => {
    expect(sortRoles(['admin', 'contributor', 'reviewer'])).toEqual([
      'contributor',
      'reviewer',
      'admin',
    ]);
  });
});
