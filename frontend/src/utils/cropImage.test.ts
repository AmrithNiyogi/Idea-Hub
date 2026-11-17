import { afterEach, describe, expect, it, vi } from 'vitest';
import { blobToAvatarFile, cropImageToBlob } from './cropImage';

describe('blobToAvatarFile', () => {
  it('picks jpg vs png extension', () => {
    const blob = new Blob(['x'], { type: 'image/jpeg' });
    const jpg = blobToAvatarFile(blob, 'image/jpeg');
    expect(jpg.name).toBe('avatar.jpg');
    expect(jpg.type).toBe('image/jpeg');

    const png = blobToAvatarFile(blob, 'image/png', 'face');
    expect(png.name).toBe('face.png');
  });
});

describe('cropImageToBlob', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('draws the crop region onto a canvas and exports a blob', async () => {
    class FakeImage {
      width = 100;
      height = 100;
      addEventListener(event: string, cb: () => void) {
        if (event === 'load') queueMicrotask(cb);
      }
      set src(_v: string) {
        /* trigger via addEventListener */
      }
    }
    vi.stubGlobal('Image', FakeImage);

    const ctx = {
      imageSmoothingEnabled: false,
      imageSmoothingQuality: '',
      drawImage: vi.fn(),
    };
    const toBlob = vi.fn(
      (cb: (b: Blob | null) => void, _mime?: string, _q?: number) => {
        cb(new Blob(['img'], { type: 'image/jpeg' }));
      },
    );
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => ctx,
          toBlob,
        } as unknown as HTMLCanvasElement;
      }
      return document.createElement(tag);
    });

    const blob = await cropImageToBlob(
      'blob:mock',
      { x: 1, y: 2, width: 10, height: 10 },
      'image/jpeg',
      0.9,
      256,
    );
    expect(blob).toBeInstanceOf(Blob);
    expect(ctx.drawImage).toHaveBeenCalled();
    expect(toBlob).toHaveBeenCalled();
  });

  it('rejects when image load fails', async () => {
    class BadImage {
      addEventListener(event: string, cb: () => void) {
        if (event === 'error') queueMicrotask(cb);
      }
      set src(_v: string) {
        /* noop */
      }
    }
    vi.stubGlobal('Image', BadImage);
    await expect(
      cropImageToBlob('bad', { x: 0, y: 0, width: 1, height: 1 }),
    ).rejects.toThrow(/Could not load image/);
  });

  it('rejects when canvas context is unavailable', async () => {
    class FakeImage {
      addEventListener(event: string, cb: () => void) {
        if (event === 'load') queueMicrotask(cb);
      }
      set src(_v: string) {
        /* noop */
      }
    }
    vi.stubGlobal('Image', FakeImage);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => null,
        } as unknown as HTMLCanvasElement;
      }
      return document.createElement(tag);
    });
    await expect(
      cropImageToBlob('x', { x: 0, y: 0, width: 1, height: 1 }),
    ).rejects.toThrow(/Canvas is not available/);
  });

  it('rejects when toBlob returns null', async () => {
    class FakeImage {
      addEventListener(event: string, cb: () => void) {
        if (event === 'load') queueMicrotask(cb);
      }
      set src(_v: string) {
        /* noop */
      }
    }
    vi.stubGlobal('Image', FakeImage);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'canvas') {
        return {
          width: 0,
          height: 0,
          getContext: () => ({
            imageSmoothingEnabled: false,
            imageSmoothingQuality: '',
            drawImage: vi.fn(),
          }),
          toBlob: (cb: (b: Blob | null) => void) => cb(null),
        } as unknown as HTMLCanvasElement;
      }
      return document.createElement(tag);
    });
    await expect(
      cropImageToBlob('x', { x: 0, y: 0, width: 1, height: 1 }),
    ).rejects.toThrow(/Failed to export/);
  });
});
