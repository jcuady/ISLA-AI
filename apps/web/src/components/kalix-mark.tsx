/**
 * KALIX shield mark.
 *
 * KALIX is derived from *kalasag* (shield): a shield enclosing a closed padlock.
 * Drawn as a self-contained SVG so it renders crisply at any size, needs no
 * network request, and inherits `currentColor` for theming.
 *
 * The padlock is true negative space — masked out of the shield rather than
 * drawn on top — which is what lets the mark sit on any background without the
 * lock needing its own fill.
 *
 * Geometry matches branding/kalix-mark.svg, the vector master traced from the
 * generated raster in branding/kalix-mark-noir.png.
 */
export function KalixMark({
  size = 26,
  className,
}: {
  size?: number;
  className?: string;
}) {
  // The mask id is suffixed by size so two differently-sized marks on the same
  // page cannot collide - duplicate DOM ids silently break mask references.
  const maskId = `kalix-knockout-${size}`;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 512 512"
      fill="none"
      role="img"
      aria-label="KALIX shield"
      className={className}
    >
      <defs>
        <mask id={maskId} maskUnits="userSpaceOnUse" x="0" y="0" width="512" height="512">
          <rect width="512" height="512" fill="#fff" />
          <g fill="#000">
            {/* lock body */}
            <rect x="168" y="240" width="176" height="150" rx="22" />
            {/* shackle: outer arc out, inner arc back, drawn as one filled ring */}
            <path d="M198 248 V198 a58 58 0 0 1 116 0 v50 h-36 v-50 a22 22 0 0 0 -44 0 v50 z" />
          </g>
        </mask>
      </defs>
      <path
        fill="currentColor"
        mask={`url(#${maskId})`}
        d="M256 18 C182 18 112 42 58 84 C45 94 38 109 38 126 L38 250 C38 346 128 432 256 480 C384 432 474 346 474 250 L474 126 C474 109 467 94 454 84 C400 42 330 18 256 18 Z"
      />
    </svg>
  );
}

export default KalixMark;