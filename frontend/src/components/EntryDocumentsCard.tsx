/** Documents attached to an idea. Everyone who can see the idea can download; authors can add or remove. */
import { useCallback, useEffect, useId, useState } from 'react';
import { documentsApi } from '../api/documents';
import type { EntryDocument } from '../types/idea';
import {
  DOC_ACCEPT,
  DOC_MAX_FILES,
  formatBytes,
  validateDocuments,
} from '../utils/entryDocuments';
import { Icon } from './Icons';

interface Props {
  ideaId: string;
  canEdit: boolean;
}

export function EntryDocumentsCard({ ideaId, canEdit }: Props) {
  const inputId = useId();
  const [docs, setDocs] = useState<EntryDocument[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    documentsApi
      .list(ideaId)
      .then((rows) => setDocs(rows))
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load documents'))
      .finally(() => setLoaded(true));
  }, [ideaId]);

  useEffect(() => {
    load();
  }, [load]);

  const upload = async (list: FileList | null) => {
    if (!list || !list.length) return;
    const files = Array.from(list);
    const problem = validateDocuments(files, docs.length);
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      for (const f of files) {
        const saved = await documentsApi.upload(ideaId, f);
        setDocs((prev) => [...prev, saved]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (doc: EntryDocument) => {
    setBusy(true);
    setError(null);
    try {
      await documentsApi.remove(ideaId, doc.id);
      setDocs((prev) => prev.filter((d) => d.id !== doc.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not remove the document');
    } finally {
      setBusy(false);
    }
  };

  if (loaded && !docs.length && !canEdit && !error) return null;

  return (
    <div className="card card--tight entry-docs">
      <h3 style={{ marginBottom: 8 }}>
        Documents <span className="muted">({docs.length})</span>
      </h3>
      {error ? (
        <p className="small" role="alert" style={{ color: 'var(--danger)' }}>
          {error}
        </p>
      ) : null}
      {docs.length ? (
        <ul className="entry-docs__list">
          {docs.map((d) => (
            <li key={d.id} className="entry-docs__row">
              <a
                className="entry-docs__name"
                href={documentsApi.downloadUrl(ideaId, d.id)}
                download={d.filename}
              >
                {d.filename}
              </a>
              <span className="muted small">
                {formatBytes(d.size_bytes)}
                {d.text_chars === 0 ? ' · AI could not read it' : ''}
              </span>
              {canEdit ? (
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  aria-label={`Remove ${d.filename}`}
                  disabled={busy}
                  onClick={() => void remove(d)}
                >
                  <Icon name="trash" size={14} />
                </button>
              ) : null}
            </li>
          ))}
        </ul>
      ) : loaded ? (
        <p className="muted small">No documents attached.</p>
      ) : null}
      {canEdit && docs.length < DOC_MAX_FILES ? (
        <div className="field" style={{ marginTop: 8 }}>
          <label htmlFor={inputId} className="small">
            Add documentation
          </label>
          <input
            id={inputId}
            className="input"
            type="file"
            accept={DOC_ACCEPT}
            multiple
            disabled={busy}
            onChange={(e) => {
              void upload(e.target.files);
              e.target.value = '';
            }}
          />
          <div className="hint">PDF, Markdown, TXT or DOCX, 10 MB each.</div>
        </div>
      ) : null}
    </div>
  );
}

export default EntryDocumentsCard;
