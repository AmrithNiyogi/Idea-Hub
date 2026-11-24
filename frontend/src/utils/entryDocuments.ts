/** Client-side checks for entry documents. The backend enforces the same limits. */

export const DOC_MAX_FILES = 5;
export const DOC_MAX_BYTES = 10 * 1024 * 1024;
export const DOC_EXTENSIONS = ['.pdf', '.md', '.txt', '.docx'] as const;
export const DOC_ACCEPT = DOC_EXTENSIONS.join(',');

function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot >= 0 ? name.slice(dot).toLowerCase() : '';
}

/**
 * Returns an error message for the first file that breaks a rule, or null.
 * `alreadyAttached` counts documents saved on the idea before this pick.
 */
export function validateDocuments(
  files: Array<Pick<File, 'name' | 'size'>>,
  alreadyAttached = 0,
): string | null {
  if (files.length + alreadyAttached > DOC_MAX_FILES) {
    return `You can attach up to ${DOC_MAX_FILES} documents.`;
  }
  for (const f of files) {
    if (!(DOC_EXTENSIONS as readonly string[]).includes(extensionOf(f.name))) {
      return `${f.name}: use PDF, Markdown, TXT or DOCX.`;
    }
    if (f.size === 0) return `${f.name} is empty.`;
    if (f.size > DOC_MAX_BYTES) return `${f.name} is larger than 10 MB.`;
  }
  return null;
}

/** Human file size, e.g. "1.2 MB". */
export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

/** GitHub is required for hackathon entries. Returns a message or null. */
export function hackathonGithubError(githubUrl: string | null | undefined): string | null {
  return (githubUrl ?? '').trim()
    ? null
    : 'Hackathon entries need a GitHub repository link (https://github.com/owner/repo).';
}

/** All client-side rules for a hackathon entry before submit. Returns a message or null. */
export function hackathonEntryError(
  githubUrl: string | null | undefined,
  files: Array<Pick<File, 'name' | 'size'>>,
): string | null {
  const gh = hackathonGithubError(githubUrl);
  if (gh) return gh;
  if (!files.length) {
    return 'Hackathon entries need at least one documentation file (PDF, Markdown, TXT or DOCX).';
  }
  return validateDocuments(files);
}
