import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { StatusPill } from './StatusPill';
import { Icon } from './Icons';
import { nextStep, relTime } from '../utils/format';
import type { Idea, Category } from '../types/idea';

function catStyle(color?: string | null): CSSProperties | undefined {
  if (!color) return undefined;
  return { ['--cat-color' as string]: color } as CSSProperties;
}

export function IdeaCard({
  idea,
  category,
}: {
  idea: Idea;
  category?: Category | null;
}) {
  const ns = nextStep(idea);
  return (
    <article className="card idea-card">
      <div className="row" style={{ gap: 6 }}>
        {category ? (
          <span className="tag tag--cat" style={catStyle(category.color)}>
            <i className="dot" aria-hidden="true" />
            {category.label}
          </span>
        ) : null}
        <StatusPill status={idea.status} />
        {idea.anonymous ? (
          <span className="pill">
            <Icon name="lock" size={12} /> Anonymous
          </span>
        ) : null}
      </div>
      <h3 className="idea-card__title">
        <Link to={`/ideas/${idea.id}`}>{idea.title}</Link>
      </h3>
      <p className="muted small clamp">
        {idea.problem || 'No problem statement yet.'}
      </p>
      <p className="muted small">{ns.text}</p>
      <div className="chip-row">
        {idea.tags.slice(0, 4).map((t) => (
          <Link
            key={t}
            className="tag"
            to={`/explore?tag=${encodeURIComponent(t)}`}
          >
            {t}
          </Link>
        ))}
      </div>
      <div className="idea-card__foot muted small">
        <span>
          <Icon name="up" size={14} /> {idea.vote_count}
        </span>
        <span>·</span>
        <span>
          <Icon name="eye" size={14} /> {idea.follow_count}
        </span>
        <span>·</span>
        <span>
          <Icon name="message" size={14} /> {idea.comment_count}
        </span>
        <span style={{ marginLeft: 'auto' }}>
          {relTime(idea.updated_at || idea.submitted_at)}
        </span>
      </div>
    </article>
  );
}
