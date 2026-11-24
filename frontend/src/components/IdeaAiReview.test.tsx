import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { IdeaAiReview } from './IdeaAiReview';
import type { IdeaAiReview as AiReview } from '../types/idea';

const review: AiReview = {
  engine: 'local-heuristic',
  simulated: true,
  generated_at: '2026-11-24T10:00:00Z',
  summary: 'Clear problem; metrics need units.',
  dotkonnekt_fit: {
    band: 'partial',
    themes: [{ id: 'agents', label: 'Agent adoption', matched_terms: ['agent', 'kompass'] }],
    angles: ['Could run as a Kompass workflow.'],
  },
  suggestions: [
    { field: 'success_metrics', kind: 'metric', text: 'Add a weekly baseline.', rationale: 'Needed to measure.' },
  ],
  suggested_metrics: [{ metric: 'Hours saved', unit: 'hours/week', baseline_prompt: 'How many today?' }],
  suggested_beneficiaries: ['Support team', 'New joiners'],
  missing_fields: ['beneficiaries'],
};

describe('IdeaAiReview', () => {
  it('renders nothing for drafts', () => {
    const { container } = render(<IdeaAiReview review={null} isDraft />);
    expect(container).toBeEmptyDOMElement();
  });

  it('says there is no AI review yet when it is not ready', () => {
    render(<IdeaAiReview review={null} isDraft={false} />);
    expect(screen.getByText(/no ai review yet/i)).toBeInTheDocument();
    expect(screen.getByText('Pending')).toBeInTheDocument();
  });

  it('renders fit, themes, angles, suggestions, metrics and gaps', () => {
    render(<IdeaAiReview review={review} isDraft={false} audience="reviewer" />);
    expect(screen.getByText('Partial DotKonnekt fit')).toBeInTheDocument();
    expect(screen.getByText('Agent adoption')).toBeInTheDocument();
    expect(screen.getByText('Could run as a Kompass workflow.')).toBeInTheDocument();
    expect(screen.getByText('Add a weekly baseline.')).toBeInTheDocument();
    expect(screen.getByText('Success metrics')).toBeInTheDocument();
    expect(screen.getByText('Hours saved')).toBeInTheDocument();
    expect(screen.getByText(/Support team · New joiners/)).toBeInTheDocument();
    expect(screen.getByText(/Still thin/)).toBeInTheDocument();
    expect(screen.getByText('Simulated')).toBeInTheDocument();
    expect(screen.getByText(/reviewer makes the decision/)).toBeInTheDocument();
  });

  it('labels a live review and tolerates an unknown band', () => {
    render(
      <IdeaAiReview
        review={{
          ...review,
          simulated: false,
          dotkonnekt_fit: { ...review.dotkonnekt_fit, band: 'odd' as never },
          suggestions: [],
          suggested_metrics: [],
          suggested_beneficiaries: [],
          missing_fields: [],
        }}
        isDraft={false}
      />,
    );
    expect(screen.getByText('Live')).toBeInTheDocument();
    expect(screen.getByText('Exploratory')).toBeInTheDocument();
    expect(screen.getByText(/nothing changes your idea/)).toBeInTheDocument();
  });
});
