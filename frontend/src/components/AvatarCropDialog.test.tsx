import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AvatarCropDialog } from './AvatarCropDialog';

vi.mock('react-easy-crop', () => ({
  default: ({
    onCropComplete,
  }: {
    onCropComplete: (a: unknown, b: unknown) => void;
  }) => (
    <button
      type="button"
      onClick={() =>
        onCropComplete(
          { x: 0, y: 0, width: 1, height: 1 },
          { x: 0, y: 0, width: 50, height: 50 },
        )
      }
    >
      mock-crop
    </button>
  ),
}));

vi.mock('../utils/cropImage', () => ({
  cropImageToBlob: vi.fn(),
  blobToAvatarFile: vi.fn(),
}));

import { blobToAvatarFile, cropImageToBlob } from '../utils/cropImage';

describe('AvatarCropDialog', () => {
  beforeEach(() => {
    vi.mocked(cropImageToBlob).mockReset();
    vi.mocked(blobToAvatarFile).mockReset();
    vi.mocked(cropImageToBlob).mockResolvedValue(
      new Blob(['x'], { type: 'image/jpeg' }),
    );
    vi.mocked(blobToAvatarFile).mockReturnValue(
      new File(['x'], 'avatar.jpg', { type: 'image/jpeg' }),
    );
  });

  it('cancels via Escape and backdrop', async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <AvatarCropDialog
        imageSrc="blob:x"
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />,
    );
    await user.keyboard('{Escape}');
    expect(onCancel).toHaveBeenCalled();

    onCancel.mockClear();
    fireEvent.click(screen.getByRole('presentation'));
    expect(onCancel).toHaveBeenCalled();
  });

  it('exports cropped file on confirm', async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <AvatarCropDialog
        imageSrc="blob:x"
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'mock-crop' }));
    await user.click(screen.getByRole('button', { name: /^Confirm$/i }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalled());
    expect(cropImageToBlob).toHaveBeenCalled();
  });

  it('shows export errors', async () => {
    const user = userEvent.setup();
    vi.mocked(cropImageToBlob).mockRejectedValue(new Error('crop boom'));
    render(
      <AvatarCropDialog
        imageSrc="blob:x"
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'mock-crop' }));
    await user.click(screen.getByRole('button', { name: /^Confirm$/i }));
    await screen.findByText(/crop boom/);
  });
});

