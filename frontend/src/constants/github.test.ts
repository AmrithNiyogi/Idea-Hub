import { describe, expect, it } from 'vitest';
import { GITHUB_REPO_PATTERN } from './github';

describe('GITHUB_REPO_PATTERN', () => {
  it.each([
    'https://github.com/acme/ideas-hub',
    'https://github.com/acme/ideas-hub/',
  ])('accepts a single repository link: %s', (url) => {
    expect(GITHUB_REPO_PATTERN.test(url)).toBe(true);
  });

  it.each([
    'http://github.com/acme/repo',
    'https://gitlab.com/acme/repo',
    'https://github.com/acme',
    'https://github.com/acme/repo/tree/main',
    'https://github.com.evil.example/acme/repo',
  ])('rejects anything else: %s', (url) => {
    expect(GITHUB_REPO_PATTERN.test(url)).toBe(false);
  });
});
