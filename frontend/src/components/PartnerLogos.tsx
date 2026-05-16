// Partner attribution marks. We use the official logos shipped from
// frontend/public/partners/ so the demo audience recognises the brands at
// a glance. Each lockup is `<icon> <wordmark>` with thin `|` separators.

type Common = { className?: string; title?: string };

/** OpenAI blossom mark — black SVG (inverted to white on dark surfaces via
 * the `invert` filter). */
export function OpenAILogo({ className = "", title = "OpenAI" }: Common) {
  return (
    <img
      src="/partners/openai.svg"
      alt={title}
      title={title}
      className={className + " invert"}
      draggable={false}
    />
  );
}

/** fal.ai crimson 4-pointed mark — original color preserved. */
export function FalLogo({ className = "", title = "fal.ai" }: Common) {
  return (
    <img
      src="/partners/fal.png"
      alt={title}
      title={title}
      className={className}
      draggable={false}
    />
  );
}

/** Gradium "Gr" mark — boosted brightness so the original grey renders bright
 * on dark backgrounds. The full wordmark lives at /partners/gradium.svg and is
 * used separately in the onboarding attribution row. */
export function GradiumLogo({ className = "", title = "Gradium" }: Common) {
  return (
    <img
      src="/partners/gradium-icon.png"
      alt={title}
      title={title}
      className={className + " brightness-200 contrast-150"}
      draggable={false}
    />
  );
}

/** Compact horizontal lockup used on each content card. Reads
 * "[icon] OpenAI | [icon] fal.ai | [icon] Gradium" — wordmarks are visible so
 * the audience can identify each partner without zooming. */
export function PartnerStrip({
  label = "Powered by",
  className = "",
  iconClass = "h-6 w-6",
}: {
  label?: string;
  className?: string;
  iconClass?: string;
}) {
  return (
    <div
      className={
        "inline-flex items-center gap-3.5 px-4 py-3 rounded-full " +
        "bg-black/55 backdrop-blur-md ring-1 ring-white/15 " +
        "text-white/85 " +
        className
      }
    >
      <span className="text-[12px] uppercase tracking-[0.18em] font-bold text-white/55 whitespace-nowrap">
        {label}
      </span>

      <span className="flex items-center gap-2 text-[15px] font-bold text-white whitespace-nowrap">
        <OpenAILogo className={iconClass} />
        <span>OpenAI</span>
      </span>

      <span className="w-px h-5 bg-white/25" aria-hidden />

      <span className="flex items-center gap-2 text-[15px] font-bold text-white whitespace-nowrap">
        <FalLogo className={iconClass} />
        <span>fal.ai</span>
      </span>

      <span className="w-px h-5 bg-white/25" aria-hidden />

      <span className="flex items-center gap-2 text-[15px] font-bold text-white whitespace-nowrap">
        <GradiumLogo className={iconClass} />
        <span>Gradium</span>
      </span>
    </div>
  );
}
