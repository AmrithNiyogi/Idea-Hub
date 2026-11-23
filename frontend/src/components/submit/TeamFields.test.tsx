import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TeamFields } from './TeamFields';
import { usersApi } from '../../api/users';
import { mockUser } from '../../test/fixtures';

vi.mock('../../api/users', () => ({
  usersApi: {
    search: vi.fn(),
    get: vi.fn(),
  },
}));

const mate = { ...mockUser, id: 'mate-1', name: 'Priya Shah', title: 'Engineer' };

function renderFields(overrides: Partial<Parameters<typeof TeamFields>[0]> = {}) {
  const props = {
    currentUserId: mockUser.id,
    coAuthorIds: [] as string[],
    teamName: '',
    githubUrl: '',
    demoUrl: '',
    onDemoUrlChange: vi.fn(),
    onCoAuthorsChange: vi.fn(),
    onTeamNameChange: vi.fn(),
    onGithubUrlChange: vi.fn(),
    ...overrides,
  };
  render(<TeamFields {...props} />);
  return props;
}

describe('TeamFields', () => {
  beforeEach(() => {
    vi.mocked(usersApi.search).mockReset();
    vi.mocked(usersApi.get).mockReset();
  });

  it('searches people and adds a teammate as a co-author', async () => {
    vi.mocked(usersApi.search).mockResolvedValue([mate, { ...mockUser, name: 'Me' }]);
    const user = userEvent.setup();
    const props = renderFields();

    await user.type(screen.getByLabelText(/Search people by name or email/i), 'pri');

    const option = await screen.findByRole('button', { name: /Priya Shah/ });
    await user.click(option);
    expect(props.onCoAuthorsChange).toHaveBeenCalledWith(['mate-1']);
    // The current user never appears as a choice.
    expect(screen.queryByRole('button', { name: /^Me$/ })).not.toBeInTheDocument();
  });

  it('removes a selected teammate', async () => {
    vi.mocked(usersApi.get).mockResolvedValue(mate);
    const user = userEvent.setup();
    const props = renderFields({ coAuthorIds: ['mate-1'] });

    await user.click(await screen.findByRole('button', { name: 'Remove Priya Shah' }));
    expect(props.onCoAuthorsChange).toHaveBeenCalledWith([]);
  });

  it('loads names for saved teammates that only have ids', async () => {
    vi.mocked(usersApi.get).mockResolvedValue(mate);
    renderFields({ coAuthorIds: ['mate-1'] });
    expect(await screen.findByText('Priya Shah')).toBeInTheDocument();
    expect(usersApi.get).toHaveBeenCalledWith('mate-1');
  });

  it('passes team name edits up', async () => {
    const user = userEvent.setup();
    const props = renderFields();
    await user.type(screen.getByLabelText(/Team name/i), 'N');
    expect(props.onTeamNameChange).toHaveBeenCalledWith('N');
  });

  it('flags a GitHub link that is not a single repository', async () => {
    renderFields({ githubUrl: 'https://github.com/acme' });
    expect(screen.getByRole('alert')).toHaveTextContent(/one repository/i);
    expect(screen.getByLabelText(/GitHub repository/i)).toHaveAttribute('aria-invalid', 'true');
  });

  it('accepts a valid repository link without a warning', async () => {
    renderFields({ githubUrl: 'https://github.com/acme/ideas-hub' });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/One repository per idea/i)).toBeInTheDocument());
  });
});
