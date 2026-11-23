/**
 * Renders an assistant reply with a small, safe subset of Markdown:
 * paragraphs, numbered and bulleted lists, **bold** and `code`.
 *
 * Builds React elements only (no HTML injection), so reply text cannot add markup.
 */

import type { ReactNode } from 'react';

const INLINE = /(\*\*[^*\n]+\*\*|`[^`\n]+`)/g;

function renderInline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2) {
      return <code key={i}>{part.slice(1, -1)}</code>;
    }
    return <span key={i}>{part}</span>;
  });
}

type Block =
  | { kind: 'p'; lines: string[] }
  | { kind: 'ol'; items: string[] }
  | { kind: 'ul'; items: string[] };

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  const paragraphs = text.replace(/\r\n/g, '\n').split(/\n\s*\n/);
  for (const para of paragraphs) {
    const lines = para
      .split('\n')
      .map((l) => l.trimEnd())
      .filter((l) => l.trim().length > 0);
    if (!lines.length) continue;

    const ordered = lines.every((l) => /^\s*\d+[.)]\s+/.test(l));
    const unordered = lines.every((l) => /^\s*[-*]\s+/.test(l));
    if (ordered) {
      blocks.push({ kind: 'ol', items: lines.map((l) => l.replace(/^\s*\d+[.)]\s+/, '')) });
    } else if (unordered) {
      blocks.push({ kind: 'ul', items: lines.map((l) => l.replace(/^\s*[-*]\s+/, '')) });
    } else {
      blocks.push({ kind: 'p', lines });
    }
  }
  return blocks;
}

export function ChatReply({ text }: { text: string }) {
  const blocks = parseBlocks(text);
  return (
    <div className="ik-chat__reply">
      {blocks.map((b, i) => {
        if (b.kind === 'ol') {
          return (
            <ol key={i}>
              {b.items.map((item, j) => (
                <li key={j}>{renderInline(item)}</li>
              ))}
            </ol>
          );
        }
        if (b.kind === 'ul') {
          return (
            <ul key={i}>
              {b.items.map((item, j) => (
                <li key={j}>{renderInline(item)}</li>
              ))}
            </ul>
          );
        }
        return <p key={i}>{b.lines.map((l, j) => (
          <span key={j}>
            {j > 0 ? <br /> : null}
            {renderInline(l)}
          </span>
        ))}</p>;
      })}
    </div>
  );
}

export default ChatReply;
