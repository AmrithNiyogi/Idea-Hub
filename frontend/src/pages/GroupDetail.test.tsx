import { act, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { GroupDetailPage } from './GroupDetail';
import { groupsApi } from '../api/groups';
import { DialogProvider } from '../components/DialogProvider';

vi.mock('../api/groups', () => ({
  groupsApi: {
    get: vi.fn(),
    messages: vi.fn(),
    meetings: vi.fn(),
    listMcp: vi.fn(),
    polls: vi.fn(),
  },
}));

vi.mock('../auth/AuthProvider', () => ({
  useAuth: () => ({ user: { id: 'me-1', name: 'Me', avatar: 1 } }),
}));

const dmGroup = {
  id: 'g1',
  kind: 'dm',
  name: 'Vaibhav Gupta',
  description: null,
  avatar_url: null,
  peer_user_id: 'them-1',
  peer_avatar: 2,
  peer_avatar_url: null,
  idea_id: null,
  can_post: true,
  can_manage: false,
  members: [
    { user_id: 'me-1', role: 'member', name: 'Me', avatar: 1 },
    { user_id: 'them-1', role: 'member', name: 'Vaibhav Gupta', avatar: 2 },
  ],
  channels: [{ id: 'c1', slug: 'dm', name: 'dm', description: null, sort_order: 0 }],
};

const msgOld = {
  id: 'm1',
  channel_id: 'c1',
  author_id: 'me-1',
  body: 'Hello',
  message_type: 'text',
  created_at: new Date().toISOString(),
};
const msgNew = {
  id: 'm2',
  channel_id: 'c1',
  author_id: 'them-1',
  body: 'hey there',
  message_type: 'text',
  created_at: new Date().toISOString(),
};

describe('GroupDetail DM polling', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(groupsApi.get).mockResolvedValue(dmGroup as never);
    vi.mocked(groupsApi.meetings).mockResolvedValue([] as never);
    vi.mocked(groupsApi.listMcp).mockResolvedValue([] as never);
    vi.mocked(groupsApi.polls).mockResolvedValue([] as never);
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it('shows a new incoming message without a page refresh', async () => {
    vi.mocked(groupsApi.messages)
      .mockResolvedValueOnce([msgOld] as never)
      .mockResolvedValue([msgOld, msgNew] as never);

    render(
      <DialogProvider>
        <MemoryRouter initialEntries={['/dms/g1']}>
          <Routes>
            <Route path="/dms/:id" element={<GroupDetailPage dmRoute />} />
          </Routes>
        </MemoryRouter>
      </DialogProvider>,
    );

    expect(await screen.findByText('Hello')).toBeInTheDocument();
    expect(screen.queryByText('hey there')).not.toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(8100);
    });

    await waitFor(() => expect(screen.getByText('hey there')).toBeInTheDocument());
  });
});
