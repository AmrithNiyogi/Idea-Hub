/** Points dimension breakdown bar matching idea-hub.html `bdBar()` / `bdLegend()`. */

export function DimLegend() {
  return (
    <div className="bd-legend" aria-label="Breakdown colours">
      <span>
        <i className="lg-q" />
        Quality
      </span>
      <span>
        <i className="lg-c" />
        Collaboration
      </span>
      <span>
        <i className="lg-d" />
        Delivery
      </span>
      <span>
        <i className="lg-i" />
        Impact
      </span>
    </div>
  );
}

export function DimBar({
  dims,
}: {
  dims?: Record<string, number> | null;
}) {
  const d = {
    quality: dims?.quality ?? 0,
    collab: dims?.collab ?? 0,
    delivery: dims?.delivery ?? 0,
    impact: dims?.impact ?? 0,
  };
  const t = d.quality + d.collab + d.delivery + d.impact;
  const seg = (k: keyof typeof d, cls: string) =>
    d[k] > 0 ? (
      <i
        key={k}
        className={cls}
        style={{ width: `${((100 * d[k]) / t).toFixed(1)}%` }}
      />
    ) : null;

  return (
    <div
      className="bd"
      role="img"
      aria-label={`Quality ${d.quality}, Collaboration ${d.collab}, Delivery ${d.delivery}, Impact ${d.impact} points`}
      title={`Quality ${d.quality} · Collaboration ${d.collab} · Delivery ${d.delivery} · Impact ${d.impact}`}
    >
      {t
        ? (
          <>
            {seg('quality', 'bd-q')}
            {seg('collab', 'bd-c')}
            {seg('delivery', 'bd-d')}
            {seg('impact', 'bd-i')}
          </>
        )
        : null}
    </div>
  );
}
