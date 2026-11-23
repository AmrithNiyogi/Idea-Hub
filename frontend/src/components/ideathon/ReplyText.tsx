/**
 * Renders the short prose an agent writes around its JSON.
 * Supports paragraphs, "- " bullets, "#" headings and **bold**. Anything else is plain text,
 * and React escapes it, so agent output never becomes markup.
 */
import type { ReactNode } from 'react';

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4 ? (
      <strong key={i}>{part.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function ReplyText({ text }: { text: string }) {
  const blocks = text
    .split(/\n\s*\n/)
    .map((b) => b.trim())
    .filter(Boolean);
  return (
    <div className="reply-text">
      {blocks.map((block, i) => {
        const lines = block.split('\n').map((l) => l.trim());
        if (/^-{3,}$/.test(block)) {
          return <hr key={i} />;
        }
        if (lines.every((l) => l.startsWith('- ') || l.startsWith('* '))) {
          return (
            <ul key={i}>
              {lines.map((l, j) => (
                <li key={j}>{inline(l.slice(2))}</li>
              ))}
            </ul>
          );
        }
        const heading = /^#{1,3}\s+(.*)$/.exec(block);
        if (heading && lines.length === 1) {
          return <h4 key={i}>{inline(heading[1])}</h4>;
        }
        return <p key={i}>{inline(lines.join(' '))}</p>;
      })}
    </div>
  );
}
