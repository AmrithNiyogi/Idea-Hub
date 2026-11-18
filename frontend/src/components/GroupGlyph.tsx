/** Group avatar (uploaded image) with initial-letter fallback. */

import { resolveAvatarSrc } from './Icons';

export function GroupGlyph({
  name,
  avatarUrl,
  size = 40,
}: {
  name: string;
  avatarUrl?: string | null;
  size?: number;
}) {
  const src = resolveAvatarSrc(avatarUrl);
  const style = { width: size, height: size };
  if (src) {
    return (
      <span
        className="grp-row__glyph grp-row__glyph--img"
        style={style}
        aria-hidden
      >
        <img src={src} alt="" />
      </span>
    );
  }
  const t = (name || '?').trim();
  return (
    <span className="grp-row__glyph" style={style} aria-hidden>
      {(t[0] || '?').toUpperCase()}
    </span>
  );
}
