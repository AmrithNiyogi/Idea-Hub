/** Pick documentation files to upload with an entry. Files are uploaded after the idea is submitted. */
import { useId, useState } from 'react';
import { Icon } from '../Icons';
import {
  DOC_ACCEPT,
  DOC_MAX_FILES,
  formatBytes,
  validateDocuments,
} from '../../utils/entryDocuments';

interface Props {
  files: File[];
  onChange: (files: File[]) => void;
  required?: boolean;
  disabled?: boolean;
}

export function EntryDocumentsPicker({ files, onChange, required, disabled }: Props) {
  const inputId = useId();
  const [error, setError] = useState<string | null>(null);

  const add = (picked: FileList | null) => {
    if (!picked || !picked.length) return;
    const incoming = Array.from(picked);
    const problem = validateDocuments(incoming, files.length);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    onChange([...files, ...incoming]);
  };

  return (
    <div className="field entry-docs">
      <label htmlFor={inputId}>
        Documentation {required ? '(at least one, required for hackathons)' : '(optional)'}
      </label>
      <input
        id={inputId}
        className="input"
        type="file"
        accept={DOC_ACCEPT}
        multiple
        disabled={disabled || files.length >= DOC_MAX_FILES}
        onChange={(e) => {
          add(e.target.files);
          e.target.value = '';
        }}
      />
      {error ? (
        <div className="error" role="alert">
          {error}
        </div>
      ) : (
        <div className="hint">
          PDF, Markdown, TXT or DOCX. Up to {DOC_MAX_FILES} files, 10 MB each. The AI
          reviewer reads these to understand the project.
        </div>
      )}
      {files.length ? (
        <ul className="entry-docs__list">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="entry-docs__row">
              <span className="entry-docs__name">{f.name}</span>
              <span className="muted small">{formatBytes(f.size)}</span>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                aria-label={`Remove ${f.name}`}
                disabled={disabled}
                onClick={() => onChange(files.filter((_, j) => j !== i))}
              >
                <Icon name="x" size={14} />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export default EntryDocumentsPicker;
