import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { IdeaCard } from './IdeaCard';
import { makeIdea, mockCategory } from '../test/fixtures';

describe('IdeaCard', () => {
  it('renders title, category, status, tags, and counts', () => {
    render(
      <MemoryRouter>
        <IdeaCard idea={makeIdea()} category={mockCategory} />
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Sample idea' })).toHaveAttribute(
      'href',
      '/ideas/idea-1',
    );
    expect(screen.getByText('Platform')).toBeInTheDocument();
    expect(screen.getByText('Submitted')).toBeInTheDocument();
    expect(screen.getByText('ci-cd')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText(/Waiting for a reviewer/i)).toBeInTheDocument();
  });

  it('shows anonymous pill and problem fallback', () => {
    render(
      <MemoryRouter>
        <IdeaCard
          idea={makeIdea({ anonymous: true, problem: '', tags: [] })}
          category={{ ...mockCategory, color: '' }}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Anonymous/i)).toBeInTheDocument();
    expect(screen.getByText(/No problem statement yet/i)).toBeInTheDocument();
    expect(screen.getByText('Platform')).toBeInTheDocument();
  });
});

