/**
 * Level identity: each level has its own mark and a one-line motto.
 * The marks are static SVG shapes, drawn in the current colour, so they
 * follow the level colour tokens in both themes.
 */

const SHAPES: Record<string, string> = {
  // one spark: the first idea
  spark: '<circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none"/>',
  // two linked points: a contributor works with others
  contributor:
    '<circle cx="8" cy="12" r="3.5" fill="currentColor" stroke="none"/><circle cx="16" cy="12" r="3.5" fill="currentColor" stroke="none"/>',
  // three stacked blocks: a builder ships layers
  builder:
    '<rect x="4" y="15" width="16" height="4" rx="1.2"/><rect x="7" y="10" width="10" height="4" rx="1.2"/><rect x="10" y="5" width="4" height="4" rx="1.2"/>',
  // four-point spark: a catalyst speeds others up
  catalyst:
    '<path d="M12 3.5l2.2 6.3 6.3 2.2-6.3 2.2L12 20.5l-2.2-6.3-6.3-2.2 6.3-2.2z" fill="currentColor" stroke="none"/>',
  // ring around a core: a pioneer opens new ground
  pioneer:
    '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3.5" fill="currentColor" stroke="none"/>',
};

export const LEVEL_MOTTO: Record<string, string> = {
  spark: 'Every idea starts with one spark.',
  contributor: 'Your ideas and help are moving work along.',
  builder: 'You are shipping work other people rely on.',
  catalyst: 'You speed up other people’s ideas.',
  pioneer: 'You have helped open new ground.',
};

interface Props {
  levelId: string;
  size?: number;
}

export function LevelMark({ levelId, size = 28 }: Props) {
  return (
    <svg
      className={`level-mark level-mark--${levelId}`}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinejoin="round"
      strokeLinecap="round"
      aria-hidden="true"
      dangerouslySetInnerHTML={{ __html: SHAPES[levelId] ?? SHAPES.spark }}
    />
  );
}
