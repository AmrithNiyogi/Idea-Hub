/**
 * Modal cropper for profile avatars — square crop → Confirm exports JPEG/PNG File.
 *
 * Uses IdeaKonnekt `.modal*` classes and react-easy-crop for pan/zoom.
 */

import { useCallback, useEffect, useId, useState } from 'react';
import Cropper, { type Area, type Point } from 'react-easy-crop';
import { blobToAvatarFile, cropImageToBlob } from '../utils/cropImage';

export interface AvatarCropDialogProps {
  /** Object URL of the image the user just picked. */
  imageSrc: string;
  /** Prefer JPEG for photos; PNG when the source is PNG. */
  outputType?: 'image/jpeg' | 'image/png';
  /** True while parent is uploading the cropped file. */
  confirming?: boolean;
  onCancel: () => void;
  /** Called with a named File ready for POST /users/me/avatar. */
  onConfirm: (file: File) => void | Promise<void>;
}

/**
 * Dialog: drag/zoom a square crop, then Confirm or Cancel.
 *
 * Escape and backdrop click cancel (discard). Focus stays in the dialog.
 */
export function AvatarCropDialog({
  imageSrc,
  outputType = 'image/jpeg',
  confirming = false,
  onCancel,
  onConfirm,
}: AvatarCropDialogProps) {
  const titleId = useId();
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [exportErr, setExportErr] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  const onCropComplete = useCallback((_area: Area, pixels: Area) => {
    setCroppedAreaPixels(pixels);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !confirming && !exporting) {
        e.preventDefault();
        onCancel();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [confirming, exporting, onCancel]);

  async function handleConfirm() {
    if (!croppedAreaPixels || confirming || exporting) return;
    setExportErr(null);
    setExporting(true);
    try {
      const blob = await cropImageToBlob(
        imageSrc,
        croppedAreaPixels,
        outputType,
      );
      const file = blobToAvatarFile(blob, outputType);
      await onConfirm(file);
    } catch (err) {
      setExportErr(err instanceof Error ? err.message : 'Crop failed');
    } finally {
      setExporting(false);
    }
  }

  const busy = confirming || exporting;

  return (
    <div
      className="modal-backdrop"
      id="avatar-crop-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel();
      }}
    >
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="modal__head">
          <h2 id={titleId}>Crop avatar</h2>
        </div>
        <div className="modal__body">
          <p className="muted small" style={{ margin: 0 }}>
            Drag to reposition. Use the slider to zoom. The square area becomes
            your profile image.
          </p>
          <div className="avatar-crop">
            <Cropper
              image={imageSrc}
              crop={crop}
              zoom={zoom}
              aspect={1}
              cropShape="round"
              showGrid={false}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={onCropComplete}
            />
          </div>
          <div className="field">
            <label htmlFor="avatar-crop-zoom">Zoom</label>
            <input
              id="avatar-crop-zoom"
              className="input"
              type="range"
              min={1}
              max={3}
              step={0.05}
              value={zoom}
              disabled={busy}
              onChange={(e) => setZoom(Number(e.target.value))}
              aria-valuemin={1}
              aria-valuemax={3}
              aria-valuenow={zoom}
            />
          </div>
          {exportErr ? (
            <p className="error" role="alert">
              {exportErr}
            </p>
          ) : null}
        </div>
        <div className="modal__foot">
          <button
            type="button"
            className="btn"
            onClick={onCancel}
            disabled={busy}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn btn--primary"
            onClick={() => void handleConfirm()}
            disabled={busy || !croppedAreaPixels}
          >
            {busy ? 'Uploading…' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}
