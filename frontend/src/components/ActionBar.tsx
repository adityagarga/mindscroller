type Props = {
  onLike: () => void;
  onDislike: () => void;
  pressed?: "like" | "dislike" | null;
};

export function ActionBar({ onLike, onDislike, pressed }: Props) {
  return (
    <div
      className="absolute right-3 bottom-[30%] z-20 flex flex-col items-center gap-5"
      style={{ paddingBottom: "max(0px, env(safe-area-inset-bottom))" }}
    >
      <Pill
        label="like"
        active={pressed === "like"}
        bg="bg-rose-500"
        onClick={onLike}
        icon={
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
          </svg>
        }
      />
      <Pill
        label="dislike"
        active={pressed === "dislike"}
        bg="bg-neutral-700"
        onClick={onDislike}
        icon={
          <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17 14V2" />
            <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22h0a3.13 3.13 0 0 1-3-3.88Z" />
          </svg>
        }
      />
    </div>
  );
}

function Pill({
  label, icon, onClick, active, bg,
}: { label: string; icon: React.ReactNode; onClick: () => void; active?: boolean; bg: string; }) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-1 select-none active:scale-90 transition-transform"
      aria-label={label}
    >
      <span
        className={
          "w-12 h-12 rounded-full grid place-items-center shadow-lg transition-all " +
          bg +
          (active ? " ring-2 ring-white scale-110" : "")
        }
      >
        {icon}
      </span>
      <span className="text-[10px] uppercase tracking-wider text-white/80 font-semibold">{label}</span>
    </button>
  );
}
