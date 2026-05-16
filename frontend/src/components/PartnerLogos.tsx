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

/** Horizontal partner lockup. Reads
 * "[icon] OpenAI | [icon] fal.ai | [icon] Gradium" — wordmarks are visible so
 * the audience can identify each partner without zooming.
 *
 * Three size variants:
 *   - "sm" used inline on content cards (default)
 *   - "md" reserved for future medium contexts
 *   - "lg" used on the onboarding splash where the pill is a hero element
 */
type PartnerSize = "sm" | "md" | "lg";

const SIZE_STYLES: Record<
  PartnerSize,
  {
    wrapper: string;
    label: string;
    text: string;
    icon: string;
    divider: string;
    gap: string;
    brandGap: string;
  }
> = {
  sm: {
    wrapper: "px-4 py-3",
    label: "text-[12px] tracking-[0.18em]",
    text: "text-[15px]",
    icon: "h-6 w-6",
    divider: "h-5",
    gap: "gap-3.5",
    brandGap: "gap-2",
  },
  md: {
    wrapper: "px-6 py-4",
    label: "text-[14px] tracking-[0.2em]",
    text: "text-[18px]",
    icon: "h-7 w-7",
    divider: "h-6",
    gap: "gap-5",
    brandGap: "gap-2.5",
  },
  lg: {
    wrapper: "px-8 py-5",
    label: "text-[18px] tracking-[0.22em]",
    text: "text-[28px]",
    icon: "h-10 w-10",
    divider: "h-9",
    gap: "gap-6",
    brandGap: "gap-3",
  },
};

export function PartnerStrip({
  label = "Powered by",
  className = "",
  size = "sm",
}: {
  label?: string;
  className?: string;
  size?: PartnerSize;
}) {
  const s = SIZE_STYLES[size];
  return (
    <div
      className={
        "inline-flex items-center rounded-full " +
        "bg-black/55 backdrop-blur-md ring-1 ring-white/15 text-white/85 " +
        s.wrapper +
        " " +
        s.gap +
        " " +
        className
      }
    >
      <span
        className={
          "uppercase font-bold text-white/55 whitespace-nowrap " + s.label
        }
      >
        {label}
      </span>

      <span
        className={
          "flex items-center font-bold text-white whitespace-nowrap " +
          s.brandGap +
          " " +
          s.text
        }
      >
        <OpenAILogo className={s.icon} />
        <span>OpenAI</span>
      </span>

      <span className={"w-px bg-white/25 " + s.divider} aria-hidden />

      <span
        className={
          "flex items-center font-bold text-white whitespace-nowrap " +
          s.brandGap +
          " " +
          s.text
        }
      >
        <FalLogo className={s.icon} />
        <span>fal.ai</span>
      </span>

      <span className={"w-px bg-white/25 " + s.divider} aria-hidden />

      <span
        className={
          "flex items-center font-bold text-white whitespace-nowrap " +
          s.brandGap +
          " " +
          s.text
        }
      >
        <GradiumLogo className={s.icon} />
        <span>Gradium</span>
      </span>
    </div>
  );
}
