import { describe, expect, it } from 'vitest';
import {
  DOC_MAX_BYTES,
  formatBytes,
  hackathonEntryError,
  hackathonGithubError,
  validateDocuments,
} from './entryDocuments';

const file = (name: string, size = 100) => ({ name, size });

describe('entry document rules', () => {
  it('accepts PDF, Markdown, TXT and DOCX', () => {
    expect(
      validateDocuments([file('a.pdf'), file('b.MD'), file('c.txt'), file('d.docx')]),
    ).toBeNull();
  });

  it('rejects other types, empty files and files over 10 MB', () => {
    expect(validateDocuments([file('a.exe')])).toMatch(/PDF, Markdown/);
    expect(validateDocuments([file('noext')])).toMatch(/PDF, Markdown/);
    expect(validateDocuments([file('a.pdf', 0)])).toMatch(/empty/);
    expect(validateDocuments([file('a.pdf', DOC_MAX_BYTES + 1)])).toMatch(/10 MB/);
  });

  it('counts documents already attached toward the limit of five', () => {
    expect(validateDocuments([file('a.pdf'), file('b.pdf')], 4)).toMatch(/up to 5/);
    expect(validateDocuments([file('a.pdf')], 4)).toBeNull();
  });

  it('formats sizes', () => {
    expect(formatBytes(512)).toBe('512 B');
    expect(formatBytes(2048)).toBe('2 KB');
    expect(formatBytes(3 * 1024 * 1024)).toBe('3.0 MB');
  });
});

describe('hackathon entry validation', () => {
  it('requires a GitHub link', () => {
    expect(hackathonGithubError('')).toMatch(/GitHub repository/);
    expect(hackathonGithubError(null)).toMatch(/GitHub repository/);
    expect(hackathonGithubError('https://github.com/a/b')).toBeNull();
    expect(hackathonEntryError('  ', [file('a.pdf')])).toMatch(/GitHub/);
  });

  it('requires at least one valid document', () => {
    expect(hackathonEntryError('https://github.com/a/b', [])).toMatch(/at least one/);
    expect(hackathonEntryError('https://github.com/a/b', [file('a.zip')])).toMatch(/PDF/);
    expect(hackathonEntryError('https://github.com/a/b', [file('a.pdf')])).toBeNull();
  });
});
