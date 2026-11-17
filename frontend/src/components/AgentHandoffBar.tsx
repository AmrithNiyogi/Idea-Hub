/**
 * Copy / download Idea Hub → Cursor / Claude Code handoff packs.
 *
 * Fetches GET /ideas/{id}/agent-context (auth required) and exposes
 * tool-tailored prompts, downloadable context.md, and the installable
 * idea-hub-pull-idea skill zip. Secrets are never included in the payload.
 */

import { useState } from 'react';
import { agentHandoffApi } from '../api/agentHandoff';
import { ideasApi } from '../api/ideas';
import type { AgentContext } from '../types/idea';
import { Icon } from './Icons';

type Tool = 'cursor' | 'claude';

type Props = {
  ideaId: string;
  ideaTitle?: string;
  compact?: boolean;
};

async function copyText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const ta = document.createElement('textarea');
  ta.value = text;
  ta.setAttribute('readonly', '');
  ta.style.position = 'fixed';
  ta.style.left = '-9999px';
  document.body.appendChild(ta);
  ta.select();
  document.execCommand('copy');
  document.body.removeChild(ta);
}

function downloadMarkdown(ctx: AgentContext) {
  const slug = ctx.slug || ctx.idea_id.slice(0, 8);
  const blob = new Blob([ctx.markdown], {
    type: 'text/markdown;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${slug}-context.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function downloadSkillMarkdown(ctx: AgentContext) {
  const blob = new Blob([ctx.skill.skill_markdown], {
    type: 'text/markdown;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${ctx.skill.name}-SKILL.md`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function AgentHandoffBar({ ideaId, ideaTitle, compact }: Props) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [showGuide, setShowGuide] = useState(false);
  const [cached, setCached] = useState<AgentContext | null>(null);

  const load = async (): Promise<AgentContext> => {
    if (cached && cached.idea_id === ideaId) return cached;
    const ctx = await ideasApi.agentContext(ideaId);
    setCached(ctx);
    return ctx;
  };

  const run = async (
    action: 'cursor' | 'claude' | 'download' | 'skill-zip' | 'skill-md' | 'copy-skill',
  ) => {
    setBusy(true);
    setErr(null);
    setMsg(null);
    try {
      if (action === 'skill-zip') {
        await agentHandoffApi.downloadSkillZip();
        setMsg('Downloaded skill zip — extract at your repo root');
        return;
      }
      const ctx = await load();
      if (action === 'download') {
        downloadMarkdown(ctx);
        setMsg('Downloaded context.md');
      } else if (action === 'skill-md') {
        downloadSkillMarkdown(ctx);
        setMsg(`Downloaded ${ctx.skill.name}-SKILL.md`);
      } else if (action === 'copy-skill') {
        await copyText(ctx.skill.skill_markdown);
        setMsg('Copied SKILL.md — save under .cursor/skills or .claude/skills');
      } else {
        const tool: Tool = action;
        await copyText(ctx.prompts[tool]);
        setMsg(
          tool === 'cursor'
            ? 'Copied Cursor prompt — paste into Agent chat to start'
            : 'Copied Claude prompt — paste into the session to start',
        );
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not build agent context');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`agent-handoff${compact ? ' agent-handoff--compact' : ''}`}>
      <div className="agent-handoff__label">
        <Icon name="spark" size={14} />
        <span>Build with an agent</span>
        {ideaTitle ? (
          <span className="muted agent-handoff__title-hint" title={ideaTitle}>
            {ideaTitle}
          </span>
        ) : null}
      </div>
      <div className="row agent-handoff__actions">
        <button
          type="button"
          className="btn btn--sm"
          disabled={busy}
          onClick={() => run('cursor')}
          title="Copy a ready-to-paste Cursor prompt with this idea’s full context"
        >
          <Icon name="copy" size={14} /> Copy for Cursor
        </button>
        <button
          type="button"
          className="btn btn--sm"
          disabled={busy}
          onClick={() => run('claude')}
          title="Copy a ready-to-paste Claude Code prompt with this idea’s full context"
        >
          <Icon name="copy" size={14} /> Copy for Claude
        </button>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          disabled={busy}
          onClick={() => run('download')}
          title="Download context.md"
        >
          <Icon name="download" size={14} /> Download context.md
        </button>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          disabled={busy}
          onClick={() => run('skill-zip')}
          title="Download idea-hub-pull-idea skill zip (Cursor + Claude paths)"
        >
          <Icon name="download" size={14} /> Download skill
        </button>
        <button
          type="button"
          className="btn btn--sm btn--ghost"
          aria-expanded={showGuide}
          onClick={() => setShowGuide((v) => !v)}
        >
          <Icon name="help" size={14} /> How to launch
        </button>
      </div>
      {msg ? (
        <p className="agent-handoff__toast" role="status">
          <Icon name="check" size={14} /> {msg}
        </p>
      ) : null}
      {err ? (
        <p className="agent-handoff__error" role="alert">
          <Icon name="alert" size={14} /> {err}
        </p>
      ) : null}
      {showGuide ? (
        <div className="notice agent-handoff__guide">
          <Icon name="info" size={16} />
          <div className="stack" style={{ gap: 6 }}>
            <strong>Start building in Cursor or Claude Code</strong>
            <p className="muted" style={{ margin: 0 }}>
              There is no reliable universal deeplink that injects a prompt into
              every install. Use a one-click copy, then paste into the agent —
              the prompt already includes the idea UUID, API URL, and full
              context.
            </p>
            <ol className="agent-handoff__steps">
              <li>
                <strong>Fastest:</strong> <em>Copy for Cursor</em> or{' '}
                <em>Copy for Claude</em> → open the target repo → Agent / Chat
                (or Claude Code) → paste. The agent can start immediately; skill
                install is optional.
              </li>
              <li>
                <strong>Install skill (optional re-fetch):</strong>{' '}
                <em>Download skill</em> → extract the zip at the repo root so
                both{' '}
                <code>.cursor/skills/idea-hub-pull-idea/SKILL.md</code> and{' '}
                <code>.claude/skills/idea-hub-pull-idea/SKILL.md</code> exist.
                Then ask the agent to use skill{' '}
                <code>idea-hub-pull-idea</code> with this idea UUID.
              </li>
              <li>
                Or <em>Download context.md</em> and attach / @-mention it in the
                session.
              </li>
              <li>
                API:{' '}
                <code>GET /api/v1/ideas/{'{id}'}/agent-context</code> · skill zip:{' '}
                <code>GET /api/v1/agent-handoff/skill-pack.zip</code> (auth
                cookie or Bearer). Base:{' '}
                <code>PUBLIC_API_URL</code> / <code>IDEA_HUB_API_URL</code>.
              </li>
            </ol>
            <div className="row agent-handoff__actions" style={{ marginTop: 4 }}>
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                disabled={busy}
                onClick={() => run('copy-skill')}
              >
                <Icon name="copy" size={14} /> Copy SKILL.md
              </button>
              <button
                type="button"
                className="btn btn--sm btn--ghost"
                disabled={busy}
                onClick={() => run('skill-md')}
              >
                <Icon name="download" size={14} /> Download SKILL.md only
              </button>
            </div>
            <p className="muted" style={{ margin: 0 }}>
              Idea ID: <code>{ideaId}</code>
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
