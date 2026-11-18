/** Minimal inline SVG icons matching the HTML prototype set (spine subset). */

type IconProps = { size?: number; className?: string };

const paths: Record<string, string> = {
  home: '<path d="M4 12l8-8 8 8"/><path d="M6 10v10h4v-6h4v6h4V10"/>',
  compass:
    '<circle cx="12" cy="12" r="9"/><polygon points="16.2,7.8 14,14 7.8,16.2 10,10"/>',
  list: '<path d="M8 6h12M8 12h12M8 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/>',
  checkcircle: '<circle cx="12" cy="12" r="9"/><path d="M8 12l2.5 2.5L16 9"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  search: '<circle cx="11" cy="11" r="6.5"/><path d="M16.5 16.5L21 21"/>',
  bell: '<path d="M6 16V10a6 6 0 1 1 12 0v6l1.5 2H4.5L6 16z"/><path d="M10 20a2 2 0 0 0 4 0"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 7 7 0 1 0 20 14.5z"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  sidebar: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M9 4.5v15"/>',
  chevronR: '<path d="M9 6l6 6-6 6"/>',
  chevronD: '<path d="M6 9l6 6 6-6"/>',
  user: '<circle cx="12" cy="8" r="3.5"/><path d="M5 20c1.5-3.5 4-5 7-5s5.5 1.5 7 5"/>',
  refresh:
    '<path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v5h-5"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  alert:
    '<path d="M12 3l10 18H2L12 3z"/><path d="M12 10v4"/><circle cx="12" cy="17" r=".8" fill="currentColor"/>',
  edit: '<path d="M4 20h4l11-11-4-4L4 16v4z"/><path d="M13 7l4 4"/>',
  inbox: '<path d="M4 8l2-4h12l2 4v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8z"/><path d="M4 8h16"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
  eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  eyeOff:
    '<path d="M3 3l18 18"/><path d="M10.6 10.6A3 3 0 0 0 13.4 13.4"/><path d="M9.9 5.2A10.5 10.5 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-3.2 4.1"/><path d="M6.1 6.1A17 17 0 0 0 2 12s3.5 7 10 7a10 10 0 0 0 4.1-.9"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 7 9-7"/>',
  check: '<path d="M5 12l5 5L20 7"/>',
  arrowRight: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  arrowLeft: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  /* IdeaKonnekt mark — 4-point spark geometry from idea-hub.html; filled for crisp sidebar glyph */
  logo: '<path d="M12 3.5 14.2 9.8 20.5 12 14.2 14.2 12 20.5 9.8 14.2 3.5 12 9.8 9.8z" fill="currentColor" stroke="none"/>',
  flag: '<path d="M5 21V4"/><path d="M5 4h11l-2 4 2 4H5"/>',
  award:
    '<circle cx="12" cy="9" r="6"/><path d="M8.5 14.5L7 22l5-3 5 3-1.5-7.5"/>',
  columns:
    '<path d="M4 5h4v14H4zM10 5h4v14h-4zM16 5h4v14h-4z"/>',
  spark:
    '<path d="M12 2l1.2 4.2L17 7.5l-3.8 1.3L12 13l-1.2-4.2L7 7.5l3.8-1.3L12 2z"/><path d="M5 14l.8 2.8L8.5 18l-2.7.9L5 22l-.8-3.1L1.5 18l2.7-.9L5 14z"/>',
  trophy:
    '<path d="M8 4h8v3a4 4 0 0 1-8 0V4z"/><path d="M8 5H5a2 2 0 0 0 2 4"/><path d="M16 5h3a2 2 0 0 1-2 4"/><path d="M10 13h4v3l-2 4-2-4v-3z"/>',
  calendar:
    '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/>',
  send: '<path d="M4 12l16-7-7 16-2-7-7-2z"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  target:
    '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r="1" fill="currentColor"/>',
  hand: '<path d="M8 11V7a1.5 1.5 0 0 1 3 0v4"/><path d="M11 11V5.5a1.5 1.5 0 0 1 3 0V11"/><path d="M14 11V7a1.5 1.5 0 0 1 3 0v6c0 3-2 5-5 5h-1c-3.5 0-6-2-6-5.5V12a1.5 1.5 0 0 1 3 0v-1"/>',
  users:
    '<circle cx="9" cy="8" r="3"/><path d="M3 19c1-3 3-4.5 6-4.5S14 16 15 19"/><circle cx="17" cy="9" r="2.5"/><path d="M21 19c-.7-2.2-2-3.3-4-3.5"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 10v6M12 7h.01"/>',
  shield: '<path d="M12 3l8 3v5c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6l8-3z"/>',
  layers:
    '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/><path d="M3 17l9 5 9-5"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  message:
    '<path d="M4 6h16v10H8l-4 4V6z"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 1 1 3.2 2.4c-.7.3-1.2.9-1.2 1.6V14"/><circle cx="12" cy="17" r=".8" fill="currentColor"/>',
  merge:
    '<circle cx="7" cy="6" r="2.5"/><circle cx="7" cy="18" r="2.5"/><circle cx="17" cy="12" r="2.5"/><path d="M7 8.5v7M9.2 12H14.5"/>',
  ban: '<circle cx="12" cy="12" r="9"/><path d="M6.5 6.5l11 11"/>',
  pause: '<path d="M8 6h3v12H8zM13 6h3v12h-3z"/>',
  play: '<path d="M8 6l12 6-12 6V6z"/>',
  trash:
    '<path d="M4 7h16M9 7V5h6v2M7 7l1 14h8l1-14"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M4 16V6a2 2 0 0 1 2-2h10"/>',
  upload:
    '<path d="M12 15V3M7 8l5-5 5 5"/><path d="M4 19h16"/>',
  download:
    '<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 19h16"/>',
  external:
    '<path d="M14 4h6v6"/><path d="M10 14L20 4"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
};

