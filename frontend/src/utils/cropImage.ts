/**
 * Canvas helpers for avatar cropping (react-easy-crop pixel areas → Blob/File).
 */

import type { Area } from 'react-easy-crop';

/**
 * Load an image from a blob/object URL and resolve when decoded.
 *
 * Args:
 *   src: Object URL or data URL for the source image.
 *
 * Returns:
 *   HTMLImageElement ready for canvas drawImage.
 *
 * Raises:
 *   Rejects when the image fails to load.
 */
function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.addEventListener('load', () => resolve(img));
    img.addEventListener('error', () =>
      reject(new Error('Could not load image for cropping')),
    );
    img.src = src;
  });
}

/**
 * Rasterize a square (or rectangular) crop region to a Blob.
 *
 * Uses the pixel crop from react-easy-crop (already in natural image coords).
 * Prefer JPEG for photo avatars; pass image/png for graphics with transparency.
 *
 * Args:
 *   imageSrc: Object/data URL of the full image being cropped.
 *   pixelCrop: Natural-pixel crop rectangle from Cropper onCropComplete.
 *   mimeType: Output MIME type (image/jpeg or image/png).
 *   quality: JPEG quality 0–1 (ignored for PNG).
 *   outputSize: Square edge length in CSS pixels for the exported file.
 *
 * Returns:
 *   Blob of the cropped image, or rejects if canvas export fails.
 */
export async function cropImageToBlob(
  imageSrc: string,
  pixelCrop: Area,
  mimeType: 'image/jpeg' | 'image/png' = 'image/jpeg',
  quality = 0.92,
  outputSize = 512,
): Promise<Blob> {
  const image = await loadImage(imageSrc);
  const canvas = document.createElement('canvas');
  canvas.width = outputSize;
  canvas.height = outputSize;
  const ctx = canvas.getContext('2d');
  if (!ctx) {
    throw new Error('Canvas is not available in this browser');
  }

  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(
    image,
    pixelCrop.x,
    pixelCrop.y,
    pixelCrop.width,
    pixelCrop.height,
    0,
    0,
    outputSize,
    outputSize,
  );

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Failed to export cropped image'));
          return;
        }
        resolve(blob);
      },
      mimeType,
      quality,
    );
  });
}

/**
 * Wrap a cropped Blob as a named File for multipart upload.
 *
 * Args:
 *   blob: Cropped image bytes.
 *   mimeType: MIME used for the File type and extension.
 *   basename: Filename stem without extension (default avatar).
 *
 * Returns:
 *   File suitable for FormData append to POST /users/me/avatar.
 */
export function blobToAvatarFile(
  blob: Blob,
  mimeType: 'image/jpeg' | 'image/png',
  basename = 'avatar',
): File {
  const ext = mimeType === 'image/png' ? 'png' : 'jpg';
  return new File([blob], `${basename}.${ext}`, { type: mimeType });
}
