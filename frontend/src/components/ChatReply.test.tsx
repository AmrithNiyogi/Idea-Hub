import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ChatReply } from './ChatReply';

describe('ChatReply', () => {
  it('renders bold text and numbered steps instead of raw Markdown', () => {
    const { container } = render(
      <ChatReply text={'Use **Submit** to start:\n\n1. Fill in the title\n2. Press **Submit idea**'} />,
    );
    expect(screen.getByText('Submit', { selector: 'strong' })).toBeInTheDocument();
    const items = container.querySelectorAll('ol li');
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent('Fill in the title');
    expect(container.textContent).not.toContain('**');
  });

  it('shows markup from the reply as plain text, never as HTML', () => {
    const { container } = render(<ChatReply text={'<img src=x onerror=alert(1)> hello'} />);
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toContain('<img');
  });
});
