import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentHandoffBar } from './AgentHandoffBar';
import type { AgentContext } from '../types/idea';

vi.mock('../api/ideas', () => ({
  ideasApi: {
    agentContext: vi.fn(),
  },
}));

vi.mock('../api/agentHandoff', () => ({
  agentHandoffApi: {
    downloadSkillZip: vi.fn(),
    skill: vi.fn(),
  },
}));

import { agentHandoffApi } from '../api/agentHandoff';
import { ideasApi } from '../api/ideas';

const ctx: AgentContext = {
  idea_id: 'idea-1',
  slug: 'sample',
  title: 'Sample',
  status: 'submitted',
  api_base_url: 'http://127.0.0.1:8000',
  skill: {
    name: 'idea-hub-pull-idea',
    skill_markdown: '# skill\n',
    install_cursor: 'cursor install',
    install_claude: 'claude install',
    zip_url: '/api/v1/agent-handoff/skill-pack.zip',
  },
  markdown: '# Sample\n',
  prompts: {
    cursor: 'cursor prompt',
    claude: 'claude prompt',
  },
};

describe('AgentHandoffBar', () => {
  beforeEach(() => {
    vi.mocked(ideasApi.agentContext).mockReset();
    vi.mocked(ideasApi.agentContext).mockResolvedValue(ctx);
    vi.mocked(agentHandoffApi.downloadSkillZip).mockReset();
    vi.mocked(agentHandoffApi.downloadSkillZip).mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it('copies Cursor / Claude prompts and downloads markdown + skill', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    const createObjectURL = vi
      .spyOn(URL, 'createObjectURL')
      .mockReturnValue('blob:mock');
    const revokeObjectURL = vi
      .spyOn(URL, 'revokeObjectURL')
      .mockImplementation(() => undefined);

    render(
      <AgentHandoffBar ideaId="idea-1" ideaTitle="Sample idea" compact />,
    );
    expect(screen.getByText(/Build with an agent/i)).toBeInTheDocument();
    expect(screen.getByText('Sample idea')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Copy for Cursor/i }));
    await screen.findByText(/Copied Cursor prompt/i);

    await user.click(screen.getByRole('button', { name: /Copy for Claude/i }));
    await screen.findByText(/Copied Claude prompt/i);

    await user.click(screen.getByRole('button', { name: /Download context/i }));
    await screen.findByText(/Downloaded context/i);
    expect(createObjectURL).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();

    await user.click(screen.getByRole('button', { name: /Download skill/i }));
    await screen.findByText(/Downloaded skill zip/i);
    expect(agentHandoffApi.downloadSkillZip).toHaveBeenCalledTimes(1);

    // Cached load — second copy should not refetch
    await user.click(screen.getByRole('button', { name: /Copy for Cursor/i }));
    await waitFor(() =>
      expect(ideasApi.agentContext).toHaveBeenCalledTimes(1),
    );

    await user.click(screen.getByRole('button', { name: /How to launch/i }));
    expect(
      screen.getByText(/Start building in Cursor or Claude Code/i),
    ).toBeInTheDocument();

    createObjectURL.mockRestore();
    revokeObjectURL.mockRestore();
  });

  it('shows error when agent context fails', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    vi.mocked(ideasApi.agentContext).mockRejectedValue(new Error('denied'));
    render(<AgentHandoffBar ideaId="idea-1" />);
    await user.click(screen.getByRole('button', { name: /Copy for Cursor/i }));
    await screen.findByText(/denied/);
  });

  it('falls back to textarea copy when clipboard API missing', async () => {
    const user = userEvent.setup({ writeToClipboard: false });
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    });
    document.execCommand = vi.fn().mockReturnValue(true) as typeof document.execCommand;
    render(<AgentHandoffBar ideaId="idea-1" />);
    await user.click(screen.getByRole('button', { name: /Copy for Cursor/i }));
    await screen.findByText(/Copied Cursor prompt/i);
    expect(document.execCommand).toHaveBeenCalledWith('copy');
  });
});
