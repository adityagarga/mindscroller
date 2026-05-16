import { forwardRef, useCallback, useRef, useState } from "react";
import { type Card as CardT } from "../lib/api";
import { useApp } from "../lib/store";
import { ActionBar } from "./ActionBar";
import { AudioControls } from "./AudioControls";
import { PartnerStrip } from "./PartnerLogos";

type Props = {
  card: CardT;
  onLike: () => void;
  onDislike: () => void;
};

export const Card = forwardRef<HTMLElement, Props>(function Card(
  { card, onLike, onDislike },
  ref,
) {
  const [imgFailed, setImgFailed] = useState(false);
  const [pressed, setPressed] = useState<"like" | "dislike" | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const getAudio = useCallback(() => audioRef.current, []);
  const isFreshlyGenerated = useApp((s) => s.freshlyGeneratedIds.has(card.id));
  // Mute is global — bind it to the audio element here so React applies it
  // synchronously on every render. Doing this only in AudioControls' effect
  // leaves a window where a freshly-mounted card briefly plays unmuted
  // before the effect runs.
  const muted = useApp((s) => s.muted);

  function flash(kind: "like" | "dislike", fn: () => void) {
    setPressed(kind);
    fn();
    setTimeout(() => setPressed(null), 600);
  }

  const hasImage = card.image_path && !imgFailed;

  return (
    <article
      ref={ref as React.Ref<HTMLElement>}
      data-card-id={card.id}
      className="feed-card bg-ink"
    >
      {/* Full-bleed blurred backdrop derived from the same image —
          fills the space outside the portrait card on desktop. */}
      {hasImage && (
        <img
          src={card.image_path!}
          alt=""
          aria-hidden
          draggable={false}
          className="absolute inset-0 w-full h-full object-cover scale-110 blur-3xl brightness-[0.35] saturate-150"
        />
      )}
      <div className="absolute inset-0 bg-black/30" />

      {/* Audio (hidden — Feed orchestrates play/pause via IntersectionObserver,
          and the in-card AudioControls drives it directly via audioRef). */}
      {card.audio_path && (
        <audio
          ref={audioRef}
          data-audio
          src={card.audio_path}
          preload="auto"
          playsInline
          muted={muted}
        />
      )}

      {/* Centered portrait card — preserves the 3:4 aspect of the fal.ai output
          so the full image is always visible (letterboxed by the blur backdrop).
          On desktop we cap the width so the card reads as a mobile-shaped column
          instead of a giant 720px rectangle. */}
      <div className="absolute inset-0 flex items-center justify-center p-3 sm:p-6">
        <div
          className="relative h-full w-full max-w-full max-h-full xl:max-w-[560px] rounded-2xl overflow-hidden shadow-2xl"
          style={{ aspectRatio: "3 / 4" }}
        >
          {card.audio_path && <AudioControls getAudio={getAudio} />}
          {hasImage ? (
            <img
              src={card.image_path!}
              alt=""
              className="absolute inset-0 w-full h-full object-cover"
              onError={() => setImgFailed(true)}
              draggable={false}
            />
          ) : (
            <div className="absolute inset-0 bg-gradient-to-br from-[#1a1a25] to-[#0d0d12]" />
          )}

          {/* Top-right: just the freshly-generated badge. The partner strip
              moved to the bottom info panel so its width doesn't overlap the
              mute button's hit area on narrower cards. */}
          {isFreshlyGenerated && (
            <div className="absolute top-3 right-3 z-20">
              <JustGeneratedBadge />
            </div>
          )}

          {/* Dim gradient bottom (legibility for script panel) */}
          <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-black/85 via-black/30 to-transparent pointer-events-none" />

          {/* Brutalist visual_hook overlay — vertically centered in upper 58% */}
          <div className="absolute inset-x-0 top-0 h-[58%] flex items-center justify-center px-5 pointer-events-none">
            <h2
              className="brutal-overlay text-center"
              style={{ fontSize: "clamp(28px, 6.5vh, 64px)" }}
            >
              {card.visual_hook}
            </h2>
          </div>

          {/* Bottom info panel: partner attribution + chips + script */}
          <div className="absolute bottom-0 left-0 right-0 px-4 pb-4 z-10">
            <div className="mb-3 flex justify-start">
              <PartnerStrip />
            </div>
            <div className="flex flex-col items-start gap-1.5 mb-3.5">
              <Chip tone="primary">{card.category}</Chip>
              <Chip tone="secondary">{card.topic}</Chip>
              {card.voice && <Chip tone="voice">🎙 {card.voice}</Chip>}
              {!card.audio_path && <Chip tone="muted">🔇 silent</Chip>}
            </div>
            <p className="text-white/95 text-[clamp(17px,2.4vw,22px)] leading-relaxed font-medium [text-shadow:0_1px_4px_rgba(0,0,0,0.85)]">
              {card.script}
            </p>
          </div>

          {/* ActionBar sits INSIDE the portrait card so it tracks the visible
              card edge — important on desktop where the card is centered and
              the dashboard would otherwise sit on top of viewport-anchored UI. */}
          <ActionBar
            onLike={() => flash("like", onLike)}
            onDislike={() => flash("dislike", onDislike)}
            pressed={pressed}
          />
        </div>
      </div>
    </article>
  );
});

type ChipTone = "primary" | "secondary" | "voice" | "muted";

// Brutalist tag: hard-edged rectangle, thick border, no rounding, no blur.
// The colored block on the left acts as a category flag.
const TONE_STYLES: Record<ChipTone, { block: string; border: string; text: string }> = {
  primary:   { block: "bg-violet-400", border: "border-violet-400", text: "text-white" },
  secondary: { block: "bg-sky-400",    border: "border-sky-400",    text: "text-white" },
  voice:     { block: "bg-amber-300",  border: "border-amber-300",  text: "text-amber-50" },
  muted:     { block: "bg-white/60",   border: "border-white/40",   text: "text-white/80" },
};

function Chip({
  children,
  tone,
  title,
}: {
  children: React.ReactNode;
  tone: ChipTone;
  title?: string;
}) {
  const t = TONE_STYLES[tone];
  return (
    <span
      title={title}
      className={
        "inline-flex items-stretch border-2 " +
        t.border +
        " bg-black/70 " +
        t.text +
        " text-[13px] font-black tracking-[0.06em] uppercase " +
        "shadow-[3px_3px_0_rgba(0,0,0,0.55)]"
      }
    >
      <span className={"w-2.5 shrink-0 " + t.block} />
      <span className="px-3 py-2 leading-none flex items-center">{children}</span>
    </span>
  );
}

// Prominent "this card was just generated for you" badge. Lives directly
// under the partner strip in the card's top-right so the connection to
// "you just clicked GENERATE NEW CONTENT" is unmissable.
function JustGeneratedBadge() {
  return (
    <span
      title="Generated for you just now"
      className="inline-flex items-stretch border-2 border-emerald-300
                 bg-emerald-400 text-ink
                 text-[15px] font-black tracking-[0.08em] uppercase
                 shadow-[3px_3px_0_rgba(0,0,0,0.6)]"
    >
      <span className="w-3 shrink-0 bg-ink" />
      <span className="px-3.5 py-2.5 leading-none flex items-center gap-2">
        <span className="inline-block w-2.5 h-2.5 rounded-full bg-ink animate-pulse" />
        ✨ Just generated for you
      </span>
    </span>
  );
}