export function Icon({
  name,
  size = 20,
  className,
}: IconProps & { name: keyof typeof paths | string }) {
  const d = paths[name] ?? paths.alert;
  return (
    <svg
      className={className ? `icon ${className}` : 'icon'}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: d }}
    />
  );
}

export const AVATAR_COLORS = [
  'var(--av-1)',
  'var(--av-2)',
  'var(--av-3)',
  'var(--av-4)',
  'var(--av-5)',
  'var(--av-6)',
  'var(--av-7)',
  'var(--av-8)',
];

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Resolve avatar_url for <img src> — prefixes API origin for /uploads paths. */
export function resolveAvatarSrc(avatarUrl?: string | null): string | null {
  if (!avatarUrl) return null;
  if (/^https?:\/\//i.test(avatarUrl) || avatarUrl.startsWith('data:')) {
    return avatarUrl;
  }
  if (avatarUrl.startsWith('/uploads/')) {
    const raw = import.meta.env.VITE_API_BASE_URL;
    const origin = typeof raw === 'string' ? raw.replace(/\/$/, '') : '';
    // Empty origin → same-origin path (Vite proxies /uploads when configured).
    return origin ? `${origin}${avatarUrl}` : avatarUrl;
  }
  return avatarUrl;
}

export function Avatar({
  name,
  avatar = 1,
  avatarUrl,
  size = 'md',
}: {
  name: string;
  avatar?: number;
  avatarUrl?: string | null;
  size?: 'sm' | 'md' | 'lg';
}) {
  const color = AVATAR_COLORS[(Math.max(1, avatar) - 1) % AVATAR_COLORS.length];
  const cls =
    size === 'lg' ? 'avatar avatar--lg' : size === 'sm' ? 'avatar avatar--sm' : 'avatar';
  const src = resolveAvatarSrc(avatarUrl);
  if (src) {
    return (
      <span
        className={cls}
        style={{
          background: color,
          overflow: 'hidden',
          padding: 0,
        }}
        aria-hidden="true"
      >
        <img
          src={src}
          alt=""
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
            display: 'block',
            borderRadius: '50%',
          }}
        />
      </span>
    );
  }
  return (
    <span className={cls} style={{ background: color }} aria-hidden="true">
      {initials(name)}
    </span>
  );
}
